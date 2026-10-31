"""Follow plug/unplug events from X for the lifetime of the X session."""

from __future__ import annotations

import contextlib
import select
import sys
import time

from miscree import system
from miscree.policy import Screens

DEBOUNCE_S = 1.0


def watch() -> None:
    """Apply the hotplug rules now and after every RandR output change.
    Only one watcher runs per display; it exits when the X session ends."""
    from Xlib import display as xdisplay, error as xerror
    from Xlib.ext import randr

    with system.file_lock("watch", blocking=False) as acquired:
        if not acquired:
            print("miscree: watcher already running", file=sys.stderr)
            return
        system.forget_seen()
        run_hotplug()

        dpy = xdisplay.Display()
        dpy.screen().root.xrandr_select_input(randr.RROutputChangeNotifyMask)
        dpy.flush()
        with contextlib.suppress(xerror.ConnectionClosedError):
            _follow(dpy)


def _follow(dpy) -> None:
    """Collapse each burst of output-change events into a single hotplug run."""
    deadline = None
    while True:
        timeout = None if deadline is None else max(0.0, deadline - time.monotonic())
        readable, _, _ = select.select([dpy], [], [], timeout)
        if readable:
            for _ in range(dpy.pending_events()):
                dpy.next_event()
            deadline = time.monotonic() + DEBOUNCE_S
        elif deadline is not None:
            deadline = None
            run_hotplug()


def run_hotplug() -> None:
    try:
        with system.file_lock("action"):
            Screens.detect().hotplug()
    except system.ScreenError as e:
        system.notify(str(e))
