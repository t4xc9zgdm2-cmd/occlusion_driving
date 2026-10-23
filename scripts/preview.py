import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame

from src.config import Config
from src.road import Road
from src.vehicle import Vehicle
from src.tangent import TangentEstimator
from src.mask import MaskController
from src.render import Renderer


def main() -> None:
    cfg = Config.load(ROOT / "config.yaml")
    pygame.init()
    screen = pygame.display.set_mode((cfg.screen_width, cfg.screen_height))
    renderer = Renderer(screen, cfg)

    road = Road(101, cfg.road_width, cfg.road_length)
    car = Vehicle(cfg)
    # Drive ~2 s with a simple lane-keeping controller so the car is on a bend.
    for _ in range(120):
        target = cfg.max_steer_rad * max(-1.0, min(1.0, -0.8 * car.x - 1.6 * car.heading))
        car.update(target, road, 1.0 / 60.0)

    tangent = TangentEstimator(cfg).find(road, car)
    mask_ctrl = MaskController(cfg)

    for condition in cfg.conditions:
        mask = mask_ctrl.update(condition, road, car, tangent, renderer.projector)
        info = {
            "index": 1,
            "total": 1,
            "t": 0.0,
            "duration": cfg.trial_seconds,
            "practice": False,
            "condition": condition,
        }
        renderer.draw_scene(road, car, mask, info, debug=True)
        pygame.display.flip()
        out = ROOT / "data" / f"preview_{condition}.png"
        pygame.image.save(screen, str(out))
        print(out)

    pygame.quit()


if __name__ == "__main__":
    main()
