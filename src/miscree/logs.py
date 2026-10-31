"""A log of every run, for figuring out what happened on someone else's machine.

~/.local/state/miscree/miscree.log, at most 1 MB plus one rotated file.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import subprocess
import sys

from miscree import __version__, paths

log = logging.getLogger("miscree")
log.addHandler(logging.NullHandler())
log.propagate = False


def start(argv: list[str]) -> None:
    """Log to the file from now on and record what is running. Never fails the command."""
    try:
        paths.STATE_DIR.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(paths.LOG_FILE, maxBytes=1_000_000, backupCount=1)
    except OSError:
        return
    handler.setFormatter(logging.Formatter("%(asctime)s [%(process)d] %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    log.info("miscree %s (%s) %s | DISPLAY=%s python %s", __version__, commit(), " ".join(argv),
             os.environ.get("DISPLAY", "-"), sys.version.split()[0])


def commit() -> str:
    """Short git commit of the repo this runs from, '+dirty' if it has local changes."""
    try:
        sha = subprocess.run(["git", "-C", str(paths.REPO), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(paths.REPO), "status", "--porcelain", "-uno"],
                               capture_output=True, text=True).stdout.strip()
    except OSError:
        return "unknown"
    return (sha or "unknown") + ("+dirty" if dirty else "")


def tail(lines: int) -> str:
    try:
        return "".join(paths.LOG_FILE.read_text(errors="replace").splitlines(keepends=True)[-lines:])
    except OSError:
        return "(no log yet)\n"
