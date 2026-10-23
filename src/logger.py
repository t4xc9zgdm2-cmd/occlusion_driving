import csv
import json
import time
from dataclasses import asdict
from pathlib import Path

from .config import Config


class SessionLogger:
    def __init__(self, config: Config, participant: str):
        self.config = config
        stamp = time.strftime("%Y%m%d_%H%M%S")
        self.dir = Path(config.data_dir) / f"{participant}_{stamp}"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.dir / "trials.csv"
        self.f = open(self.csv_path, "w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.f)
        self.writer.writerow([
            "t", "participant", "condition", "trial", "seed",
            "s", "x", "heading", "steer", "speed", "curvature",
            "tangent_s", "tangent_x", "tangent_confidence",
            "mask_x", "mask_y", "off_road", "fps",
        ])
        self.rows = 0
        self.metadata = {
            "participant": participant,
            "started": stamp,
            "config": asdict(config),
            "trial_order": [],
        }

    def log_frame(self, row) -> None:
        self.writer.writerow(row)
        self.rows += 1
        if self.rows % 60 == 0:
            self.f.flush()

    def set_trial_order(self, order) -> None:
        self.metadata["trial_order"] = [
            {"condition": c, "seed": s, "trial": i + 1} for i, (c, s) in enumerate(order)
        ]

    def close(self, extra: dict | None = None) -> None:
        self.f.flush()
        self.f.close()
        if extra:
            self.metadata.update(extra)
        with open(self.dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
