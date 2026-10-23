import random
import time

import pygame

from .config import Config
from .road import Road
from .vehicle import Vehicle
from .tangent import TangentEstimator
from .mask import MaskController
from .render import Renderer
from .input import read_steer_axis
from .logger import SessionLogger


class Experiment:
    def __init__(
        self,
        config: Config,
        participant: str,
        debug: bool = False,
        smoke_test: bool = False,
    ):
        self.config = config
        self.participant = participant
        self.debug = debug or config.debug
        self.smoke_test = smoke_test

        self.screen = None
        self.clock = None
        self.renderer = None
        self.logger = None

    def _init_pygame(self) -> None:
        pygame.init()
        pygame.display.set_caption("Occlusion Driving Experiment")
        self.screen = pygame.display.set_mode((self.config.screen_width, self.config.screen_height))
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(self.screen, self.config)

    def run(self) -> None:
        self._init_pygame()

        if not self.smoke_test:
            if not self._start_screen():
                pygame.quit()
                return

        trials = [(c, s) for c in self.config.conditions for s in self.config.seeds]
        random.shuffle(trials)
        duration = self.config.trial_seconds

        if self.smoke_test:
            trials = [(c, self.config.seeds[0]) for c in self.config.conditions]
            duration = 5.0

        self.logger = SessionLogger(self.config, self.participant)
        self.logger.set_trial_order(trials)

        if not self.smoke_test:
            for i in range(self.config.practice_trials):
                ok = self._run_trial(
                    condition="full",
                    seed=9000 + i,
                    duration=self.config.practice_seconds,
                    practice=True,
                    index=i + 1,
                    total=self.config.practice_trials,
                )
                if not ok:
                    self._finish(aborted=True)
                    return

        for i, (condition, seed) in enumerate(trials):
            ok = self._run_trial(condition, seed, duration, False, i + 1, len(trials))
            if not ok:
                self._finish(aborted=True)
                return

        self._finish(aborted=False)

    def _finish(self, aborted: bool) -> None:
        if self.logger:
            self.logger.close({
                "aborted": aborted,
                "finished": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

        if self.smoke_test:
            print("SMOKE OK")
            if self.logger:
                print(f"data dir: {self.logger.dir}")
        else:
            msg = "Experiment aborted." if aborted else "Experiment complete. Data saved."
            self.renderer.draw_message([msg, "Press ESC or close the window."])
            self._wait_for_quit()
        pygame.quit()

    def _start_screen(self) -> bool:
        lines = [
            "OCCLUSION DRIVING EXPERIMENT",
            f"Participant: {self.participant}",
            "",
            "Keep the car in the center of the road.",
            "Use LEFT / RIGHT arrow keys (or A / D) to steer.",
            "Speed is fixed. Some parts of the road may be masked.",
            "",
            "Press SPACE to start practice.",
            "ESC to quit.",
        ]
        self.renderer.draw_message(lines, big_first=True)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return False
                    if event.key == pygame.K_SPACE:
                        return True
            self.clock.tick(30)

    def _run_trial(
        self,
        condition: str,
        seed: int,
        duration: float,
        practice: bool,
        index: int,
        total: int,
    ) -> bool:
        road = Road(seed, self.config.road_width, self.config.road_length)
        car = Vehicle(self.config)
        tangent_est = TangentEstimator(self.config)
        mask_ctrl = MaskController(self.config)

        if not self.smoke_test:
            self._countdown(3)

        t = 0.0
        fps_est = 0.0
        while t < duration:
            dt = self.clock.tick(self.config.fps) / 1000.0
            dt = min(dt, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return False

            axis = read_steer_axis()
            car.update(axis * self.config.max_steer_rad, road, dt)
            tangent = tangent_est.find(road, car)
            mask = mask_ctrl.update(condition, road, car, tangent, self.renderer.projector)

            info = {
                "index": index,
                "total": total,
                "t": t,
                "duration": duration,
                "practice": practice,
                "condition": condition,
            }
            self.renderer.draw_scene(road, car, mask, info, self.debug)
            pygame.display.flip()

            fps_est = 0.9 * fps_est + 0.1 * (1.0 / max(dt, 1e-4))
            if not practice:
                mx, my = mask.center if mask.center else (-1, -1)
                self.logger.log_frame([
                    round(t, 4), self.participant, condition, index, seed,
                    round(car.s, 4), round(car.x, 4), round(car.heading, 4),
                    round(car.steer, 4), round(car.speed, 3), round(road.curvature(car.s), 5),
                    round(tangent.s, 4), round(tangent.x, 4), round(tangent.confidence, 3),
                    mx, my, int(car.off_road), round(fps_est, 1),
                ])
            t += dt

        if not practice:
            self.logger.f.flush()

        if not self.smoke_test:
            self.renderer.draw_message([
                "PRACTICE COMPLETE" if practice else "TRIAL COMPLETE",
                "Press SPACE to continue.",
            ])
            if not self._wait_for_space():
                return False
        return True

    def _countdown(self, n: int) -> None:
        for i in range(n, 0, -1):
            self.renderer.draw_message([str(i)], big_first=True)
            self._wait_ms(700)
        self.renderer.draw_message(["GO"], big_first=True)
        self._wait_ms(300)

    def _wait_for_space(self) -> bool:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return False
                    if event.key == pygame.K_SPACE:
                        return True
            self.clock.tick(30)

    def _wait_for_quit(self) -> None:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return
            self.clock.tick(30)

    def _wait_ms(self, ms: int) -> None:
        start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start < ms:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return
            self.clock.tick(60)
