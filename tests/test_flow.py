import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import Config
from src.experiment import Experiment


def main():
    cfg = Config()
    cfg.data_dir = str(ROOT / "data" / "test_flow")
    cfg.trial_seconds = 1.0
    cfg.practice_seconds = 1.0
    cfg.practice_trials = 0
    cfg.trials_per_condition = 1
    cfg.seeds = [101]
    cfg.conditions = ["full", "tangent", "control"]

    exp = Experiment(cfg, "FLOW", debug=False, smoke_test=False)
    # Skip human-in-the-loop screens for this automated flow test.
    exp._start_screen = lambda: True
    exp._countdown = lambda n: None
    exp._wait_for_space = lambda: True
    exp._wait_for_quit = lambda: None
    exp.run()
    print("flow test ok")


if __name__ == "__main__":
    main()
