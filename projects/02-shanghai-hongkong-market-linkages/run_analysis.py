"""Run this project's shared verifier from any working directory."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))

from portfolio_common.verification import main


if __name__ == "__main__":
    main(ROOT)
