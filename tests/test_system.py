import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from miscree import paths, system


class RuntimeDirTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="miscree-rt-"))
        self.dir = self.root / "miscree"
        patch = mock.patch.object(paths, "RUNTIME_DIR", self.dir)
        patch.start()
        self.addCleanup(patch.stop)

    def mode(self):
        return stat.S_IMODE(os.lstat(self.dir).st_mode)

    def test_created_private(self):
        system.runtime_dir()
        self.assertEqual(self.mode(), 0o700)

    def test_loose_permissions_are_tightened(self):
        self.dir.mkdir(mode=0o777)
        os.chmod(self.dir, 0o777)
        system.runtime_dir()
        self.assertEqual(self.mode(), 0o700)

    def test_symlink_is_refused(self):
        target = self.root / "elsewhere"
        target.mkdir()
        self.dir.symlink_to(target)
        with self.assertRaises(system.ScreenError):
            system.runtime_dir()

    def test_file_is_refused(self):
        self.dir.write_text("")
        with self.assertRaises(system.ScreenError):
            system.runtime_dir()


if __name__ == "__main__":
    unittest.main()
