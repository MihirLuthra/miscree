#!/usr/bin/env bash
# Install miscree for the current user and hook it into i3 and the X login.
# Safe to re-run: it updates the program and leaves your edited config alone.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: ./install.sh [options]

  --link         Symlink to this checkout instead of copying (edits take effect live)
  --no-i3        Don't touch the i3 config
  --no-session   Don't touch ~/.xprofile (render scale is then up to you)
  -h, --help     Show this help

Environment:
  BIN_DIR        Where to put the miscree command (default: ~/.local/bin)
EOF
}

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
TARGET="$BIN_DIR/miscree"
MODE=copy
SETUP_ARGS=()

while (($#)); do
    case "$1" in
        --link) MODE=link ;;
        --no-i3 | --no-session) SETUP_ARGS+=("$1") ;;
        -h | --help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
    shift
done

step() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

step "Checking dependencies"
command -v python3 >/dev/null || die "python3 is required"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' || die "python3 >= 3.9 is required"

missing=()
python3 -c 'import Xlib' 2>/dev/null || missing+=(python3-xlib)
for tool in xrandr xrdb xset; do
    command -v "$tool" >/dev/null || { missing+=(x11-xserver-utils); break; }
done
if ((${#missing[@]})); then
    if command -v apt-get >/dev/null; then
        step "Installing ${missing[*]} (needs sudo)"
        sudo apt-get install -y "${missing[@]}"
    else
        die "please install: python-xlib, xrandr, xrdb, xset (Debian names: ${missing[*]})"
    fi
fi

step "Installing miscree to $TARGET ($MODE)"
mkdir -p "$BIN_DIR"
rm -f "$TARGET"
if [[ $MODE == link ]]; then
    ln -s "$REPO/bin/miscree" "$TARGET"
else
    python3 "$REPO/scripts/build_zipapp.py" "$TARGET"
    chmod +x "$TARGET"
fi

step "Hooking into i3 and the login"
"$TARGET" setup --bin "$TARGET" "${SETUP_ARGS[@]}" | sed 's/^/    /'

if command -v i3-msg >/dev/null && i3-msg -t get_version >/dev/null 2>&1; then
    step "Reloading i3"
    i3-msg reload >/dev/null
fi

step "Done. Log out and back in once so every app picks up the render scale."
echo "    Then: plug/unplug screens, or use \$mod+; \$mod+k (and with Shift)."
echo "    See what was detected: miscree list"
