"""A tiny simulated X server: answers xrandr/xrdb/xset like the real tools."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


def edid(name: str | None, mm: tuple[int, int]) -> str:
    """Minimal EDID: size in basic params (cm) and in the first timing descriptor (mm)."""
    data = bytearray(128)
    data[0:8] = b"\x00\xff\xff\xff\xff\xff\xff\x00"
    data[21], data[22] = round(mm[0] / 10), round(mm[1] / 10)
    timing = bytearray(18)
    timing[0:2] = b"\x01\x1d"
    timing[12], timing[13] = mm[0] & 0xFF, mm[1] & 0xFF
    timing[14] = (mm[0] >> 8) << 4 | (mm[1] >> 8)
    data[54:72] = timing
    if name is None:
        return data.hex()
    descriptor = bytearray(18)
    descriptor[3] = 0xFC
    descriptor[5:18] = (name.encode() + b"\n").ljust(13, b" ")
    data[72:90] = descriptor
    return data.hex()


@dataclass
class Screen:
    modes: str
    mm: tuple[int, int]
    edid: str | None = None


SCREENS = {
    "eDP-1": Screen("   1920x1200     60.00 +  48.00  \n   1600x1200     60.00  ", (302, 189),
                    edid(None, (302, 189))),
    "HDMI-1": Screen("   3840x2160     60.00 +  30.00  \n   1920x1080     60.00  ", (597, 336),
                     edid("DELL U2723QE", (597, 336))),
    "DP-1": Screen("   3840x2160     60.00 +  59.94  ", (1210, 680), edid("SAMSUNG", (1210, 680))),
    "DP-2": Screen("   1920x1080     60.00 +  74.97  ", (527, 296), edid("LG 24MP", (527, 296))),
    "DP-3": Screen("   1920x1080     60.00 +  ", (0, 0)),
}


class FakeX:
    def __init__(self, connected, enabled, dpi: int = 192):
        self.connected, self.enabled, self.dpi = set(connected), set(enabled), dpi
        self.xrandr_calls: list[list[str]] = []
        self.blanked = False
        self.reject = lambda args: False

    def xrandr_text(self) -> str:
        lines = ["Screen 0: minimum 320 x 200, current 1920 x 1200, maximum 16384 x 16384"]
        for name, s in SCREENS.items():
            on = name in self.enabled
            if name not in self.connected:
                lines.append(f"{name} disconnected{' 1920x1080+0+0' if on else ''} (normal left inverted right)")
                continue
            geometry = " 1920x1080+0+0" if on else ""
            mm = f" {s.mm[0]}mm x {s.mm[1]}mm" if on else ""
            lines.append(f"{name} connected{geometry} (normal left inverted right x axis y axis){mm}")
            if s.edid:
                lines.append("\tEDID: ")
                lines += [f"\t\t{s.edid[i:i + 32]}" for i in range(0, 256, 32)]
            lines.append("\tBroadcast RGB: Automatic ")
            lines.append(s.modes)
        return "\n".join(lines) + "\n"

    def run(self, cmd, check=True, input=None):
        def ok(out=""):
            return subprocess.CompletedProcess(cmd, 0, out, "")

        if cmd[:2] == ["xrdb", "-query"]:
            return ok(f"Xft.dpi:\t{self.dpi}\n")
        if cmd[:2] == ["xrdb", "-merge"]:
            return ok()
        if cmd[:3] == ["xset", "dpms", "force"]:
            self.blanked = True
            return ok()
        if cmd == ["xrandr", "--current", "--prop"]:
            return ok(self.xrandr_text())
        if cmd[0] == "xrandr":
            args = cmd[1:]
            if self.reject(args):
                return subprocess.CompletedProcess(cmd, 1, "", "BadMatch")
            self.xrandr_calls.append(args)
            current = None
            for arg, nxt in zip(args, args[1:] + [""]):
                if arg == "--output":
                    current = nxt
                    self.enabled.add(current)
                elif arg == "--off":
                    self.enabled.discard(current)
            return ok()
        raise AssertionError(f"unexpected command {cmd}")

    def last_args(self) -> list[str]:
        return self.xrandr_calls[-1]

    def option(self, output: str, flag: str) -> str | None:
        """Value of `flag` for `output` in the last xrandr call."""
        args, current = self.last_args(), None
        for arg, nxt in zip(args, args[1:] + [""]):
            if arg == "--output":
                current = nxt
            elif current == output and arg == flag:
                return nxt
        return None
