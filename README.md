# miscree

Laptop / external display switching for **i3 on X11**, with a size (zoom) per screen
that applies **instantly to apps that are already open**.

| Event / key | What happens |
|---|---|
| Plug in a display | Switch to it alone, sized for it |
| Unplug it | Back to the laptop alone, sized for the laptop |
| `$mod+;` | Laptop on. If the external is on: mirror, sized for the **laptop** |
| `$mod+k` | External on. If the laptop is on: mirror, sized for the **external** |
| `$mod+Shift+;` / `$mod+Shift+k` | That screen off; the other re-sizes for itself. The last screen is blanked (any key wakes it) |

## Install

```sh
./install.sh
```

Then log out and back in once. That's all.

The installer:

1. installs `python3-xlib` (and `x11-xserver-utils`) with apt if missing;
2. puts a single-file `miscree` in `~/.local/bin`;
3. creates `~/.config/miscree/config.ini` and `~/.config/miscree/i3.conf` (keybindings), never overwriting your edits;
4. adds `include ~/.config/miscree/i3.conf` to your i3 config, comments out any of your bindings that clash with those keys, checks the result with `i3 -C` (rolling back if i3 rejects it) and reloads i3;
5. adds one line to `~/.xprofile` that sets the render scale at login.

Every edit sits in a `# >>> miscree >>>` block or is prefixed `# miscree-disabled:`, the first
version of each file is kept as `<file>.miscree-backup`, and re-running changes nothing.

| Option | |
|---|---|
| `--link` | symlink to this checkout instead of copying, so edits apply live (`make install-dev`) |
| `--no-i3` | leave the i3 config alone (add `include ~/.config/miscree/i3.conf` yourself) |
| `--no-session` | leave `~/.xprofile` alone (e.g. you use `startx`: put the line in `~/.xinitrc`) |
| `BIN_DIR=...` | install somewhere other than `~/.local/bin` |

## Configure

`~/.config/miscree/config.ini`. Run `miscree list` to see what each screen is detected as:

```
OUTPUT  STATE  KIND     MODEL         SIZE   NATIVE        ZOOM          LOGICAL
eDP-1   on     laptop   -             14.0"  1920x1200@60  1.35 (fixed)  2836x1773
HDMI-1  off    monitor  DELL U2723QE  27.2"  3840x2160@60  1.04 (fixed)  7373x4147
```

Zoom is set per kind of screen (`laptop`, `monitor`, `tv`) or per monitor model, as any of:

- `130dpi`: the size you'd get from `Xft.dpi: 130`
- `1.35`: a plain factor (1 = 96 dpi)
- `auto`: chosen from the screen's physical pixel density (TVs: 1080 logical lines)

Changes apply at the next switch. To change keybindings, edit `~/.config/miscree/i3.conf`.

To run something after every switch (e.g. reset the wallpaper), create an executable
`~/.config/miscree/post-apply`. It gets `MISCREE_LAYOUT` describing the new layout.

## How it works

X11 apps read their DPI (`Xft.dpi`) once, at startup, so changing it never affects open windows.
miscree never changes it. At login every app is told to render at a fixed **render scale**
(2× by default). On every switch, miscree scales the *screen* with an xrandr transform
instead, so the change is instant everywhere. Because the screen is only scaled *down*
from 2×, text stays sharp.

A small watcher (`miscree watch`, started by i3) listens for RandR output events,
debounces them, and applies the plug/unplug rules. It runs once per X session and exits with it.

## Commands

```
miscree on|off laptop|external
miscree list
miscree watch | hotplug
miscree setup | teardown [--purge]
miscree session-init
```

## Uninstall

```sh
./uninstall.sh            # keeps ~/.config/miscree
./uninstall.sh --purge    # removes it too
```

It removes the blocks, restores the bindings it commented out and deletes the command.

## Development

```sh
make test           # unit tests against a simulated X server, no display needed
make install-dev    # install as a symlink to this checkout
make build          # single-file build in dist/miscree
```

```
src/miscree/
  model.py      screens and modes (plain data)
  xrandr.py     parse xrandr/EDID, apply layouts
  config.py     config.ini and zoom rules
  layout.py     pure layout planning (framebuffer sizes, transforms)
  policy.py     what each shortcut / plug / unplug does
  watcher.py    RandR event loop
  session.py    login-time render scale (Xft.dpi, GDK/Qt env)
  integrate.py  i3 / ~/.xprofile setup and teardown
  system.py     every side effect (commands, notifications, locks, state)
  cli.py        command line
  templates/    default config.ini and i3.conf
```

## Limits

- X11 only (Wayland compositors do per-screen scaling themselves).
- One external display at a time; plugging in another switches to it.
- Mirroring keeps the aspect ratio (`mirror_fit = letterbox`). If your driver rejects that,
  it falls back to `stretch` automatically.
- Debugging: `pkill -f "miscree watch"; miscree watch` runs the watcher in a terminal.
