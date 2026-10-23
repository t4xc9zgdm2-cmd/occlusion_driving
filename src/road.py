import math
import random


class Road:
    """Winding road defined by a sum of sines.

    Road coordinates:
      s: distance along the road (m)
      x: lateral offset from the road centerline (m, positive = right)

    Curvature sign:
      curvature < 0 -> left curve  -> inside edge is the LEFT edge (side=-1)
      curvature > 0 -> right curve -> inside edge is the RIGHT edge (side=+1)
    """

    def __init__(self, seed: int, width: float = 7.0, length: float = 1000.0):
        rng = random.Random(seed)
        self.seed = seed
        self.width = width
        self.length = length

        # Two sine components make a road that is not a single perfect arc.
        self.a1 = rng.uniform(6.0, 10.0)
        self.l1 = rng.uniform(100.0, 150.0)
        self.p1 = rng.uniform(0.0, 2.0 * math.pi)
        self.a2 = rng.uniform(2.0, 4.0)
        self.l2 = rng.uniform(45.0, 75.0)
        self.p2 = rng.uniform(0.0, 2.0 * math.pi)

    def center_x(self, s: float) -> float:
        w1 = 2.0 * math.pi / self.l1
        w2 = 2.0 * math.pi / self.l2
        return self.a1 * math.sin(w1 * s + self.p1) + self.a2 * math.sin(w2 * s + self.p2)

    def center_dx(self, s: float) -> float:
        w1 = 2.0 * math.pi / self.l1
        w2 = 2.0 * math.pi / self.l2
        return self.a1 * w1 * math.cos(w1 * s + self.p1) + self.a2 * w2 * math.cos(w2 * s + self.p2)

    def center_ddx(self, s: float) -> float:
        w1 = 2.0 * math.pi / self.l1
        w2 = 2.0 * math.pi / self.l2
        return -self.a1 * w1 * w1 * math.sin(w1 * s + self.p1) - self.a2 * w2 * w2 * math.sin(w2 * s + self.p2)

    def curvature(self, s: float) -> float:
        dx = self.center_dx(s)
        ddx = self.center_ddx(s)
        return ddx / ((1.0 + dx * dx) ** 1.5)

    def edge_x(self, s: float, side: int) -> float:
        """side = -1 left edge, side = +1 right edge."""
        return self.center_x(s) + side * self.width / 2.0

    def lateral_offset(self, car_s: float, car_x: float, car_heading: float, s: float, point_x: float) -> float:
        """Lateral offset of a world point from the car, in the car frame.

        car_heading is relative to the road tangent at car_s. The road tangent
        angle at car_s must be added before projecting the world x difference;
        otherwise a road with a non-zero slope appears shifted sideways.
        """
        psi = math.atan(self.center_dx(car_s)) + car_heading
        ds = s - car_s
        dx = point_x - self.center_x(car_s) - car_x
        return dx - ds * math.tan(psi)

    def inside_side(self, s: float, fallback: int = 1) -> int:
        c = self.curvature(s)
        if c < -1e-4:
            return -1
        if c > 1e-4:
            return 1
        return fallback
