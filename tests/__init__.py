"""Point every miscree path at throwaway directories before anything imports it."""

import os
import tempfile

_root = tempfile.mkdtemp(prefix="miscree-tests-")
os.environ["HOME"] = os.path.join(_root, "home")
os.environ["XDG_CONFIG_HOME"] = os.path.join(_root, "home", ".config")
os.environ["XDG_RUNTIME_DIR"] = os.path.join(_root, "run")
os.environ["DISPLAY"] = ":42"
os.makedirs(os.environ["XDG_CONFIG_HOME"])
