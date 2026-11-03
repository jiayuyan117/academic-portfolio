"""Record executed source/optimization audits without changing model outputs."""
import csv
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from skill_extraction import load, save, digest


def main():
    folder = ROOT / ".runtime/source-reconstruction"
    audit = load(folder / "source_audit.json")
    matches = {}
    for name in ("jobs.csv", "skillspan_train.csv", "skillspan_dev.csv", "skillspan_test.csv"):
        with (ROOT / "data/full" / name).open(encoding="utf-8", newline="") as stream:
            delivered = list(csv.DictReader(stream))
        with (folder / name).open(encoding="utf-8", newline="") as stream:
            reconstructed = list(csv.DictReader(stream))
        matches[name] = delivered == reconstructed
    if not all(matches.values()):
        raise ValueError("A reconstructed input differs from the delivered data")
    save(ROOT / "results/source_audit.json", {**audit, "all_fields_and_order_match_delivery": matches})
    import joblib
    optimization = {}
    for channel in ("skill", "knowledge"):
        # Only load models produced by this local training invocation.
        classifier = joblib.load(ROOT / ".runtime/extraction" / f"{channel}_classifier.joblib")
        optimization[channel] = {
            "iterations": classifier.n_iter_.tolist(), "iteration_limit": int(classifier.max_iter),
            "convergence_warning": bool(max(classifier.n_iter_) >= classifier.max_iter),
        }
    save(ROOT / "results/extraction/optimization.json", optimization)
    save(ROOT / "results/environment.json", {
        "python": platform.python_version(), "platform": platform.system(),
        "packages": {name: importlib.metadata.version(name) for name in
                     ("numpy", "pandas", "scipy", "scikit-learn", "matplotlib", "joblib", "threadpoolctl")},
        "requirements_sha256": digest(ROOT / "requirements.txt"),
    })
    print("Source reconstruction and executed optimization budgets recorded")


if __name__ == "__main__":
    main()
