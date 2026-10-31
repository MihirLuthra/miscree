import unittest

from miscree import paths, xrandr
from miscree.config import Config, parse_zoom
from miscree.integrate import template
from miscree.system import ScreenError
from tests.fakes import FakeX


def outputs():
    x = FakeX(connected={"eDP-1", "HDMI-1", "DP-1", "DP-2", "DP-3"}, enabled=set())
    return {o.name: o for o in xrandr.parse_xrandr(x.xrandr_text())}


class ConfigFileTest(unittest.TestCase):
    def tearDown(self):
        paths.CONFIG_FILE.unlink(missing_ok=True)

    def write(self, text):
        paths.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        paths.CONFIG_FILE.write_text(text)

    def test_missing_file_gives_defaults(self):
        cfg = Config.load()
        self.assertEqual(cfg.render_scale, 2)
        self.assertEqual(set(cfg.zoom.values()), {None})

    def test_shipped_template_loads(self):
        self.write(template("config.ini"))
        cfg = Config.load()
        self.assertAlmostEqual(cfg.zoom["laptop"], 130 / 96)
        self.assertAlmostEqual(cfg.zoom["monitor"], 100 / 96)
        self.assertIsNone(cfg.zoom["tv"])

    def test_models_and_inline_comments(self):
        self.write("[general]\nmirror_fit = stretch ; why not\n[models]\nDELL U2723QE = 1.25\n")
        cfg = Config.load()
        self.assertEqual(cfg.mirror_fit, "stretch")
        self.assertEqual(cfg.zoom_for(outputs()["HDMI-1"]), 1.25)
        self.assertEqual(cfg.zoom_source(outputs()["HDMI-1"]), "model")

    def test_bad_values_are_reported(self):
        for text in ("[zoom]\nlaptop = big\n", "[general]\nrender_scale = 1.5\n",
                     "[general]\nmirror_fit = crop\n", "[zoom]\nphone = 2\n", "[zoom]\nlaptop = -1\n"):
            with self.subTest(text=text):
                self.write(text)
                with self.assertRaises(ScreenError):
                    Config.load()


class ZoomTest(unittest.TestCase):
    def test_parse_zoom(self):
        self.assertIsNone(parse_zoom("auto"))
        self.assertEqual(parse_zoom(" 1.5 "), 1.5)
        self.assertEqual(parse_zoom("192dpi"), 2.0)

    def test_kinds(self):
        cfg, o = Config(), outputs()
        self.assertEqual([cfg.kind(o[n]) for n in ("eDP-1", "HDMI-1", "DP-1", "DP-3")],
                         ["laptop", "monitor", "tv", "monitor"])

    def test_auto_zoom(self):
        cfg, o = Config(), outputs()
        self.assertEqual(cfg.zoom_for(o["eDP-1"]), 1.5)
        self.assertEqual(cfg.zoom_for(o["HDMI-1"]), 1.5)
        self.assertEqual(cfg.zoom_for(o["DP-2"]), 1.0)
        self.assertEqual(cfg.zoom_for(o["DP-1"]), 2.0)
        self.assertEqual(cfg.zoom_for(o["DP-3"]), 1.0)


if __name__ == "__main__":
    unittest.main()
