# miscree

Laptop / external display switching for **i3 on X11**, with a size (zoom) per screen
that applies **instantly to apps that are already open**.

Nothing runs in the background: besides the one run at login, every switch is a key or command.

| Key / command | What happens |
|---|---|
| Login | Both screens mirrored, sized for the **laptop** (or whichever one is connected) |
| `bin/miscree hotplug` after plugging in a display | Switch to it alone, sized for it |
| `bin/miscree hotplug` after unplugging it | Back to the laptop alone, sized for the laptop |
| `$mod+;` | Laptop on. If the external is on: mirror, sized for the **laptop** |
| `$mod+k` | External on. If the laptop is on: mirror, sized for the **external** |
| `$mod+Shift+;` / `$mod+Shift+k` | That screen off; the other re-sizes for itself. The last screen is blanked (any key wakes it) |

## Setup

miscree itself is never installed: everything runs from this repo. It needs Python 3.9+
and `xrandr`, `xrdb`, `xset`; `./install-deps.sh` installs whichever are
missing (with apt; on other distros it lists them for you).

```sh
./install-deps.sh
bin/miscree setup
```

Then log out and back in once. That's all.

Setup:

1. creates `~/.config/miscree/config.ini`, never overwriting your edits;
2. adds `set $miscree <repo>/bin/miscree` and `include <repo>/i3.conf` (keybindings, and `miscree startup` once at login) to your i3 config, comments out any of your bindings that clash with those keys, checks the result with `i3 -C` (rolling back if i3 rejects it) and reloads i3;
3. adds one line to `~/.xprofile` that runs `<repo>/bin/miscree session-init` at login to set the render scale.

Every edit sits in a `# >>> miscree >>>` block or is prefixed `# miscree-disabled:`, the first
version of each file is kept as `<file>.miscree-backup`, and re-running changes nothing.
Since i3 and the login point into the repo, don't move it after running setup (or run setup again if you do).

| Option | |
|---|---|
| `--no-i3` | leave the i3 config alone |
| `--no-session` | leave `~/.xprofile` alone (e.g. you use `startx`: put the line in `~/.xinitrc`) |

## Updating

`git pull`. Keybindings and commands use the new code right away.
If an update changes the keys in `i3.conf`, run `bin/miscree setup` again so clashing bindings get commented out.

## Configure

`~/.config/miscree/config.ini`. Run `bin/miscree list` to see what each screen is detected as:

```
OUTPUT  STATE  KIND     MODEL         SIZE   NATIVE        ZOOM          LOGICAL
eDP-1   on     laptop   -             14.0"  1920x1200@60  1.35 (fixed)  2836x1773
HDMI-1  off    monitor  DELL U2723QE  27.2"  3840x2160@60  1.04 (fixed)  7373x4147
```

Zoom is set per kind of screen (`laptop`, `monitor`, `tv`) or per monitor model, as any of:

- `130dpi`: the size you'd get from `Xft.dpi: 130`
- `1.35`: a plain factor (1 = 96 dpi)
- `auto`: chosen from the screen's physical pixel density (TVs: 1080 logical lines)

Changes apply at the next switch. To change keybindings, edit `i3.conf` in this repo and run `i3-msg reload`.

To run something after every switch (e.g. reset the wallpaper), create an executable
`~/.config/miscree/post-apply`. It gets `MISCREE_LAYOUT` describing the new layout.

## How it works

X11 apps read their DPI (`Xft.dpi`) once, at startup, so changing it never affects open windows.
miscree never changes it. At login every app is told to render at a fixed **render scale**
(2× by default). On every switch, miscree scales the *screen* with an xrandr transform
instead, so the change is instant everywhere. Because the screen is only scaled *down*
from 2×, text stays sharp.

`hotplug` remembers which external screens were connected the last time it ran, so it can tell
a newly plugged-in screen from an unplugged one.

## Commands

All run as `bin/miscree <command>` (or put `bin/` on your `PATH`).

```
miscree on|off laptop|external
miscree list
miscree startup | hotplug
miscree setup | teardown [--purge]
miscree session-init
```

## Remove

```sh
bin/miscree teardown           # keeps ~/.config/miscree
bin/miscree teardown --purge   # removes it too
```

It removes the blocks, restores the bindings it commented out and reloads i3.
Then the repo can be deleted.

## Development

```sh
make test           # unit tests against a simulated X server, no display needed
```

```
src/miscree/
  model.py      screens and modes (plain data)
  xrandr.py     parse xrandr/EDID, apply layouts
  config.py     config.ini and zoom rules
  layout.py     pure layout planning (framebuffer sizes, transforms)
  policy.py     what each shortcut / plug / unplug does
  session.py    login-time render scale (Xft.dpi, GDK/Qt env)
  integrate.py  i3 / ~/.xprofile setup and teardown
  system.py     every side effect (commands, notifications, locks, state)
  cli.py        command line
  templates/    default config.ini
```

## Limits

- X11 only (Wayland compositors do per-screen scaling themselves).
- One external display at a time; plugging in another switches to it.
- Mirroring keeps the aspect ratio (`mirror_fit = letterbox`). If your driver rejects that,
  it falls back to `stretch` automatically.
- Errors are printed and shown as desktop notifications.
