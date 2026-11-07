import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Tuple

import yaml


@dataclass
class Config:
    # Display
    screen_width: int = 1280
    screen_height: int = 720
    fps: int = 60

    # Camera / projection
    fov_deg: float = 105.0
    camera_height: float = 1.2
    horizon_frac: float = 0.42

    # First-person cockpit. These occlude the near-field road the way a real
    # dashboard/hood does, so the driver cannot use the area just ahead of the
    # bumper as a lane-keeping anchor.
    hood_height_frac: float = 0.24      # hood top above the bottom edge
    hood_top_width_frac: float = 0.40
    hood_bottom_width_frac: float = 0.60
    dashboard_height_frac: float = 0.13

    # Road / vehicle
    road_width: float = 7.0
    road_length: float = 1000.0
    speed: float = 11.0                # m/s (~39.6 km/h)
    wheelbase: float = 2.6
    max_steer_deg: float = 10.0
    steer_tau: float = 0.18            # s, smoothing when steering
    steer_return_tau: float = 0.14     # s, smoothing when returning to center

    # Experiment
    trial_seconds: float = 30.0
    practice_seconds: float = 20.0
    trials_per_condition: int = 3
    practice_trials: int = 2
    conditions: List[str] = field(default_factory=lambda: ["full", "tangent", "control"])
    seeds: List[int] = field(default_factory=lambda: [101, 202, 303])

    # Mask
    mask_radius_frac: float = 0.13     # max radius, fraction of screen height
    mask_min_frac: float = 0.06        # min radius, fraction of screen height
    mask_cover_frac: float = 1.10      # radius as fraction of projected half
                                       # road width at the tangent distance
    mask_style: str = "black"          # black | solid | mosaic | blur
    mask_color: Tuple[int, int, int] = (110, 110, 110)  # used by "solid"

    # Misc
    data_dir: str = "data"
    debug: bool = False

    def __post_init__(self):
        self.mask_color = tuple(int(c) for c in self.mask_color)
        self.mask_style = str(self.mask_style).lower()
        if self.mask_style not in {"black", "solid", "mosaic", "blur"}:
            raise ValueError(f"Unknown mask_style: {self.mask_style}")
        self.conditions = list(self.conditions)
        self.seeds = [int(s) for s in self.seeds]

    @property
    def max_steer_rad(self) -> float:
        return math.radians(self.max_steer_deg)

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        allowed = cls.__dataclass_fields__.keys()
        clean = {k: v for k, v in data.items() if k in allowed}
        return cls(**clean)

    def to_dict(self) -> dict:
        return asdict(self)
