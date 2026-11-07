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
        self.cy = config.screen_height * config.horizon_frac
        pitch = math.radians(config.camera_pitch_deg)
        self.sin_pitch, self.cos_pitch = math.sin(pitch), math.cos(pitch)
        self.horizon = self.cy + self.f * math.tan(pitch)
        self.camera_height = config.camera_height

    def project(self, road: Road, car: Vehicle, s: float, x: float) -> Optional[Tuple[int, int]]:
        z = s - car.s
        if z <= 0.5:
            return None
        lat = road.lateral_offset(car.s, car.x, car.heading, s, x) - self.config.camera_lateral_offset
        depth = z * self.cos_pitch - self.camera_height * self.sin_pitch
        if depth <= 0.5:
            return None
        sx = self.cx + self.f * lat / depth
        sy = self.cy + self.f * (self.camera_height * self.cos_pitch + z * self.sin_pitch) / depth
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
        self.horizon = self.projector.horizon
        self.f = self.projector.f
        self.h = config.camera_height

        self.sky = (164, 186, 192)
        self.ground = (83, 103, 70)
        self.road_color = (104, 105, 102)
        self.edge_color = (120, 119, 108)
        self.hood_color = (25, 25, 25)
        self.dashboard_color = (16, 16, 20)
        self.text_color = (240, 240, 240)
        self.cockpit = self._build_cockpit()
        self.wheel = self._build_wheel()
        self.landscape = self._build_landscape()

    def _build_landscape(self) -> pygame.Surface:
        """Cache the featureless sky; moving terrain is drawn separately."""
        w, h = self.config.screen_width, self.config.screen_height
        layer = pygame.Surface((w, h))
        horizon = int(self.horizon)
        for y in range(horizon + 1):
            t = y / max(1, horizon)
            color = tuple(int(a+(b-a)*t) for a,b in zip((145,174,187),(204,211,199)))
            pygame.draw.line(layer, color, (0,y), (w,y))
        pygame.draw.rect(layer, self.ground, (0,horizon,w,h-horizon))
        return layer

    def _draw_mountains(self, road: Road, car: Vehicle) -> None:
        """Approximate distant parallax, anchored to the world rather than keys.

        Actual view heading includes road tangent and relative vehicle heading.
        Continuous ridge functions extend beyond both edges, so turning cannot
        expose a blank strip or trigger a visible panorama wrap.
        """
        w, h = self.config.screen_width, self.config.screen_height
        yaw = math.atan(road.center_dx(car.s)) + car.heading
        world_x = road.center_x(car.s) + car.x + self.config.camera_lateral_offset
        for distance, base, amplitude, color in [
            (1600.0, .016, .075, (139,156,145)),
            (650.0, .006, .043, (112,136,116)),
        ]:
            # Turning right moves the terrain left. Translation has a much
            # smaller effect, with slightly more parallax in the nearer layer.
            shift = self.f * (yaw + world_x / distance)
            scale = 1.0 + min(max(car.s, 0.0), 1000.0) / (distance * 12.0)
            ridge = []
            for x in range(-8, w + 9, 8):
                u = .5 + ((x + shift) / w - .5) / scale
                profile = .50 + .24*math.sin(u*9.0+.8) + .16*math.sin(u*21.0+1.7) + .07*math.sin(u*39.0)
                y = self.horizon - h * (base + amplitude * profile * scale)
                ridge.append((x, int(y)))
            ridge.extend([(w+8, int(self.horizon)), (-8, int(self.horizon))])
            pygame.draw.polygon(self.screen, color, ridge)

    def draw_scene(self, road: Road, car: Vehicle, mask, info: dict, debug: bool = False) -> None:
        w, h = self.config.screen_width, self.config.screen_height
        self.screen.blit(self.landscape, (0, 0))
        self._draw_mountains(road, car)
        self._draw_road(road, car)
        self._draw_mask(mask)
        if debug and getattr(mask, "tangent", None) is not None:
            p = self.projector.project(road, car, mask.tangent.s, mask.tangent.x)
            if p:
                x, y = p
                pygame.draw.line(self.screen, (255, 230, 0), (x - 9, y), (x + 9, y), 2)
                pygame.draw.line(self.screen, (255, 230, 0), (x, y - 9), (x, y + 9), 2)
        self._draw_cockpit(car)
        self._draw_hud(car, mask, info, debug)

    def _draw_road(self, road: Road, car: Vehicle) -> None:
        h = self.config.screen_height
        left_pts = []
        right_pts = []

        for y in range(int(self.horizon) + 1, h):
            q = (y - self.projector.cy) / self.f
            cp, sp = self.projector.cos_pitch, self.projector.sin_pitch
            z = self.h * (cp + q * sp) / max(1e-6, q * cp - sp)
            if z > 220.0:
                continue

            s = car.s + z
            center_lat = road.lateral_offset(car.s, car.x, car.heading, s, road.center_x(s)) - self.config.camera_lateral_offset
            left = center_lat - road.width / 2.0
            right = center_lat + road.width / 2.0

            depth = z * cp - self.h * sp
            sx_l = self.cx + self.f * left / depth
            sx_r = self.cx + self.f * right / depth

            # Road fill for this scanline.
            pygame.draw.line(self.screen, self.road_color, (sx_l, y), (sx_r, y), 1)
            left_pts.append((int(sx_l), y))
            right_pts.append((int(sx_r), y))

        # Intentionally no dashed centerline. A bright line running under the
        # car is an artificial lane-keeping anchor and lets participants ignore
        # the far road/tangent point.

        if len(left_pts) > 1:
            pygame.draw.lines(self.screen, self.edge_color, False, left_pts, 1)
            pygame.draw.lines(self.screen, self.edge_color, False, right_pts, 1)

    def _build_cockpit(self) -> pygame.Surface:
        """Cache fixed cabin geometry; all coordinates scale with the window."""
        w, h = self.config.screen_width, self.config.screen_height
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        def poly(color, points):
            pygame.draw.polygon(layer, color, [(int(x*w), int(y*h)) for x, y in points])
        # Low eye point: a broad foreshortened hood is visible beyond the
        # windshield seal. Its curved front lip, rather than a road overlay,
        # determines the nearest visible road distance.
        top = 1.0 - self.config.hood_height_frac
        # Smooth crowned bonnet: continuous cross-section, with a soft sky
        # reflection and a dark falloff toward the windshield. Baked once.
        hood_edge = []
        glass_edge = []
        pad_edge = []
        for x in range(w):
            u = x / max(1, w-1)
            front = (top + .26*(u-.59)**2)*h
            rear = (top + .108 + .095*(u-.27)**2)*h
            pad = rear + .027*h
            hood_edge.append((x, int(front)))
            glass_edge.append((x, int(rear)))
            pad_edge.append((x, int(pad)))
            for y in range(int(front), int(rear)+1):
                t = (y-front)/max(1,rear-front)
                reflection = 22*math.exp(-((t-.23)/.26)**2)
                crown = 9*math.exp(-((u-.57)/.43)**2)
                shade = 47 + crown + reflection - 19*t
                layer.set_at((x,y),(int(shade),int(shade+9),int(shade+13),255))
            pygame.draw.line(layer,(10,17,21),(x,int(rear)),(x,int(rear+.009*h)))
            for y in range(int(rear+.009*h), int(pad)+1):
                t = (y-rear)/max(1,pad-rear)
                shade = int(43-9*t)
                layer.set_at((x,y),(shade,shade+7,shade+11,255))
            pygame.draw.line(layer,(32,39,43),(x,int(pad)),(x,h))
        pygame.draw.aalines(layer,(99,111,115),False,hood_edge)
        pygame.draw.aalines(layer,(66,78,83),False,glass_edge)
        pygame.draw.aalines(layer,(51,62,68),False,pad_edge)
        # Low-profile curved wipers sit at the glass base.
        for start,end in [(.19,.44),(.57,.82)]:
            points=[]
            for i in range(41):
                u=start+(end-start)*i/40
                yy=(top+.108+.095*(u-.27)**2-.004)*h
                points.append((int(u*w),int(yy)))
            pygame.draw.lines(layer,(17,24,28),False,points,3)
            pygame.draw.aalines(layer,(52,63,68),False,points)
        dash=top+.17
        for y in range(int(dash*h),h):
            shade=int(34-16*(y-dash*h)/max(1,h-dash*h))
            pygame.draw.line(layer,(shade,shade+5,shade+9),(0,y),(w,y))
        # Instrument binnacle projects toward the driver, below the glass.
        poly((12,18,23),[(.16,dash+.09),(.19,dash+.015),(.25,dash-.025),(.44,dash-.025),(.51,dash+.03),(.53,dash+.10)])
        # Reference framing: only the lower left A-pillar enters the image.
        # Its foot joins the door at the screen edge, not a second strip of
        # forward-facing dashboard with exterior road visible to its left.
        poly((10,17,21),[(0,top-.035),(.045,top+.045),(.115,top+.15),(.10,1),(0,1)])
        poly((27,35,40),[(0,top+.08),(.052,top+.15),(.077,1),(0,1)])
        poly((15,22,26),[(0,top-.21),(.018,top-.17),(.145,top+.105),(.12,top+.18),(.077,top+.185),(0,top+.075)])
        poly((143,148,141),[(0,top-.19),(.009,top-.17),(.131,top+.10),(.112,top+.155),(.087,top+.16),(0,top+.045)])
        poly((171,175,163),[(0,top-.17),(.008,top-.155),(.124,top+.10),(.112,top+.12),(.097,top+.105)])
        poly((16,23,27),[(1.16,0),(1.20,0),(1,top+.23),(.96,top+.17)])
        poly((120,130,126),[(1.17,.08),(1.185,.10),(.989,top+.20),(.975,top+.17)])
        for x,width in [(.065,.10),(.65,.13),(.84,.15)]:
            rect=pygame.Rect(int(x*w),int((dash+.035)*h),int(width*w),int(.061*h))
            pygame.draw.rect(layer,(87,96,99),rect,border_radius=6)
            pygame.draw.rect(layer,(8,15,20),rect.inflate(-5,-5),border_radius=5)
            for i in range(1,5):
                yy=rect.y+int(rect.h*i/5)
                pygame.draw.line(layer,(56,66,71),(rect.x+7,yy),(rect.right-7,yy),2)
        # Recessed, unlit center console adds depth without driving guidance.
        poly((8,15,21),[(.67,dash+.13),(.85,dash+.14),(.87,1),(.66,1)])
        poly((20,31,40),[(.69,dash+.15),(.83,dash+.16),(.84,dash+.27),(.68,dash+.26)])
        pygame.draw.line(layer,(74,83,86),(int(.75*w),int((dash+.14)*h)),(w,int((dash+.16)*h)),2)
        return layer

    def _build_wheel(self) -> pygame.Surface:
        size = max(100, int(min(self.config.screen_width*.31, self.config.screen_height*.57)))
        wheel = pygame.Surface((size, size), pygame.SRCALPHA)
        c, r = size//2, int(size*.45)
        pygame.draw.circle(wheel, (8,12,15), (c,c), r, max(9,int(size*.063)))
        pygame.draw.circle(wheel, (68,75,78), (c,c), r, 2)
        pygame.draw.circle(wheel, (31,37,40), (c,c), int(r*.87), 2)
        for angle in (0, 180, 90):
            t = math.radians(angle)
            end = (int(c+math.cos(t)*r*.91), int(c+math.sin(t)*r*.91))
            pygame.draw.line(wheel, (12,17,21), (c,c), end, int(size*.095))
            pygame.draw.line(wheel, (63,70,73), (c,c), end, max(2,int(size*.018)))
        pygame.draw.ellipse(wheel, (19,25,29), (int(size*.32),int(size*.35),int(size*.36),int(size*.31)))
        pygame.draw.arc(wheel, (72,79,82), (int(size*.33),int(size*.36),int(size*.34),int(size*.28)), .15, 2.9, 2)
        label = self.small.render('AIRBAG', True, (112,120,123))
        wheel.blit(label, (c-label.get_width()//2, int(size*.52)))
        return wheel

    def _draw_cockpit(self, car: Vehicle) -> None:
        w, h = self.config.screen_width, self.config.screen_height
        self.screen.blit(self.cockpit, (0,0))
        # A fixed speedometer supplies no road curvature or lateral-error cue.
        center = (int(.37*w), int((1-self.config.hood_height_frac+.19)*h))
        radius = int(.061*h)
        pygame.draw.circle(self.screen, (6,12,16), center, radius)
        pygame.draw.circle(self.screen, (87,99,101), center, radius, 2)
        for value in range(0,121,20):
            angle = math.radians(150 + value*2)
            p1 = (int(center[0]+math.cos(angle)*radius*.76), int(center[1]+math.sin(angle)*radius*.76))
            p2 = (int(center[0]+math.cos(angle)*radius*.9), int(center[1]+math.sin(angle)*radius*.9))
            pygame.draw.line(self.screen, (158,174,173), p1,p2,2)
        angle = math.radians(150 + min(120, car.speed*3.6)*2)
        tip = (int(center[0]+math.cos(angle)*radius*.7),int(center[1]+math.sin(angle)*radius*.7))
        pygame.draw.line(self.screen, (192,124,100), center,tip,2)
        # Positive model steering moves right on screen; pygame positive rotation
        # is counterclockwise, hence the negative sign. Use actual smoothed steer.
        rotated = pygame.transform.rotozoom(self.wheel, -math.degrees(car.steer)*self.config.steering_wheel_ratio, 1)
        self.screen.blit(rotated, rotated.get_rect(center=(int(.37*w),int(.865*h))))

    def _draw_mask(self, mask) -> None:
        if getattr(mask, "condition", "full") == "full":
            return
        center = getattr(mask, "center", None)
        radius = int(getattr(mask, "radius", 0))
        if center is None or radius <= 0:
            return

        style = getattr(mask, "style", self.config.mask_style)
        if style == "black":
            pygame.draw.circle(self.screen, (0, 0, 0), center, radius)
        elif style == "solid":
            pygame.draw.circle(self.screen, self.config.mask_color, center, radius)
        elif style in ("mosaic", "blur"):
            self._draw_textured_mask(center, radius, style)
        else:
            raise ValueError(f"Unknown mask style: {style}")

    def _draw_textured_mask(
        self,
        center: Tuple[int, int],
        radius: int,
        style: str,
    ) -> None:
        """Cover the tangent area with mosaic/blur, clipped to a circle."""
        w, h = self.config.screen_width, self.config.screen_height
        cx, cy = center
        left = max(0, cx - radius)
        top = max(0, cy - radius)
        right = min(w, cx + radius + 1)
        bottom = min(h, cy + radius + 1)
        rect = pygame.Rect(left, top, right - left, bottom - top)
        if rect.w < 2 or rect.h < 2:
            return

        region = self.screen.subsurface(rect).copy()
        if style == "mosaic":
            block = max(4, radius // 5)
            small_w = max(1, rect.w // block)
            small_h = max(1, rect.h // block)
            small = pygame.transform.scale(region, (small_w, small_h))
            effect = pygame.transform.scale(small, (rect.w, rect.h))
        else:
            small_w = max(1, rect.w // 10)
            small_h = max(1, rect.h // 10)
            small = pygame.transform.smoothscale(region, (small_w, small_h))
            effect = pygame.transform.smoothscale(small, (rect.w, rect.h))

        effect = effect.convert_alpha()
        circle = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.circle(
            circle,
            (255, 255, 255, 255),
            (cx - rect.x, cy - rect.y),
            radius,
        )
        effect.blit(circle, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.screen.blit(effect, rect.topleft)

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
            dbg.append(
                f"mask={getattr(mask, 'condition', '?')}  "
                f"center={getattr(mask, 'center', None)}  "
                f"r={getattr(mask, 'radius', 0)}"
            )
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
