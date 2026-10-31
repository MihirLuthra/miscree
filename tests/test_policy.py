"""End-to-end behaviour of the shortcuts and plug/unplug rules."""

import unittest
from unittest import mock

from miscree import system
from miscree.policy import Screens
from tests.fakes import FakeX


class PolicyTest(unittest.TestCase):
    def start(self, connected, enabled, dpi=192):
        self.x = FakeX(connected, enabled, dpi)
        self.notes = []
        for patch in (mock.patch.object(system, "run", self.x.run),
                      mock.patch.object(system, "notify", self.notes.append),
                      mock.patch("builtins.print")):
            patch.start()
            self.addCleanup(patch.stop)
        system.forget_seen()
        self.hotplug()

    def screens(self):
        return Screens.detect()

    def on(self, target):
        self.screens().turn_on(target)

    def off(self, target):
        self.screens().turn_off(target)

    def hotplug(self):
        self.screens().hotplug()

    def plug(self, name):
        self.x.connected.add(name)
        self.hotplug()

    def unplug(self, name):
        self.x.connected.discard(name)
        self.hotplug()

    # ── plug / unplug ──

    def test_session_start_without_external_uses_laptop(self):
        self.start({"eDP-1"}, {"eDP-1"})
        self.assertEqual(self.x.enabled, {"eDP-1"})
        self.assertIn("--primary", self.x.last_args())

    def test_session_start_with_external_uses_only_external(self):
        self.start({"eDP-1", "DP-1"}, {"eDP-1"})
        self.assertEqual(self.x.enabled, {"DP-1"})

    def test_plug_switches_to_external_and_unplug_switches_back(self):
        self.start({"eDP-1"}, {"eDP-1"})
        self.plug("HDMI-1")
        self.assertEqual(self.x.enabled, {"HDMI-1"})
        self.assertEqual(self.x.last_args()[:2], ["--fb", "5120x2880"])
        self.unplug("HDMI-1")
        self.assertEqual(self.x.enabled, {"eDP-1"})
        self.assertEqual(self.x.last_args()[:2], ["--fb", "2560x1600"])

    def test_unrelated_events_change_nothing(self):
        self.start({"eDP-1", "HDMI-1"}, {"eDP-1"})
        self.on("laptop")
        calls = len(self.x.xrandr_calls)
        self.hotplug()
        self.assertEqual(len(self.x.xrandr_calls), calls)

    def test_unplug_of_screen_user_already_turned_off_changes_nothing(self):
        self.start({"eDP-1", "DP-1"}, {"eDP-1"})
        self.on("laptop")
        self.off("external")
        calls = len(self.x.xrandr_calls)
        self.unplug("DP-1")
        self.assertEqual(len(self.x.xrandr_calls), calls)

    def test_nothing_on_recovers(self):
        self.start({"eDP-1"}, {"eDP-1"})
        self.x.enabled.clear()
        self.hotplug()
        self.assertEqual(self.x.enabled, {"eDP-1"})

    # ── shortcuts ──

    def test_laptop_on_while_external_on_mirrors_sized_for_laptop(self):
        self.start({"eDP-1", "HDMI-1"}, set())
        self.on("laptop")
        self.assertEqual(self.x.enabled, {"eDP-1", "HDMI-1"})
        self.assertEqual(self.x.last_args()[:2], ["--fb", "2560x1600"])
        self.assertEqual(self.x.option("HDMI-1", "--same-as"), "eDP-1")

    def test_external_on_while_laptop_on_mirrors_sized_for_external(self):
        self.start({"eDP-1", "HDMI-1"}, set())
        self.on("laptop")
        self.on("external")
        self.assertEqual(self.x.last_args()[:2], ["--fb", "5120x2880"])
        self.assertEqual(self.x.option("eDP-1", "--same-as"), "HDMI-1")

    def test_turning_one_mirrored_screen_off_resizes_the_other(self):
        self.start({"eDP-1", "HDMI-1"}, set())
        self.on("laptop")
        self.off("laptop")
        self.assertEqual(self.x.enabled, {"HDMI-1"})
        self.assertEqual(self.x.last_args()[:2], ["--fb", "5120x2880"])
        self.on("laptop")
        self.off("external")
        self.assertEqual(self.x.enabled, {"eDP-1"})
        self.assertEqual(self.x.last_args()[:2], ["--fb", "2560x1600"])

    def test_turning_off_the_last_screen_blanks_it(self):
        self.start({"eDP-1"}, {"eDP-1"})
        self.off("laptop")
        self.assertTrue(self.x.blanked)
        self.assertEqual(self.x.enabled, {"eDP-1"})

    def test_external_on_without_external_tells_you(self):
        self.start({"eDP-1"}, {"eDP-1"})
        self.on("external")
        self.assertEqual(self.notes, ["No external screen connected"])

    def test_letterbox_rejected_falls_back_to_stretch(self):
        self.start({"eDP-1", "HDMI-1"}, set())
        self.x.reject = lambda args: "--same-as" in args and any(a.startswith("0.740741,0,-") for a in args)
        self.on("laptop")
        self.assertEqual(self.x.option("HDMI-1", "--same-as"), "eDP-1")
        self.assertEqual(self.x.option("HDMI-1", "--transform"), "0.666667,0,0,0,0.740741,0,0,0,1")

    def test_works_at_render_scale_one(self):
        self.start({"eDP-1"}, {"eDP-1"}, dpi=96)
        self.assertEqual(self.x.last_args()[:2], ["--fb", "1280x800"])

    def test_list(self):
        self.start({"eDP-1", "HDMI-1"}, {"eDP-1"}, dpi=96)
        text = self.screens().describe()
        self.assertIn("DELL U2723QE", text)
        self.assertIn("log out and back in", text)


if __name__ == "__main__":
    unittest.main()
