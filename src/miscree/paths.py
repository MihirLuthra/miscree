"""Where miscree keeps its files. All derived from XDG variables."""

import os
from pathlib import Path


def _xdg(var: str, default: Path) -> Path:
    return Path(os.environ.get(var) or default)


HOME = Path.home()
CONFIG_DIR = _xdg("XDG_CONFIG_HOME", HOME / ".config") / "miscree"
CONFIG_FILE = CONFIG_DIR / "config.ini"
I3_SNIPPET = CONFIG_DIR / "i3.conf"
HOOK_FILE = CONFIG_DIR / "post-apply"

RUNTIME_DIR = _xdg("XDG_RUNTIME_DIR", Path(f"/tmp/miscree-{os.getuid()}")) / "miscree"
DISPLAY_ID = os.environ.get("DISPLAY", ":0").replace("/", "_")
STATE_FILE = RUNTIME_DIR / f"state-{DISPLAY_ID}.json"

I3_CONFIG_CANDIDATES = (_xdg("XDG_CONFIG_HOME", HOME / ".config") / "i3" / "config", HOME / ".i3" / "config")
XPROFILE = HOME / ".xprofile"
