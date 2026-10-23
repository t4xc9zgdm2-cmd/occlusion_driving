import math
from dataclasses import dataclass

from .config import Config
from .road import Road
from .vehicle import Vehicle


@dataclass
class TangentPoint:
    s: float
    x: float
    z: float
    bearing: float
    side: int
    confidence: float


class TangentEstimator:
    """Estimate the tangent point on the inside edge by a bearing extremum.

    The tangent point is the point on the inside edge whose bearing is closest
    to the car's heading (minimum |bearing|). For a left curve the left edge's
    bearings are negative and the tangent is the least negative; for a right
    curve the right edge's bearings are positive and the tangent is the least
    positive. This is a discrete approximation; confidence is a prominence
    measure, not a calibrated probability.
    """

    def __init__(self, config: Config):
        self.config = config
        self.last_side = 1

    def _side(self, road: Road, car: Vehicle) -> int:
        # Look a little ahead so the side does not flip at every inflection.
        c = road.curvature(car.s + 8.0)
        if c < -0.002:
            side = -1
        elif c > 0.002:
            side = 1
        else:
            side = self.last_side
        self.last_side = side
        return side

    def _bearing(self, road: Road, car: Vehicle, side: int, z: float) -> float:
        s = car.s + z
        ex = road.edge_x(s, side)
        lat = road.lateral_offset(car.s, car.x, car.heading, s, ex)
        return math.atan2(lat, z)

    def find(
        self,
        road: Road,
        car: Vehicle,
        z_min: float = 5.0,
        z_max: float = 55.0,
        n: int = 220,
    ) -> TangentPoint:
        side = self._side(road, car)
        best = None
        best_i = 0
        bearings = []

        for i in range(n):
            z = z_min + (z_max - z_min) * i / (n - 1)
            b = self._bearing(road, car, side, z)
            bearings.append(b)
            s = car.s + z
            ex = road.edge_x(s, side)
            if best is None:
                best = (s, ex, z, b)
                best_i = i
            elif abs(b) < abs(best[3]):
                best = (s, ex, z, b)
                best_i = i

        # Refine the discrete extremum with a ternary search in the
        # neighbouring interval. This makes the reported bearing a local
        # extremum instead of "the best of 220 samples".
        step = (z_max - z_min) / (n - 1)
        lo = max(z_min, best[2] - step)
        hi = min(z_max, best[2] + step)
        for _ in range(40):
            m1 = lo + (hi - lo) / 3.0
            m2 = hi - (hi - lo) / 3.0
            b1 = self._bearing(road, car, side, m1)
            b2 = self._bearing(road, car, side, m2)
            if abs(b1) < abs(b2):
                hi = m2
            else:
                lo = m1

        z = 0.5 * (lo + hi)
        s = car.s + z
        ex = road.edge_x(s, side)
        b = self._bearing(road, car, side, z)

        b0, b1 = bearings[0], bearings[-1]
        prominence = abs(b - 0.5 * (b0 + b1))
        confidence = min(1.0, prominence / 0.05)
        if best_i == 0 or best_i == n - 1:
            # The extremum is at the end of the sampled interval: not a clean
            # tangent point. Keep it for the mask, but lower the confidence.
            confidence *= 0.3

        return TangentPoint(s=s, x=ex, z=z, bearing=b, side=side, confidence=confidence)
