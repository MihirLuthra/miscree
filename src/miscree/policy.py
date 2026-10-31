"""The rules: what each shortcut and each plug/unplug does."""

from __future__ import annotations

from miscree import system, xrandr
from miscree.config import Config
from miscree.layout import Layout, Planner
from miscree.model import Output

TARGETS = ("laptop", "external")


class Screens:
    """A snapshot of the connected screens plus the actions you can take on them."""

    def __init__(self, outputs: list[Output], config: Config, render_scale: float):
        self.outputs = outputs
        self.config = config
        self.planner = Planner(config, render_scale)
        self.laptop = next((o for o in outputs if o.internal and o.usable), None)
        self.externals = [o for o in outputs if not o.internal and o.usable]
        self.external = next((o for o in self.externals if o.enabled),
                             self.externals[0] if self.externals else None)

    @classmethod
    def detect(cls) -> "Screens":
        return cls(xrandr.query_outputs(), Config.load(), xrandr.render_scale())

    # ── actions ──

    def turn_on(self, target: str) -> None:
        """On. If the other screen is on too: mirror, sized for this one."""
        screen, other = self._pick(target)
        if screen is None:
            return system.notify(f"No {target} screen connected")
        if other and other.enabled:
            self._show(self.planner.mirror(lead=screen, follower=other))
        else:
            self._show([self.planner.single(screen)])

    def turn_off(self, target: str) -> None:
        """Off. The remaining screen is re-sized for itself; the last one is blanked."""
        screen, other = self._pick(target)
        if screen is None or not screen.enabled:
            return system.notify(f"The {target} screen is already off")
        if other and other.enabled:
            self._show([self.planner.single(other)])
        else:
            system.blank_screen()

    def startup(self) -> None:
        """Login: both screens mirrored, sized for the laptop; otherwise whichever is connected."""
        system.save_seen({o.name for o in self.externals})
        if self.laptop and self.external:
            self._show(self.planner.mirror(lead=self.laptop, follower=self.external))
        else:
            self.default()

    def hotplug(self) -> None:
        """Plugged in -> that screen alone. Unplugged, or nothing left on -> default.
        Every other output event (including our own xrandr calls) is ignored."""
        now = {o.name for o in self.externals}
        seen = system.load_seen()
        system.save_seen(now)
        if seen is None:
            return self.default()
        added, removed = now - seen, seen - now
        enabled = {o.name for o in self.outputs if o.enabled}
        if added:
            newest = next(o for o in self.externals if o.name in added)
            self._show([self.planner.single(newest)])
        elif removed or not enabled & {o.name for o in self.outputs if o.usable}:
            if self.laptop and enabled == {self.laptop.name}:
                return
            self.default()

    def default(self) -> None:
        """The external screen alone if one is plugged in, otherwise the laptop."""
        screen = self.external or self.laptop
        if screen:
            self._show([self.planner.single(screen)])

    # ── reporting ──

    def describe(self) -> str:
        rows = [("OUTPUT", "STATE", "KIND", "MODEL", "SIZE", "NATIVE", "ZOOM", "LOGICAL")]
        for o in self.outputs:
            if not o.usable:
                continue
            rows.append((
                o.name,
                "on" if o.enabled else "off",
                self.config.kind(o),
                o.model or "-",
                f'{o.diagonal_inches:.1f}"' if o.mm[0] else "?",
                f"{o.mode.name}@{o.mode.rate:.0f}",
                f"{self.config.zoom_for(o):.3g} ({self.config.zoom_source(o)})",
                "x".join(map(str, self.planner.logical_size(o))),
            ))
        widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
        table = "\n".join("  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows)
        footer = f"render scale {self.planner.render_scale:g}"
        if self.planner.render_scale != self.config.render_scale:
            footer += f" (config wants {self.config.render_scale}: log out and back in to apply)"
        return f"{table}\n\n{footer}"

    # ── helpers ──

    def _pick(self, target: str) -> tuple[Output | None, Output | None]:
        return (self.laptop, self.external) if target == "laptop" else (self.external, self.laptop)

    def _show(self, candidates: list[Layout]) -> None:
        layout = xrandr.apply(candidates, self.outputs)
        print(f"miscree: {layout.description}")
