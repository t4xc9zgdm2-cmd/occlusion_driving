import argparse
import os
import sys
from pathlib import Path

# Must be set before pygame initializes the display.
if "--smoke-test" in sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.config import Config
from src.experiment import Experiment


def main() -> None:
    parser = argparse.ArgumentParser(description="Occlusion driving experiment")
    parser.add_argument("--participant", "-p", default=None, help="Participant ID, e.g. P01")
    parser.add_argument("--debug", action="store_true", help="Show tangent/mask/error overlay")
    parser.add_argument("--smoke-test", action="store_true", help="Headless 3-trial smoke test")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    config_path = Path(args.config) if args.config else root / "config.yaml"
    config = Config.load(config_path)

    participant = args.participant
    if not participant:
        participant = "SMOKE" if args.smoke_test else (input("Participant ID: ").strip() or "P00")

    exp = Experiment(config, participant, debug=args.debug, smoke_test=args.smoke_test)
    exp.run()


if __name__ == "__main__":
    main()
