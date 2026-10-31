"""User configuration (~/.config/miscree/config.ini) and zoom rules."""

from __future__ import annotations

import configparser
from dataclasses import dataclass, field
from pathlib import Path

from miscree import paths
from miscree.model import Output
from miscree.system import ScreenError

AUTO = None
KINDS = ("laptop", "monitor", "tv")


def parse_zoom(value: str, allow_auto: bool = True) -> float | None:
    """'auto', a factor like '1.5', or a DPI like '130dpi' (same as Xft.dpi: 130)."""
    value = value.strip().lower()
    if value == "auto" and allow_auto:
        return AUTO
    if value.endswith("dpi"):
        return float(value[:-3]) / 96
    return float(value)


@dataclass
class Config:
    render_scale: int = 2
    mirror_fit: str = "letterbox"
    tv_min_inches: float = 40.0
    zoom: dict[str, float | None] = field(default_factory=lambda: dict.fromkeys(KINDS, AUTO))
    target_dpi: dict[str, float] = field(default_factory=lambda: {"laptop": 108.0, "monitor": 110.0})
    tv_logical_height: int = 1080
    zoom_step: float = 0.25
    models: dict[str, float] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        path = path or paths.CONFIG_FILE
        cfg = cls()
        if not path.exists():
            return cfg
        ini = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
        try:
            ini.read(path)
            cfg._read(ini)
        except (configparser.Error, ValueError) as e:
            raise ScreenError(f"Bad config {path}: {e}") from e
        cfg._validate(path)
        return cfg

    def _read(self, ini: configparser.ConfigParser) -> None:
        general = ini["general"] if ini.has_section("general") else {}
        auto = ini["auto"] if ini.has_section("auto") else {}
        self.render_scale = int(general.get("render_scale", self.render_scale))
        self.mirror_fit = general.get("mirror_fit", self.mirror_fit).strip().lower()
        self.tv_min_inches = float(general.get("tv_min_inches", self.tv_min_inches))
        self.target_dpi["laptop"] = float(auto.get("laptop_target_dpi", self.target_dpi["laptop"]))
        self.target_dpi["monitor"] = float(auto.get("monitor_target_dpi", self.target_dpi["monitor"]))
        self.tv_logical_height = int(auto.get("tv_logical_height", self.tv_logical_height))
        self.zoom_step = float(auto.get("step", self.zoom_step))
        if ini.has_section("zoom"):
            self.zoom.update({kind: parse_zoom(v) for kind, v in ini["zoom"].items()})
        if ini.has_section("models"):
            self.models = {name.lower(): parse_zoom(v, allow_auto=False) for name, v in ini["models"].items()}

    def _validate(self, path: Path) -> None:
        problems = []
        if self.render_scale not in (1, 2, 3):
            problems.append("render_scale must be 1, 2 or 3")
        if self.mirror_fit not in ("letterbox", "stretch"):
            problems.append("mirror_fit must be letterbox or stretch")
        if unknown := set(self.zoom) - set(KINDS):
            problems.append(f"unknown [zoom] keys: {', '.join(sorted(unknown))}")
        if any(z is not AUTO and z <= 0 for z in [*self.zoom.values(), *self.models.values()]):
            problems.append("zoom values must be positive")
        if problems:
            raise ScreenError(f"Bad config {path}: " + "; ".join(problems))

    # ── zoom rules ──

    def kind(self, o: Output) -> str:
        if o.internal:
            return "laptop"
        return "tv" if o.diagonal_inches >= self.tv_min_inches else "monitor"

    def zoom_source(self, o: Output) -> str:
        if o.model and o.model.lower() in self.models:
            return "model"
        return "auto" if self.zoom.get(self.kind(o)) is AUTO else "fixed"

    def zoom_for(self, o: Output) -> float:
        source = self.zoom_source(o)
        if source == "model":
            return self.models[o.model.lower()]
        if source == "fixed":
            return self.zoom[self.kind(o)]
        return self.auto_zoom(o)

    def auto_zoom(self, o: Output) -> float:
        """Laptop/monitor: physical DPI / target DPI. TVs and screens that don't
        report a size: make the screen tv_logical_height logical pixels tall."""
        kind = self.kind(o)
        if kind == "tv" or o.dpi is None:
            raw = o.mode.height / self.tv_logical_height
        else:
            raw = o.dpi / self.target_dpi[kind]
        return max(1.0, round(raw / self.zoom_step) * self.zoom_step)
