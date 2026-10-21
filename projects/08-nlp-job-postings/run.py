"""Portable task entry point; smoke outputs never replace research results."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def execute(*arguments):
    environment = os.environ.copy()
    environment.update(PYTHONUTF8="1", MPLBACKEND="Agg", OPENBLAS_NUM_THREADS="2", OMP_NUM_THREADS="2")
    subprocess.run([sys.executable, "-B", *arguments], cwd=ROOT, env=environment, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=("data", "reproduce", "verify", "smoke", "report", "test"))
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    if args.task == "data":
        execute("data/download_data.py")
    elif args.task == "reproduce":
        execute("src/classification.py")
        execute("src/skill_extraction.py")
        execute("src/analyze_skills.py")
        execute("src/build_report.py")
        execute("src/verify.py", "--full")
    elif args.task == "verify":
        execute("src/verify.py", *(["--full"] if args.full else []))
    elif args.task == "smoke":
        output = ".runtime/smoke"
        execute("src/classification.py", "--data-dir", "data/sample", "--output-dir", output + "/classification", "--bootstrap", "100")
        execute("src/classification.py", "--stage", "verify", "--data-dir", "data/sample", "--output-dir", output + "/classification")
        execute("src/smoke_extraction.py", "--data-dir", "data/sample", "--output-dir", output + "/extraction")
        execute("src/skill_extraction.py", "--stage", "verify", "--data-dir", "data/sample", "--output-dir", output + "/extraction")
    elif args.task == "report":
        execute("src/build_report.py")
    else:
        execute("-m", "unittest", "discover", "-s", "tests", "-v")


if __name__ == "__main__":
    main()
