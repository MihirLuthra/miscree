#!/usr/bin/env bash
# Install what miscree needs to run from this repo: python3 >= 3.9,
# xrandr, xrdb and xset. Installs only what's missing. Safe to re-run.
set -euo pipefail

step() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
die() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

step "Checking dependencies"
command -v python3 >/dev/null || die "python3 is required"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' || die "python3 >= 3.9 is required"

missing=()
for tool in xrandr xrdb xset; do
    command -v "$tool" >/dev/null || { missing+=(x11-xserver-utils); break; }
done

if ((${#missing[@]} == 0)); then
    step "All dependencies are present"
elif command -v apt-get >/dev/null; then
    step "Installing ${missing[*]} (needs sudo)"
    sudo apt-get install -y "${missing[@]}"
else
    die "please install: xrandr, xrdb, xset (Debian names: ${missing[*]})"
fi

echo "    Next: bin/miscree setup"
