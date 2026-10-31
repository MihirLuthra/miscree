"""`miscree report`: everything needed to debug a setup, as one block of text to share.

Raw EDID is left out: it carries each monitor's serial number. So are mode timings,
details of disconnected outputs and config comments, to keep it short enough to paste.
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
from pathlib import Path

from miscree import __version__, integrate, logs, paths, session

XRANDR_NOISE_RE = re.compile(r"^(\s+[0-9a-f]{8,}|\s+[hv]: .*)\n", re.M)  # EDID hex, mode timings
OTHER_TOOLS = "autorandr|srandrd|kanshi|grobi|arandr"
DRIVERS = r"modeset|intel|AMDGPU|RADEON|NOUVEAU|NVIDIA"
# From the X server log: which driver runs the screen, its acceleration and options, its problems.
# Not the rest: it also holds the hostname, kernel command line and raw EDID.
XORG_RE = re.compile(rf"Matched \S+ as autoconfigured driver 0|LoadModule: \"({DRIVERS.lower()}|nvidia)\"|"
                     rf"\((II|WW|EE|\*\*)\) ({DRIVERS})\(\d\): (glamor|.*TearFree|.*AccelMethod|.*DRI driver|Option)|"
                     rf"\((WW|EE)\) ({DRIVERS})\(\d\): ")
ENV = ("DISPLAY", "XDG_SESSION_TYPE", "XDG_CURRENT_DESKTOP", "XDG_RUNTIME_DIR",
       *session.session_env(1), "QT_SCALE_FACTOR", "QT_AUTO_SCREEN_SCALE_FACTOR")


def command(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"({e})"
    return (proc.stdout + proc.stderr).strip() or f"(no output, exit {proc.returncode})"


def file(path) -> str:
    try:
        return path.read_text().strip() or "(empty)"
    except OSError as e:
        return f"({e.strerror})"


def matching(text: str, pattern: str) -> str:
    return "\n".join(l for l in text.splitlines() if re.search(pattern, l)) or "(none)"


def xrandr_verbose() -> str:
    out, disconnected = [], False
    for line in XRANDR_NOISE_RE.sub("", command(["xrandr", "--verbose"]) + "\n").splitlines():
        if not line[:1].isspace():
            disconnected = " disconnected " in line
        elif disconnected:
            continue
        out.append(line)
    return "\n".join(out)


def xorg_driver() -> str:
    display = os.environ.get("DISPLAY", ":0").lstrip(":").split(".")[0]
    logs_ = [p / f"Xorg.{display}.log" for p in (paths.HOME / ".local/share/xorg", Path("/var/log"))]
    found = [p for p in logs_ if p.is_file()]
    if not found:
        return "(no X server log found)"
    log_file = max(found, key=lambda p: p.stat().st_mtime)
    lines = (re.sub(r"^\[ *[\d.]+\] ", "", l) for l in log_file.read_text(errors="replace").splitlines())
    return f"{log_file}\n" + "\n".join(dict.fromkeys(l for l in lines if XORG_RE.search(l)))


def miscree_lines(text: str) -> str:
    """Our block and the bindings we disabled, from someone's i3 config or ~/.xprofile."""
    ours = [l for l in text.splitlines() if integrate.DISABLED in l]
    ours += [m.group(0) for m in integrate.BLOCK_RE.finditer(text)]
    return "\n".join(l.strip("\n") for l in ours) or "(none)"


def sections(screens: str) -> list[tuple[str, str]]:
    i3_config = integrate.find_i3_config()
    return [
        ("miscree", f"{__version__} ({logs.commit()}) from {paths.REPO}"),
        ("system", f"{platform.platform()}, python {platform.python_version()}"),
        ("graphics", command(["sh", "-c", "lspci -k -d ::0300; lspci -k -d ::0302; lspci -k -d ::0380"])),
        ("X driver", xorg_driver()),
        ("i3", command(["i3", "--version"])),
        ("environment", "\n".join(f"{k}={os.environ.get(k, '-')}" for k in ENV)),
        ("X resources", matching(command(["xrdb", "-query"]), r"^(Xft|Xcursor)")),
        ("miscree list", screens),
        ("xrandr --verbose (EDID and timings removed)", xrandr_verbose()),
        (str(paths.CONFIG_FILE), matching(file(paths.CONFIG_FILE), r"^[^;\s]")),
        (f"i3 config ({i3_config})", miscree_lines(i3_config.read_text()) if i3_config else "(no i3 config found)"),
        (str(paths.XPROFILE), miscree_lines(file(paths.XPROFILE))),
        ("other display tools", matching(command(["sh", "-c", "systemctl list-unit-files; systemctl --user list-unit-files; "
                                                  f"pgrep -a '{OTHER_TOOLS}'"]), OTHER_TOOLS)),
        (f"last log lines ({paths.LOG_FILE})", logs.tail(200)),
    ]


def build(screens: str) -> str:
    return "\n".join(f"===== {title} =====\n{body.rstrip()}\n" for title, body in sections(screens))
