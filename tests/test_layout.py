import unittest

from miscree import xrandr
from miscree.config import Config
from miscree.layout import Planner, format_matrix, scale_matrix
from tests.fakes import FakeX


def outputs():
    x = FakeX(connected={"eDP-1", "HDMI-1"}, enabled={"eDP-1"})
    return {o.name: o for o in xrandr.parse_xrandr(x.xrandr_text())}


class PlannerTest(unittest.TestCase):
    def setUp(self):
        self.o = outputs()
        self.planner = Planner(Config(), render_scale=2)

    def test_single_scales_framebuffer_by_render_scale_over_zoom(self):
        layout = self.planner.single(self.o["eDP-1"])
        self.assertEqual(layout.fb, (2560, 1600))
        self.assertAlmostEqual(layout.placements[0].transform[0], 2560 / 1920)

    def test_zoom_equal_to_render_scale_is_untransformed(self):
        planner = Planner(Config(zoom={"laptop": 2.0, "monitor": 2.0, "tv": 2.0}), render_scale=2)
        layout = planner.single(self.o["HDMI-1"])
        self.assertEqual(layout.fb, (3840, 2160))
        self.assertEqual(format_matrix(layout.placements[0].transform), "none")

    def test_mirror_letterbox_keeps_aspect_and_centres(self):
        letterbox, stretch = self.planner.mirror(lead=self.o["eDP-1"], follower=self.o["HDMI-1"])
        self.assertIn("letterbox", letterbox.description)
        self.assertIn("stretch", stretch.description)
        t = letterbox.placements[1].transform
        self.assertEqual(t[0], t[4])
        self.assertAlmostEqual(t[0] * 3840 + 2 * t[2], 2560)
        self.assertEqual(letterbox.placements[1].same_as, "eDP-1")
        self.assertEqual(letterbox.fb, (2560, 1600))

    def test_mirror_fit_preference_orders_fallbacks(self):
        planner = Planner(Config(mirror_fit="stretch"), render_scale=2)
        first, _ = planner.mirror(lead=self.o["eDP-1"], follower=self.o["HDMI-1"])
        self.assertIn("stretch", first.description)

    def test_xrandr_args_turn_everything_else_off(self):
        args = self.planner.single(self.o["HDMI-1"]).xrandr_args(list(self.o.values()))
        self.assertEqual(args[:2], ["--fb", "5120x2880"])
        self.assertEqual(args[-3:], ["--output", "eDP-1", "--off"])
        self.assertNotIn("DP-1", args)

    def test_format_matrix(self):
        self.assertEqual(format_matrix(scale_matrix(1, 1)), "none")
        self.assertEqual(format_matrix(scale_matrix(2, 2, -10)), "2,0,-10,0,2,0,0,0,1")


if __name__ == "__main__":
    unittest.main()
