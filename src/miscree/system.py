"""Side effects: running commands, notifications, locks and runtime state.

Everything that touches the outside world goes through here, so tests can
replace `system.run` with a fake X server.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import shutil
import stat
import subprocess
import sys

from pathlib import Path

from miscree import paths
from miscree.logs import log


class ScreenError(Exception):
    """A problem worth telling the user about."""


def run(cmd: list[str], check: bool = True, input: str | None = None) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True, input=input)
    err = proc.stderr.strip()
    log.info("$ %s -> %d%s", " ".join(cmd), proc.returncode, f": {err}" if err else "")
    if check and proc.returncode != 0:
        raise ScreenError(f"{' '.join(cmd)} failed: {proc.stderr.strip()}")
    return proc


def notify(message: str) -> None:
    log.warning("notify: %s", message)
    print(f"miscree: {message}", file=sys.stderr)
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "-a", "miscree", "-t", "2500", "Display", message], check=False)


def blank_screen() -> None:
    run(["xset", "dpms", "force", "off"], check=False)


def runtime_dir() -> Path:
    """The private directory for locks and state: a real directory, owned by us, mode 0700.
    It may fall back to /tmp, where another user could have planted it (or a symlink) first."""
    path = paths.RUNTIME_DIR
    with contextlib.suppress(FileExistsError):
        path.mkdir(mode=0o700, parents=True)
    st = os.lstat(path)
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
        raise ScreenError(f"{path} is not a directory owned by you; remove it and try again")
    if st.st_mode & 0o077:
        os.chmod(path, 0o700)
    return path


@contextlib.contextmanager
def file_lock(name: str, blocking: bool = True):
    """Yield True while holding the named lock, False if non-blocking and taken."""
    with open(runtime_dir() / f"{name}-{paths.DISPLAY_ID}.lock", "w") as fh:
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
    runtime_dir()
    paths.STATE_FILE.write_text(json.dumps({"connected": sorted(names)}))
    log.debug("seen externals: %s", sorted(names) or "none")


def forget_seen() -> None:
    paths.STATE_FILE.unlink(missing_ok=True)
