"""Command line interface."""

from __future__ import annotations

import argparse
import shutil
import sys

from miscree import __version__, integrate, logs, report, session, system
from miscree.logs import log
from miscree.policy import TARGETS, Screens

DESCRIPTION = """\
Laptop / external display control for i3 on X11.

  on  laptop|external   turn a screen on (mirrors, sized for it, if the other is on)
  off laptop|external   turn a screen off (the other re-sizes; the last one blanks)
  startup               mirror both screens, sized for the laptop (run by i3 at login)
  hotplug               apply the plug/unplug rules once
  list                  show screens, their kind and zoom
  setup / teardown      hook this repo into i3 and the login, or unhook it
  session-init          login hook: print env for the configured render scale
  report                print everything needed to debug a problem (versions, screens, config, log)
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="miscree", description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"miscree {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")
    for name in ("on", "off"):
        sub.add_parser(name, help=f"turn a screen {name}").add_argument("screen", choices=TARGETS)
    sub.add_parser("startup", help="mirror both screens, sized for the laptop")
    sub.add_parser("hotplug", help="apply plug/unplug rules once")
    sub.add_parser("list", help="show screens")
    sub.add_parser("session-init", help="login hook")
    sub.add_parser("report", help="print debugging info to share")
    setup = sub.add_parser("setup", help="hook into i3 and the login")
    setup.add_argument("--no-i3", dest="i3", action="store_false", help="leave the i3 config alone")
    setup.add_argument("--no-session", dest="session", action="store_false", help="leave ~/.xprofile alone")
    teardown = sub.add_parser("teardown", help="undo setup")
    teardown.add_argument("--purge", action="store_true", help="also delete ~/.config/miscree")
    return parser


def reload_i3() -> None:
    if shutil.which("i3-msg"):
        system.run(["i3-msg", "reload"], check=False)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logs.start(sys.argv[1:] if argv is None else argv)
    try:
        if args.command == "report":
            print(report.build(describe_screens()))
        elif args.command == "session-init":
            print(session.session_init())
        elif args.command == "setup":
            print("\n".join(integrate.setup(i3=args.i3, session=args.session)))
            reload_i3()
        elif args.command == "teardown":
            print("\n".join(integrate.teardown(purge=args.purge)))
            reload_i3()
        else:
            with system.file_lock("action"):
                screens = Screens.detect()
                log.info("screens:\n%s", screens.describe())
                if args.command == "on":
                    screens.turn_on(args.screen)
                elif args.command == "off":
                    screens.turn_off(args.screen)
                elif args.command == "startup":
                    screens.startup()
                elif args.command == "hotplug":
                    screens.hotplug()
                elif args.command == "list":
                    print(screens.describe())
    except system.ScreenError as e:
        system.notify(str(e))
        return 1
    except Exception:
        log.exception("crashed")
        raise
    return 0


def describe_screens() -> str:
    try:
        return Screens.detect().describe()
    except Exception as e:
        return f"(could not detect screens: {e})"


def run() -> None:
    """Entry point for bin/miscree."""
    sys.exit(main())
