"""Command line interface."""

from __future__ import annotations

import argparse
import os
import sys

from miscree import __version__, integrate, session, system, watcher
from miscree.policy import TARGETS, Screens

DESCRIPTION = """\
Laptop / external display control for i3 on X11.

  on  laptop|external   turn a screen on (mirrors, sized for it, if the other is on)
  off laptop|external   turn a screen off (the other re-sizes; the last one blanks)
  watch                 follow plug/unplug events (started from i3)
  hotplug               apply the plug/unplug rules once
  list                  show screens, their kind and zoom
  setup / teardown      hook into i3 and the login (run by install.sh / uninstall.sh)
  session-init          login hook: print env for the configured render scale
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="miscree", description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"miscree {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")
    for name in ("on", "off"):
        sub.add_parser(name, help=f"turn a screen {name}").add_argument("screen", choices=TARGETS)
    sub.add_parser("watch", help="follow plug/unplug events")
    sub.add_parser("hotplug", help="apply plug/unplug rules once")
    sub.add_parser("list", help="show screens")
    sub.add_parser("session-init", help="login hook")
    setup = sub.add_parser("setup", help="hook into i3 and the login")
    setup.add_argument("--bin", help="path i3 and the login should run (default: this program)")
    setup.add_argument("--no-i3", dest="i3", action="store_false", help="leave the i3 config alone")
    setup.add_argument("--no-session", dest="session", action="store_false", help="leave ~/.xprofile alone")
    teardown = sub.add_parser("teardown", help="undo setup")
    teardown.add_argument("--purge", action="store_true", help="also delete ~/.config/miscree")
    return parser


def default_bin() -> str:
    path = os.path.abspath(sys.argv[0])
    if path.endswith(".py"):
        raise system.ScreenError("run setup from the installed miscree, or pass --bin")
    return path


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "watch":
            watcher.watch()
        elif args.command == "session-init":
            print(session.session_init())
        elif args.command == "setup":
            print("\n".join(integrate.setup(args.bin or default_bin(), i3=args.i3, session=args.session)))
        elif args.command == "teardown":
            print("\n".join(integrate.teardown(purge=args.purge)))
        else:
            with system.file_lock("action"):
                screens = Screens.detect()
                if args.command == "on":
                    screens.turn_on(args.screen)
                elif args.command == "off":
                    screens.turn_off(args.screen)
                elif args.command == "hotplug":
                    screens.hotplug()
                elif args.command == "list":
                    print(screens.describe())
    except system.ScreenError as e:
        system.notify(str(e))
        return 1
    return 0


def run() -> None:
    """Entry point for the installed single-file build."""
    sys.exit(main())
