#!/usr/bin/env bash
# Undo install.sh: unhook from i3 and the login, restore clashing keybindings,
# remove the command. Keeps ~/.config/miscree unless --purge is given.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: ./uninstall.sh [--purge]

  --purge      Also delete ~/.config/miscree (your miscree config)
EOF
}

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
TARGET="$BIN_DIR/miscree"
TEARDOWN_ARGS=()

while (($#)); do
    case "$1" in
        --purge) TEARDOWN_ARGS+=(--purge) ;;
        -h | --help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
    shift
done

step() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }

step "Unhooking from i3 and the login"
"$REPO/bin/miscree" teardown "${TEARDOWN_ARGS[@]}" | sed 's/^/    /'

step "Stopping the watcher and removing $TARGET"
pkill -f "miscree watch" 2>/dev/null || true
rm -f "$TARGET"

if command -v i3-msg >/dev/null && i3-msg -t get_version >/dev/null 2>&1; then
    step "Reloading i3"
    i3-msg reload >/dev/null
fi

step "Done. Log out and back in to return to your previous render scale."
