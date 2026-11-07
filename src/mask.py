from dataclasses import dataclass
from typing import Optional, Tuple

from .config import Config
from .road import Road
from .vehicle import Vehicle
from .tangent import TangentPoint
from .render import Projector


@dataclass
class MaskState:
    condition: str
    center: Optional[Tuple[int, int]]
    radius: int
    tangent: Optional[TangentPoint] = None
    control_s: Optional[float] = None
    style: str = "black"


class MaskController:
    """Build the screen-space mask for the current condition.

    conditions:
      full    -> no mask
      tangent -> mask centred on the tangent point (inside edge)
      control -> mask on the opposite edge at the same longitudinal position
    """

    def __init__(self, config: Config):
        self.config = config

    def update(
        self,
        condition: str,
        road: Road,
        car: Vehicle,
        tangent: TangentPoint,
        projector: Projector,
    ) -> MaskState:
        style = self.config.mask_style
        if condition == "full":
            return MaskState("full", None, 0, tangent, None, style)

        if condition == "tangent":
            s = tangent.s
            side = tangent.side
        elif condition == "control":
            # Opposite edge at the same longitudinal position. A shift of only
            # 2-3 m along the same edge projects to almost the same screen
            # position, so it would not be a usable control mask.
            s = tangent.s
            side = -tangent.side
        else:
            raise ValueError(f"Unknown condition: {condition}")

        x = road.edge_x(s, side)
        center = projector.project(road, car, s, x)

        # A fixed pixel radius becomes a full-road occlusion when the tangent is
        # far away, because the projected road is narrow. Scale the radius to
        # the projected half-road width at the tangent distance, then clamp it.
        z = max(tangent.z, 1e-3)
        depth = max(0.5, z * projector.cos_pitch - projector.camera_height * projector.sin_pitch)
        half_road_px = projector.f * (road.width / 2.0) / depth
        radius = int(round(half_road_px * self.config.mask_cover_frac))
        min_radius = int(round(self.config.screen_height * self.config.mask_min_frac))
        max_radius = int(round(self.config.screen_height * self.config.mask_radius_frac))
        radius = max(min_radius, min(max_radius, radius))

        return MaskState(condition, center, radius, tangent, s, style)
