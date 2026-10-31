"""Side effects: running commands, notifications, locks and runtime state.

Everything that touches the outside world goes through here, so tests can
replace `system.run` with a fake X server.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import shutil
import subprocess
import sys

from miscree import paths


class ScreenError(Exception):
    """A problem worth telling the user about."""


def run(cmd: list[str], check: bool = True, input: str | None = None) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, input=input)
    if check and proc.returncode != 0:
        raise ScreenError(f"{' '.join(cmd)} failed: {proc.stderr.strip()}")
    return proc


def notify(message: str) -> None:
    print(f"miscree: {message}", file=sys.stderr)
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "-a", "miscree", "-t", "2500", "Display", message], check=False)


def blank_screen() -> None:
    run(["xset", "dpms", "force", "off"], check=False)


@contextlib.contextmanager
def file_lock(name: str, blocking: bool = True):
    """Yield True while holding the named lock, False if non-blocking and taken."""
    paths.RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with open(paths.RUNTIME_DIR / f"{name}-{paths.DISPLAY_ID}.lock", "w") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            yield False
            return
        yield True


def load_seen() -> set[str] | None:
    """External screens connected at the last hotplug run (None = first run)."""
    try:
        return set(json.loads(paths.STATE_FILE.read_text())["connected"])
    except (OSError, ValueError, KeyError):
        return None


def save_seen(names: set[str]) -> None:
    paths.RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    paths.STATE_FILE.write_text(json.dumps({"connected": sorted(names)}))


def forget_seen() -> None:
    paths.STATE_FILE.unlink(missing_ok=True)
