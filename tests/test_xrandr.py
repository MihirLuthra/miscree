import unittest

from miscree import xrandr
from tests.fakes import FakeX, edid


class ParseTest(unittest.TestCase):
    def setUp(self):
        x = FakeX(connected={"eDP-1", "HDMI-1", "DP-3"}, enabled={"eDP-1"})
        self.outputs = {o.name: o for o in xrandr.parse_xrandr(x.xrandr_text())}

    def test_connection_and_enabled_state(self):
        self.assertTrue(self.outputs["eDP-1"].connected and self.outputs["eDP-1"].enabled)
        self.assertTrue(self.outputs["HDMI-1"].connected)
        self.assertFalse(self.outputs["HDMI-1"].enabled)
        self.assertFalse(self.outputs["DP-1"].connected)

    def test_native_mode_is_preferred_mode_at_highest_rate(self):
        mode = self.outputs["HDMI-1"].mode
        self.assertEqual((mode.name, mode.width, mode.height, mode.rate), ("3840x2160", 3840, 2160, 60.0))

    def test_model_and_size_come_from_edid_whether_on_or_off(self):
        o = self.outputs["HDMI-1"]
        self.assertEqual(o.model, "DELL U2723QE")
        self.assertEqual(o.mm, (597, 336))
        self.assertEqual(self.outputs["eDP-1"].mm, (302, 189))
        self.assertTrue(self.outputs["eDP-1"].internal)

    def test_size_falls_back_to_header_without_edid(self):
        x = FakeX(connected={"DP-3"}, enabled={"DP-3"})
        o = xrandr.parse_xrandr(x.xrandr_text())[-1]
        self.assertEqual(o.mm, (0, 0))

    def test_screen_without_edid(self):
        o = self.outputs["DP-3"]
        self.assertIsNone(o.model)
        self.assertEqual(o.mm, (0, 0))
        self.assertIsNone(o.dpi)


class EdidTest(unittest.TestCase):
    def test_name_and_size(self):
        self.assertEqual(xrandr.parse_edid(edid("SAMSUNG", (1210, 680))), ("SAMSUNG", (1210, 680)))

    def test_garbage(self):
        self.assertEqual(xrandr.parse_edid("zz"), (None, (0, 0)))
        self.assertEqual(xrandr.parse_edid("00" * 128), (None, (0, 0)))


if __name__ == "__main__":
    unittest.main()
