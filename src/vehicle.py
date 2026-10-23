import math

from .config import Config
from .road import Road


class Vehicle:
    """Simple kinematic bicycle model in road coordinates.

    heading is relative to the road tangent, so the road curvature appears as a
    disturbance term in dheading/dt.
    """

    def __init__(self, config: Config):
        self.config = config
        self.s = 0.0
        self.x = 0.0
        self.heading = 0.0
        self.steer = 0.0
        self.speed = config.speed
        self.off_road = False

    def update(self, steer_target: float, road: Road, dt: float) -> None:
        # First-order smoothing of the steering command. This is what makes the
        # keyboard usable: the raw key press is binary, the command is not.
        tau = self.config.steer_tau if abs(steer_target) > 1e-6 else self.config.steer_return_tau
        alpha = min(1.0, dt / max(tau, 1e-4))
        self.steer += (steer_target - self.steer) * alpha
        self.steer = max(-self.config.max_steer_rad, min(self.config.max_steer_rad, self.steer))

        curv = road.curvature(self.s)
        yaw_rate = self.speed * math.tan(self.steer) / self.config.wheelbase - curv * self.speed
        self.heading += yaw_rate * dt
        self.heading = max(-0.7, min(0.7, self.heading))

        self.x += self.speed * math.sin(self.heading) * dt
        self.s += self.speed * math.cos(self.heading) * dt
        self.off_road = abs(self.x) > self.config.road_width / 2.0

    @property
    def lateral_error(self) -> float:
        return self.x
