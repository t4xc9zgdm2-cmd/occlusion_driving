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


class MaskController:
    """Build the screen-space mask for the current condition.

    conditions:
      full    -> no mask
      tangent -> mask centred on the tangent point (inside edge)
      control -> mask on the same inside edge, shifted along the road
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
        if condition == "full":
            return MaskState("full", None, 0, tangent)

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
        radius = int(self.config.screen_height * self.config.mask_radius_frac)
        return MaskState(condition, center, radius, tangent, s)
