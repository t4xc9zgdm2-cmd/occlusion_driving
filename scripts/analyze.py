import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis import main


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data")
    main(data_dir)
