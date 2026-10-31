import shutil
import unittest
from unittest import mock

from miscree import integrate, paths, session, system
from miscree.integrate import BEGIN, DISABLED, END

USER_I3 = """\
set $mod Mod4
font pango:monospace 10
bindsym $mod+Return exec kitty
bindsym Mod4+k exec --no-startup-id xrandr --output HDMI-1 --auto
bindsym $mod+Shift+k exec --no-startup-id xrandr --output HDMI-1 --off
bindsym --release $mod+semicolon exec old-laptop-on
mode "resize" {
    bindsym k resize shrink height 10 px
    bindsym $mod+k mode "default"
}
bar {
    status_command i3status
}
"""


class TextHelpersTest(unittest.TestCase):
    def test_set_block_is_idempotent_and_removable(self):
        once = integrate.set_block("a\n", "body")
        self.assertEqual(integrate.set_block(once, "body"), once)
        self.assertEqual(integrate.set_block(once, "new").count(BEGIN), 1)
        self.assertEqual(integrate.remove_block(once), "a\n")
        self.assertEqual(integrate.set_block("", "x"), f"{BEGIN}\nx\n{END}\n")

    def test_key_combo_resolves_variables_and_flags(self):
        v = {"$mod": "Mod4"}
        self.assertEqual(integrate.key_combo("bindsym --release $mod+Shift+K exec x", v),
                         frozenset({"mod4", "shift", "k"}))
        self.assertIsNone(integrate.key_combo("exec foo", v))

    def test_disable_only_top_level_clashes(self):
        v = integrate.i3_variables(USER_I3)
        wanted = {frozenset({"mod4", "k"}), frozenset({"mod4", "shift", "k"}), frozenset({"mod4", "semicolon"})}
        text, disabled = integrate.disable_bindings(USER_I3, wanted, v)
        self.assertEqual(len(disabled), 3)
        self.assertIn("    bindsym $mod+k mode \"default\"", text)
        self.assertIn("bindsym $mod+Return exec kitty\n", text)
        self.assertEqual(integrate.restore_bindings(text), USER_I3)


class SetupTest(unittest.TestCase):
    BIN = "/home/me/.local/bin/miscree"

    def setUp(self):
        self.i3 = paths.I3_CONFIG_CANDIDATES[0]
        self.i3.parent.mkdir(parents=True, exist_ok=True)
        self.i3.write_text(USER_I3)
        paths.XPROFILE.write_text("export FOO=1\n")
        self.addCleanup(self.clean)

    def clean(self):
        for f in (self.i3, paths.XPROFILE):
            f.unlink(missing_ok=True)
            f.with_name(f.name + ".miscree-backup").unlink(missing_ok=True)
        shutil.rmtree(paths.CONFIG_DIR, ignore_errors=True)

    def test_setup_then_teardown_restores_everything(self):
        report = integrate.setup(self.BIN)
        i3 = self.i3.read_text()
        self.assertIn(f"include {paths.I3_SNIPPET}", i3)
        self.assertEqual(i3.count(DISABLED), 3)
        self.assertIn(self.BIN, paths.I3_SNIPPET.read_text())
        self.assertIn("$mod+semicolon", paths.I3_SNIPPET.read_text())
        self.assertIn(f'"{self.BIN}" session-init', paths.XPROFILE.read_text())
        self.assertTrue(paths.CONFIG_FILE.exists())
        self.assertEqual(self.i3.with_name("config.miscree-backup").read_text(), USER_I3)
        self.assertTrue(any("disabled clashing" in line for line in report))

        self.assertTrue(any("already up to date" in line for line in integrate.setup(self.BIN)))
        self.assertEqual(self.i3.read_text(), i3)

        integrate.teardown()
        self.assertEqual(self.i3.read_text(), USER_I3)
        self.assertEqual(paths.XPROFILE.read_text(), "export FOO=1\n")
        self.assertTrue(paths.CONFIG_FILE.exists())
        integrate.teardown(purge=True)
        self.assertFalse(paths.CONFIG_DIR.exists())

    def test_user_edits_to_config_survive_reinstall(self):
        integrate.setup(self.BIN)
        paths.CONFIG_FILE.write_text("[zoom]\nlaptop = 2\n")
        integrate.setup(self.BIN)
        self.assertEqual(paths.CONFIG_FILE.read_text(), "[zoom]\nlaptop = 2\n")

    def test_opt_outs(self):
        integrate.setup(self.BIN, i3=False, session=False)
        self.assertEqual(self.i3.read_text(), USER_I3)
        self.assertEqual(paths.XPROFILE.read_text(), "export FOO=1\n")

    def test_rejected_i3_config_is_rolled_back(self):
        with mock.patch.object(integrate, "validate_i3", side_effect=system.ScreenError("nope")):
            with self.assertRaises(system.ScreenError):
                integrate.setup(self.BIN)
        self.assertEqual(self.i3.read_text(), USER_I3)


class SessionTest(unittest.TestCase):
    def test_exports_and_resources(self):
        merged = []

        def fake_run(cmd, check=True, input=None):
            merged.append((cmd[:3], open(cmd[3]).read()))

        with mock.patch.object(system, "run", fake_run):
            out = session.session_init()
        self.assertIn("export GDK_SCALE=2", out)
        self.assertIn("export GDK_DPI_SCALE=0.5", out)
        self.assertEqual(merged, [(["xrdb", "-nocpp", "-merge"], "Xft.dpi: 192\nXcursor.size: 48\n")])


if __name__ == "__main__":
    unittest.main()
