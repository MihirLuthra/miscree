"""Pure layout planning: which outputs, which transforms. No side effects."""

from __future__ import annotations

from dataclasses import dataclass

from miscree.config import Config
from miscree.model import Output

Matrix = tuple[float, float, float, float, float, float, float, float, float]


def scale_matrix(sx: float, sy: float, tx: float = 0.0, ty: float = 0.0) -> Matrix:
    """xrandr transform mapping output pixels to framebuffer pixels."""
    return (sx, 0.0, tx, 0.0, sy, ty, 0.0, 0.0, 1.0)


IDENTITY = scale_matrix(1, 1)


def format_matrix(m: Matrix) -> str:
    return "none" if m == IDENTITY else ",".join(f"{v:.6g}" for v in m)


@dataclass
class Placement:
    output: Output
    transform: Matrix
    same_as: str | None = None
    primary: bool = False


@dataclass
class Layout:
    description: str
    fb: tuple[int, int]
    placements: list[Placement]

    @property
    def names(self) -> set[str]:
        return {p.output.name for p in self.placements}

    def xrandr_args(self, all_outputs: list[Output]) -> list[str]:
        """Full xrandr arguments: every output in the layout set, every other one off."""
        args = ["--fb", f"{self.fb[0]}x{self.fb[1]}"]
        for p in self.placements:
            mode = p.output.mode
            args += ["--output", p.output.name, "--mode", mode.name, "--rate", f"{mode.rate:.2f}",
                     "--transform", format_matrix(p.transform)]
            args += ["--same-as", p.same_as] if p.same_as else ["--pos", "0x0"]
            if p.primary:
                args.append("--primary")
        for o in all_outputs:
            if o.name not in self.names and (o.enabled or o.connected):
                args += ["--output", o.name, "--off"]
        return args


class Planner:
    """Turns 'show this screen' / 'mirror these two' into concrete layouts.

    Apps render at `render_scale` (Xft.dpi / 96). Each screen gets a framebuffer of
    native size * render_scale / zoom, scaled onto the panel by an xrandr transform.
    """

    def __init__(self, config: Config, render_scale: float):
        self.config = config
        self.render_scale = render_scale

    def logical_size(self, o: Output) -> tuple[int, int]:
        factor = self.render_scale / self.config.zoom_for(o)
        return round(o.mode.width * factor), round(o.mode.height * factor)

    def single(self, o: Output) -> Layout:
        lw, lh = self.logical_size(o)
        transform = scale_matrix(lw / o.mode.width, lh / o.mode.height)
        return Layout(f"{o.name} only", (lw, lh), [Placement(o, transform, primary=True)])

    def mirror(self, lead: Output, follower: Output) -> list[Layout]:
        """Lead is sized for itself; follower shows the same picture fitted to it.
        Returns the configured fit first, the other fit as a fallback."""
        base = self.single(lead)
        lw, lh = base.fb
        fw, fh = follower.mode.width, follower.mode.height
        k = max(lw / fw, lh / fh)
        fits = {
            "letterbox": scale_matrix(k, k, (lw - k * fw) / 2, (lh - k * fh) / 2),
            "stretch": scale_matrix(lw / fw, lh / fh),
        }
        order = sorted(fits, key=lambda fit: fit != self.config.mirror_fit)
        return [
            Layout(f"{lead.name} mirrored to {follower.name} ({fit})", base.fb,
                   base.placements + [Placement(follower, fits[fit], same_as=lead.name)])
            for fit in order
        ]
