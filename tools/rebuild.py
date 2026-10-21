"""Rebuild selected Python projects using the invoking interpreter; fail on errors."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = {
    "01": ("01-equity-time-series-forecasting", ["run_analysis.py"]),
    "02": ("02-shanghai-hongkong-market-linkages", ["run_analysis.py"]),
    "03": ("03-china-nev-industry-analytics",
           ["src/nev_visualization.py", "src/build_figures_en.py"]),
    "04": ("04-bike-sharing-interactive-visualization", ["src/build_charts.py"]),
    "05": ("05-beijing-air-quality-seaborn", ["src/analyze.py"]),
    "06": ("06-consumer-behaviour-matplotlib", ["src/analyze.py"]),
}


def main() -> None:
    """Run selected projects with this interpreter, stopping on the first failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", choices=PROJECTS, action="append",
                        help="Repeat to select projects; default: all Python projects.")
    args = parser.parse_args()
    env = os.environ.copy()
    env.update(PYTHONUTF8="1", MPLBACKEND="Agg", OPENBLAS_NUM_THREADS="1",
               OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
    for number in args.project or PROJECTS:
        folder, scripts = PROJECTS[number]
        for script in scripts:
            print(f"[{number}] {script}", flush=True)
            subprocess.run([sys.executable, script], cwd=ROOT / "projects" / folder,
                           env=env, check=True)


if __name__ == "__main__":
    main()
