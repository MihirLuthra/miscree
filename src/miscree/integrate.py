"""Hooking miscree into i3 and the X login, and undoing it.

Every edit to a file you own is:
  * fenced in a marked block (or, for clashing keybindings, prefixed with a marker),
    so running setup again changes nothing and teardown removes exactly what was added;
  * backed up once, before the first change, to <file>.miscree-backup;
  * for the i3 config, validated with `i3 -C` and rolled back if i3 rejects it.
"""

from __future__ import annotations

import pkgutil
import re
import shutil
import subprocess
from pathlib import Path

from miscree import paths
from miscree.system import ScreenError

BEGIN = "# >>> miscree >>>"
END = "# <<< miscree <<<"
DISABLED = "# miscree-disabled: "
BLOCK_RE = re.compile(rf"\n?{re.escape(BEGIN)}\n.*?{re.escape(END)}\n?", re.S)
SET_RE = re.compile(r"^\s*set\s+(\$\S+)\s+(.+?)\s*$")
BINDSYM_RE = re.compile(r"^\s*bindsym\s+(?:--\S+\s+)*(\S+)")


# ───────────────────────────── text helpers (pure) ─────────────────────────────

def template(name: str) -> str:
    return pkgutil.get_data("miscree", f"templates/{name}").decode()


def remove_block(text: str) -> str:
    return BLOCK_RE.sub("", text)


def set_block(text: str, body: str) -> str:
    base = remove_block(text).rstrip("\n")
    return f"{base}{chr(10) * 2 if base else ''}{BEGIN}\n{body}\n{END}\n"


def i3_variables(text: str) -> dict[str, str]:
    return {m[1]: m[2] for m in map(SET_RE.match, text.splitlines()) if m}


def key_combo(line: str, variables: dict[str, str]) -> frozenset[str] | None:
    """`bindsym $mod+Shift+k ...` -> {'mod4', 'shift', 'k'} (None if not a bindsym)."""
    match = BINDSYM_RE.match(line)
    if not match:
        return None
    keys = match[1]
    for var in sorted(variables, key=len, reverse=True):
        keys = keys.replace(var, variables[var])
    return frozenset(k.lower() for k in keys.split("+"))


def disable_bindings(text: str, combos: set[frozenset[str]], variables: dict[str, str]) -> tuple[str, list[str]]:
    """Comment out top-level bindsym lines (not inside mode/bar blocks or our own
    block) that bind any of `combos`. Returns the new text and the disabled lines."""
    out, disabled, depth, in_ours = [], [], 0, False
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        in_ours = (in_ours or stripped == BEGIN) and stripped != END
        if depth == 0 and not in_ours and key_combo(line, variables) in combos:
            out.append(DISABLED + line)
            disabled.append(stripped)
        else:
            out.append(line)
        if not stripped.startswith("#"):
            depth = max(0, depth + stripped.count("{") - stripped.count("}"))
    return "".join(out), disabled


def restore_bindings(text: str) -> str:
    return "".join(line[len(DISABLED):] if line.startswith(DISABLED) else line
                   for line in text.splitlines(keepends=True))


def xprofile_body(bin_path: str) -> str:
    return f'[ -x "{bin_path}" ] && eval "$("{bin_path}" session-init)"'


# ───────────────────────────── file operations ─────────────────────────────

def find_i3_config() -> Path | None:
    return next((p for p in paths.I3_CONFIG_CANDIDATES if p.is_file()), None)


def backup_once(path: Path) -> None:
    backup = path.with_name(path.name + ".miscree-backup")
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)


def write_if_missing(path: Path, content: str, report: list[str]) -> None:
    if path.exists():
        report.append(f"kept your {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    report.append(f"created {path}")


def update_file(path: Path, new_text: str, report: list[str], what: str) -> bool:
    old_text = path.read_text() if path.exists() else ""
    if new_text == old_text:
        report.append(f"{what} already up to date ({path})")
        return False
    backup_once(path)
    path.write_text(new_text)
    report.append(f"updated {what} ({path})")
    return True


def validate_i3(path: Path) -> None:
    if not shutil.which("i3"):
        return
    proc = subprocess.run(["i3", "-C", "-c", str(path)], capture_output=True, text=True)
    errors = [l for l in (proc.stdout + proc.stderr).splitlines() if "ERROR: CONFIG" in l]
    if errors or proc.returncode != 0:
        raise ScreenError("i3 rejected the config, so it was left unchanged:\n" + "\n".join(errors[:8]))


# ───────────────────────────── setup / teardown ─────────────────────────────

def setup(bin_path: str, i3: bool = True, session: bool = True) -> list[str]:
    report: list[str] = []
    write_if_missing(paths.CONFIG_FILE, template("config.ini"), report)
    if i3:
        write_if_missing(paths.I3_SNIPPET, template("i3.conf").replace("@BIN@", bin_path), report)
        _setup_i3(report)
    if session:
        old = paths.XPROFILE.read_text() if paths.XPROFILE.exists() else ""
        update_file(paths.XPROFILE, set_block(old, xprofile_body(bin_path)), report, "login hook")
    return report


def _setup_i3(report: list[str]) -> None:
    config = find_i3_config()
    if config is None:
        report.append("no i3 config found; skipped i3 integration")
        return
    original = config.read_text()
    variables = i3_variables(original)
    wanted = {key_combo(line, variables) for line in paths.I3_SNIPPET.read_text().splitlines()} - {None}
    text, disabled = disable_bindings(original, wanted, variables)
    text = set_block(text, f"include {paths.I3_SNIPPET}")
    if update_file(config, text, report, "i3 config"):
        try:
            validate_i3(config)
        except ScreenError:
            config.write_text(original)
            raise
    report += [f"disabled clashing i3 binding: {line}" for line in disabled]


def teardown(purge: bool = False) -> list[str]:
    report: list[str] = []
    config = find_i3_config()
    if config:
        update_file(config, restore_bindings(remove_block(config.read_text())), report, "i3 config")
    if paths.XPROFILE.exists():
        update_file(paths.XPROFILE, remove_block(paths.XPROFILE.read_text()), report, "login hook")
    if purge and paths.CONFIG_DIR.exists():
        shutil.rmtree(paths.CONFIG_DIR)
        report.append(f"removed {paths.CONFIG_DIR}")
    return report
