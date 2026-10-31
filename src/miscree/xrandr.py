"""Reading screens from X and applying layouts with xrandr."""

from __future__ import annotations

import os
import re
import subprocess
from typing import TYPE_CHECKING

from miscree import paths, system
from miscree.logs import log
from miscree.model import Mode, Output

if TYPE_CHECKING:
    from miscree.layout import Layout

HEADER_RE = re.compile(r"^(\S+) (connected|disconnected)\b(.*)$")
GEOMETRY_RE = re.compile(r"\b\d+x\d+\+\d+\+\d+\b")
MM_RE = re.compile(r"(\d+)mm x (\d+)mm")
MODE_RE = re.compile(r"^ {2,}(\d+)x(\d+)(\S*)\s+(.*)$")
RATE_RE = re.compile(r"(\d+\.\d+)([* ])([+ ])")
HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
EDID_HEADER = b"\x00\xff\xff\xff\xff\xff\xff\x00"


def parse_edid(hexdata: str) -> tuple[str | None, tuple[int, int]]:
    """Return (monitor name, physical size in mm) from raw EDID hex.

    Size comes from the first detailed timing descriptor (mm precision), falling
    back to the basic display parameters (cm precision)."""
    try:
        edid = bytes.fromhex(hexdata)
    except ValueError:
        return None, (0, 0)
    if len(edid) < 128 or edid[:8] != EDID_HEADER:
        return None, (0, 0)
    name, mm = None, (edid[21] * 10, edid[22] * 10)
    for index, offset in enumerate((54, 72, 90, 108)):
        block = edid[offset:offset + 18]
        if block[0:2] != b"\x00\x00":
            if index == 0:
                width = block[12] | (block[14] & 0xF0) << 4
                height = block[13] | (block[14] & 0x0F) << 8
                mm = (width, height) if width and height else mm
        elif block[3] == 0xFC:
            name = block[5:18].split(b"\n")[0].decode("ascii", "replace").strip() or None
    return name, mm


def parse_xrandr(text: str) -> list[Output]:
    """Parse `xrandr --prop` output. An output's mode is its preferred (native) mode."""
    blocks: list[tuple[re.Match, list[str]]] = []
    for line in text.splitlines():
        header = HEADER_RE.match(line)
        if header:
            blocks.append((header, []))
        elif blocks:
            blocks[-1][1].append(line)
    return [_parse_output(header, body) for header, body in blocks]


def _parse_output(header: re.Match, body: list[str]) -> Output:
    name, status, rest = header.groups()
    edid_hex, in_edid = "", False
    preferred: Mode | None = None
    first: Mode | None = None
    for line in body:
        stripped = line.strip()
        if stripped == "EDID:":
            in_edid = True
            continue
        if in_edid:
            if HEX_RE.match(stripped):
                edid_hex += stripped
                continue
            in_edid = False
        mode_line = MODE_RE.match(line)
        if not mode_line:
            continue
        w, h, suffix, rates_text = mode_line.groups()
        rates = RATE_RE.findall(rates_text + "  ")
        if not rates:
            continue
        mode = Mode(f"{w}x{h}{suffix}", int(w), int(h), max(float(r) for r, _, _ in rates))
        first = first or mode
        if preferred is None and any(p == "+" for _, _, p in rates):
            preferred = mode

    model, mm = parse_edid(edid_hex)
    header_mm = MM_RE.search(rest)
    if not mm[0] and header_mm:
        mm = (int(header_mm[1]), int(header_mm[2]))
    return Output(
        name=name,
        connected=status == "connected",
        enabled=bool(GEOMETRY_RE.search(rest)),
        mode=preferred or first,
        mm=mm,
        model=model,
    )


def query_outputs() -> list[Output]:
    return parse_xrandr(system.run(["xrandr", "--current", "--prop"]).stdout)


def render_scale() -> float:
    """The scale apps currently render at, from Xft.dpi (96 dpi = 1.0)."""
    proc = system.run(["xrdb", "-query"], check=False)
    match = re.search(r"^Xft\.dpi:\s*([\d.]+)", proc.stdout, re.M)
    return float(match[1]) / 96 if match else 1.0


def apply(candidates: list["Layout"], outputs: list[Output]) -> "Layout":
    """Apply the first layout xrandr accepts, then run the user's post-apply hook."""
    errors = []
    for layout in candidates:
        proc = system.run(["xrandr", *layout.xrandr_args(outputs)], check=False)
        if proc.returncode == 0:
            log.info("applied: %s", layout.description)
            _run_hook(layout)
            return layout
        errors.append(f"{layout.description}: {proc.stderr.strip()}")
    raise system.ScreenError("xrandr rejected every layout:\n" + "\n".join(errors))


def _run_hook(layout: "Layout") -> None:
    hook = paths.HOOK_FILE
    if hook.is_file() and os.access(hook, os.X_OK):
        log.info("running %s", hook)
        subprocess.Popen([str(hook)], env={**os.environ, "MISCREE_LAYOUT": layout.description},
                         start_new_session=True)
