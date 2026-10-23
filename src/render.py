import math
from typing import Optional, Tuple

import pygame

from .config import Config
from .road import Road
from .vehicle import Vehicle


class Projector:
    """Pinhole projection of road-plane points to screen pixels."""

    def __init__(self, config: Config):
        self.config = config
        self.f = (config.screen_width / 2.0) / math.tan(math.radians(config.fov_deg) / 2.0)
        self.cx = config.screen_width / 2.0
        self.horizon = config.screen_height * config.horizon_frac
        self.camera_height = config.camera_height

    def project(self, road: Road, car: Vehicle, s: float, x: float) -> Optional[Tuple[int, int]]:
        z = s - car.s
        if z <= 0.5:
            return None
        lat = road.lateral_offset(car.s, car.x, car.heading, s, x)
        sx = self.cx + self.f * lat / z
        sy = self.horizon + self.f * self.camera_height / z
        if sy < self.horizon - 2 or sy > self.config.screen_height + 2:
            return None
        return int(round(sx)), int(round(sy))


class Renderer:
    def __init__(self, screen: pygame.Surface, config: Config):
        self.screen = screen
        self.config = config
        self.projector = Projector(config)
        # Default pygame font: avoid SysFont's Windows registry quirks.
        self.font = pygame.font.Font(None, 22)
        self.small = pygame.font.Font(None, 15)
        self.big = pygame.font.Font(None, 42)

        self.cx = config.screen_width / 2.0
        self.horizon = config.screen_height * config.horizon_frac
        self.f = self.projector.f
        self.h = config.camera_height

        self.sky = (120, 170, 220)
        self.ground = (55, 105, 55)
        self.road_color = (72, 72, 72)
        self.edge_color = (242, 242, 242)
        self.center_color = (230, 230, 230)
        self.hood_color = (25, 25, 25)
        self.text_color = (240, 240, 240)

    def draw_scene(self, road: Road, car: Vehicle, mask, info: dict, debug: bool = False) -> None:
        w, h = self.config.screen_width, self.config.screen_height
        self.screen.fill(self.sky)
        pygame.draw.rect(self.screen, self.ground, (0, int(self.horizon), w, h - int(self.horizon)))
        self._draw_road(road, car)
        self._draw_hood()
        self._draw_mask(mask)
        if debug and getattr(mask, "tangent", None) is not None:
            p = self.projector.project(road, car, mask.tangent.s, mask.tangent.x)
            if p:
                x, y = p
                pygame.draw.line(self.screen, (255, 230, 0), (x - 9, y), (x + 9, y), 2)
                pygame.draw.line(self.screen, (255, 230, 0), (x, y - 9), (x, y + 9), 2)
        self._draw_hud(car, mask, info, debug)

    def _draw_road(self, road: Road, car: Vehicle) -> None:
        w, h = self.config.screen_width, self.config.screen_height
        left_pts = []
        right_pts = []

        for y in range(int(self.horizon) + 1, h):
            dy = max(1.0, y - self.horizon)
            z = self.f * self.h / dy
            if z > 220.0:
                continue

            s = car.s + z
            center_lat = road.lateral_offset(car.s, car.x, car.heading, s, road.center_x(s))
            left = center_lat - road.width / 2.0
            right = center_lat + road.width / 2.0

            sx_l = self.cx + self.f * left / z
            sx_r = self.cx + self.f * right / z

            # Road fill for this scanline.
            pygame.draw.line(self.screen, self.road_color, (sx_l, y), (sx_r, y), 1)
            left_pts.append((int(sx_l), y))
            right_pts.append((int(sx_r), y))

            # Dashed centerline.
            if int(z / 4.0) % 2 == 0:
                sx_c = self.cx + self.f * center_lat / z
                pygame.draw.line(self.screen, self.center_color, (sx_c, y), (sx_c, y + 1), 1)

        if len(left_pts) > 1:
            pygame.draw.lines(self.screen, self.edge_color, False, left_pts, 2)
            pygame.draw.lines(self.screen, self.edge_color, False, right_pts, 2)

    def _draw_hood(self) -> None:
        w, h = self.config.screen_width, self.config.screen_height
        cx = w / 2.0
        pts = [
            (int(cx - 280), h),
            (int(cx + 280), h),
            (int(cx + 205), int(h - 92)),
            (int(cx - 205), int(h - 92)),
        ]
        pygame.draw.polygon(self.screen, self.hood_color, pts)
        pygame.draw.line(self.screen, (80, 80, 80), pts[3], pts[2], 2)

    def _draw_mask(self, mask) -> None:
        if getattr(mask, "condition", "full") == "full":
            return
        center = getattr(mask, "center", None)
        radius = int(getattr(mask, "radius", 0))
        if center is None or radius <= 0:
            return
        pygame.draw.circle(self.screen, self.config.mask_color, center, radius)
        pygame.draw.circle(self.screen, (65, 65, 65), center, radius, 2)

    def _draw_hud(self, car: Vehicle, mask, info: dict, debug: bool) -> None:
        w, h = self.config.screen_width, self.config.screen_height
        t_left = max(0.0, info["duration"] - info["t"])
        lines = [
            f"Trial {info['index']}/{info['total']}",
            f"Time {t_left:4.1f}s",
            f"Speed {car.speed * 3.6:.0f} km/h",
        ]
        if info.get("practice"):
            lines.append("PRACTICE")
        y = 12
        for line in lines:
            self.screen.blit(self.font.render(line, True, self.text_color), (14, y))
            y += 28

        hint = self.small.render("LEFT / RIGHT  or  A / D", True, (225, 225, 225))
        self.screen.blit(hint, (14, h - 26))

        if debug:
            tangent = getattr(mask, "tangent", None)
            dbg = [
                f"condition={info['condition']}",
                f"x={car.x:+.2f} m  hdg={math.degrees(car.heading):+.1f} deg",
                f"steer={math.degrees(car.steer):+.1f} deg",
            ]
            if tangent is not None:
                dbg.append(f"tangent z={tangent.z:.1f} m  conf={tangent.confidence:.2f}")
            dbg.append(f"mask={getattr(mask, 'condition', '?')}  center={getattr(mask, 'center', None)}")
            y = 12
            for line in dbg:
                surf = self.small.render(line, True, (255, 255, 120))
                self.screen.blit(surf, (w - surf.get_width() - 14, y))
                y += 20

    def draw_message(self, lines, big_first: bool = False) -> None:
        if isinstance(lines, str):
            lines = [lines]
        self.screen.fill((20, 20, 26))

        rendered = []
        for i, line in enumerate(lines):
            font = self.big if (big_first and i == 0) else self.font
            color = (255, 255, 255) if i == 0 else (210, 210, 210)
            surf = font.render(line, True, color)
            rendered.append((surf, font.get_linesize()))

        total_h = sum(h for _, h in rendered)
        y = (self.config.screen_height - total_h) // 2
        for surf, line_h in rendered:
            x = (self.config.screen_width - surf.get_width()) // 2
            self.screen.blit(surf, (x, y))
            y += line_h
        pygame.display.flip()
