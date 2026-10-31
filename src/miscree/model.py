"""Plain data describing screens."""

from __future__ import annotations

import math
from dataclasses import dataclass

INTERNAL_PREFIXES = ("eDP", "LVDS", "DSI")


@dataclass(frozen=True)
class Mode:
    name: str
    width: int
    height: int
    rate: float


@dataclass
class Output:
    name: str
    connected: bool
    enabled: bool
    mode: Mode | None
    mm: tuple[int, int] = (0, 0)
    model: str | None = None

    @property
    def internal(self) -> bool:
        return self.name.startswith(INTERNAL_PREFIXES)

    @property
    def usable(self) -> bool:
        return self.connected and self.mode is not None

    @property
    def diagonal_inches(self) -> float:
        return math.hypot(*self.mm) / 25.4

    @property
    def dpi(self) -> float | None:
        if not self.mm[0] or not self.mode:
            return None
        return self.mode.width / (self.mm[0] / 25.4)
