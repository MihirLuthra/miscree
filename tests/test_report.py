import logging
import unittest
from unittest import mock

from miscree import integrate, paths, report, system
from miscree.logs import log

VERBOSE = """\
Screen 0: minimum 320 x 200, current 1920 x 1200, maximum 16384 x 16384
eDP-1 connected primary 1920x1200+0+0 (0x49) normal 301mm x 188mm
\tBrightness: 1.0
\tEDID:
\t\t00ffffffffffff0030e4c5050000000000
\t\t00ffffffffffff0030e4c50500000000
  1920x1200 (0x49) 154.129MHz +HSync -VSync *current +preferred
        h: width  1920 start 1968 end 2000 total 2080 skew    0 clock  74.10KHz
        v: height 1200 start 1203 end 1209 total 1235           clock  60.00Hz
HDMI-1 disconnected (normal left inverted right x axis y axis)
\tIdentifier: 0x43
\tCONNECTOR_ID: 516
"""

XORG_LOG = """\
[    13.466] Current Operating System: Linux my-hostname 7.0.0-42-generic x86_64
[    13.466] Kernel command line: BOOT_IMAGE=/boot/vmlinuz root=UUID=e7ef1883 ro quiet
[    13.478] (==) Matched intel as autoconfigured driver 0
[    13.480] (**) intel(0): Option "TearFree" "true"
[    13.481] (II) intel(0): EDID (in hex):
[    13.481] (II) intel(0): \t00ffffffffffff0006afab7300000000
[    13.490] (EE) event5  - Touchpad: kernel bug: Touch jump detected and discarded.
[    14.100] (EE) intel(0): failed to set mode: Invalid argument
"""


class ReportTest(unittest.TestCase):
    def test_xrandr_keeps_modes_drops_edid_timings_and_disconnected_details(self):
        with mock.patch.object(report, "command", return_value=VERBOSE):
            text = report.xrandr_verbose()
        self.assertIn("\tBrightness: 1.0", text)
        self.assertIn("1920x1200 (0x49) 154.129MHz", text)
        self.assertIn("HDMI-1 disconnected", text)
        self.assertNotIn("00ffffffffffff", text)
        self.assertNotIn("h: width", text)
        self.assertNotIn("CONNECTOR_ID", text)

    def test_miscree_lines_shows_only_our_block_and_disabled_bindings(self):
        text = integrate.set_block(f"set $mod Mod4\n{integrate.DISABLED}bindsym $mod+k focus up\n", "include x")
        self.assertEqual(report.miscree_lines(text),
                         f"{integrate.DISABLED}bindsym $mod+k focus up\n{integrate.BEGIN}\ninclude x\n{integrate.END}")
        self.assertEqual(report.miscree_lines("set $mod Mod4\n"), "(none)")

    def test_xorg_driver_keeps_driver_lines_only(self):
        log_dir = paths.HOME / ".local/share/xorg"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "Xorg.0.log").write_text(XORG_LOG)
        self.addCleanup((log_dir / "Xorg.0.log").unlink)
        with mock.patch.dict("os.environ", {"DISPLAY": ":0"}):
            text = report.xorg_driver()
        self.assertIn("(==) Matched intel as autoconfigured driver 0", text)
        self.assertIn('(**) intel(0): Option "TearFree" "true"', text)
        self.assertIn("(EE) intel(0): failed to set mode", text)
        for private in ("my-hostname", "root=UUID", "00ffffffffffff", "Touchpad", "13.466"):
            self.assertNotIn(private, text)

    def test_missing_tool_is_reported_not_raised(self):
        self.assertIn("No such file", report.command(["miscree-no-such-tool"]))


class LogTest(unittest.TestCase):
    def test_commands_and_their_errors_are_logged(self):
        with self.assertLogs(log, logging.INFO) as logged:
            system.run(["sh", "-c", "echo oops >&2; exit 3"], check=False)
        self.assertEqual(logged.output, ["INFO:miscree:$ sh -c echo oops >&2; exit 3 -> 3: oops"])

    def test_notifications_are_logged(self):
        with self.assertLogs(log, logging.WARNING) as logged, \
             mock.patch("shutil.which", return_value=None), mock.patch("builtins.print"):
            system.notify("No external screen connected")
        self.assertEqual(logged.output, ["WARNING:miscree:notify: No external screen connected"])


if __name__ == "__main__":
    unittest.main()
