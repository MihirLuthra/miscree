"""Login-time setup: make every app render at the configured render scale.

Called from ~/.xprofile as:  eval "$(miscree session-init)"
It loads Xft.dpi into the X resource database and prints the environment
variables GTK, Qt and the cursor need, for the shell to export.
"""

from __future__ import annotations

import tempfile

from miscree import system
from miscree.config import Config


def session_env(scale: int) -> dict[str, str]:
    return {
        "GDK_SCALE": str(scale),
        "GDK_DPI_SCALE": f"{1 / scale:.4g}",
        "QT_ENABLE_HIGHDPI_SCALING": "1",
        "XCURSOR_SIZE": str(24 * scale),
    }


def x_resources(scale: int) -> str:
    return f"Xft.dpi: {96 * scale}\nXcursor.size: {24 * scale}\n"


def session_init() -> str:
    """Load X resources and return shell export lines. Never fails the login."""
    try:
        scale = Config.load().render_scale
    except system.ScreenError as e:
        system.notify(f"{e} (using render_scale 2)")
        scale = 2
    load_x_resources(x_resources(scale))
    return "\n".join(f"export {k}={v}" for k, v in session_env(scale).items())


def load_x_resources(text: str) -> None:
    """Merge into the X resource database. Via a file, without cpp: some xrdb builds
    ignore stdin, and cpp isn't installed everywhere."""
    with tempfile.NamedTemporaryFile("w", prefix="miscree-", suffix=".Xresources") as fh:
        fh.write(text)
        fh.flush()
        system.run(["xrdb", "-nocpp", "-merge", fh.name], check=False)
