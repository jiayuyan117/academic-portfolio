"""Verify committed evidence without retraining or changing expected results."""
import argparse
import csv
import gzip
import json
from pathlib import Path
import numpy as np
from sklearn.model_selection import train_test_split

from classification import verify_outputs as verify_classification
import model_comparison as comparison
from analyze_skills import calculate
from skill_extraction import (
    CHANNELS, METHODS, digest, load, require_equal, scores, validate_spans,
    verify_outputs as verify_extraction,
)

ROOT = Path(__file__).resolve().parents[1]


def verify_comparison_evidence():
    """Recompute comparison metrics using the committed cohort, without raw text."""
    folder = ROOT / "results/comparison"
    with gzip.open(ROOT / "data/cohort.jsonl.gz", "rt", encoding="utf-8") as stream:
        records = [json.loads(line) for line in stream]
    labels = sorted({r["label"] for r in records})
    selected, split_ids = {}, {}
    for split, count in comparison.SIZES.items():
        indices = np.array([i for i, r in enumerate(records) if r["split"] == split])
        if len(indices) > count:
            indices = train_test_split(
                indices, train_size=count, stratify=[records[i]["label"] for i in indices],
                random_state=comparison.SEED,
            )[0]
        require_equal(len(indices), count, "comparison split count")
        selected[split] = indices
        split_ids[split] = [records[i]["id"] for i in indices]
    require_equal(load(folder / "fair_split_ids.json"), split_ids, "comparison selection")
    results = {}
    for name, directory in comparison.MODEL_NAMES.items():
        output = folder / directory
        config = load(output / "run_config.json")
        require_equal(config["status"], "completed", directory)
        signed = dict(config)
        stored_hash = signed.pop("run_config_sha256")
        require_equal(comparison.object_digest(signed), stored_hash, "comparison config")
        require_equal(config["split_ids_sha256"], comparison.object_digest(split_ids), "comparison IDs")
        require_equal(config["split_ids_file_sha256"], digest(folder / "fair_split_ids.json"), "comparison ID file")
        require_equal(config["labels"], labels, "comparison labels")
        require_equal(config["parameters"], comparison.specification(name), "comparison parameters")
        files = ["predictions.csv", "metrics.json"] + comparison.validation_files(name)
        require_equal(sorted(config["output_sha256"]), sorted(files), "comparison artifacts")
        for filename in files:
            require_equal(digest(output / filename), config["output_sha256"][filename], filename)
        for filename, expected in config["source_sha256"].items():
            path = ROOT / filename if filename.startswith("requirements") else ROOT / "src" / filename
            require_equal(digest(path), expected, "comparison source " + filename)
        stored = load(output / "metrics.json")
        require_equal(sorted(stored), ["test", "validation"], "comparison metric sections")
        require_equal(sorted(stored["validation"]), sorted(comparison.validation_files(name)), "validation files")
        scores = []
        for filename, split in [("predictions.csv", "test")] + [
            (f, "valid") for f in comparison.validation_files(name)
        ]:
            predictions = comparison.read_predictions(output / filename, records, selected[split], labels)
            actual = comparison.metrics([records[i]["label"] for i in selected[split]], predictions, labels)
            expected = stored["test"] if split == "test" else stored["validation"][filename]
            comparison.close(actual, expected, directory + "." + filename)
            if split == "valid":
                scores.append(actual["macro_f1"])
        selection = (
            {"selected_epoch": 3, "history": [
                {"epoch": i + 1, "valid_macro_f1": score} for i, score in enumerate(scores)]}
            if name == "cnn" else
            {"C": comparison.GRID[int(np.argmax(scores))], "validation_grid": [
                {"C": c, "valid_macro_f1": score} for c, score in zip(comparison.GRID, scores)]}
        )
        comparison.close(config["selection"], selection, "comparison selection scores")
        results[directory] = stored["test"]["macro_f1"]
    return results


def verify_extraction_evidence(folder):
    config = load(folder / "config.json")
    expected_files = {f"{s}_{c}_{m}.json" for s in ("dev", "test") for c in CHANNELS for m in METHODS}
    require_equal(sorted(config["prediction_sha256"]), sorted(expected_files), "span prediction files")
    with (folder / "metrics.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    indexed = {(r["split"], r["channel"], r["method"]): r for r in rows}
    require_equal(len(indexed), 8, "eight span evaluations")
    require_equal(len(rows), 8, "unique span evaluations")
    audit = load(folder / "audit.json")
    for split in ("dev", "test"):
        for channel in CHANNELS:
            pairing = None
            for method in METHODS:
                filename = f"{split}_{channel}_{method}.json"
                require_equal(digest(folder / filename), config["prediction_sha256"][filename], filename)
                predictions = load(folder / filename)
                require_equal(len(predictions), audit["evaluation_sentences_after_training_overlap_removal"][split], "sentence count")
                ids = [r["sentence_id"] for r in predictions]
                require_equal(len(set(ids)), len(ids), "unique sentence IDs")
                metadata = [{k: r[k] for k in ("sentence_id", "source", "job_idx", "tokens_sha256", "gold")} for r in predictions]
                if pairing is not None:
                    require_equal(metadata, pairing, "paired gold sentences")
                pairing = metadata
                gold, predicted = set(), set()
                for row in predictions:
                    require_equal(row["channel"], channel, "channel")
                    require_equal(row["method"], method, "method")
                    gold.update((row["sentence_id"], *span) for span in validate_spans(row["gold"], row["token_count"]))
                    predicted.update((row["sentence_id"], *span) for span in validate_spans(row["prediction"], row["token_count"]))
                actual = scores(predicted, gold)
                require_equal(actual, {k: float(indexed[(split, channel, method)][k]) for k in actual}, filename)
    require_equal(calculate(folder), load(folder / "paired_intervals.json"), "extraction paired intervals")
    return {"evaluations": 8, "gold_basis": "saved paired gold, protected by artifact hashes"}


def verify_manifest():
    manifest = load(ROOT / "results/manifest.json")
    for name, value in manifest["sha256"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT.resolve()):
            raise ValueError("Manifest path leaves project")
        require_equal(digest(path), value, name)
    delivery = load(ROOT / "data/delivery_manifest.json")
    require_equal(digest(ROOT / "data/cohort.jsonl.gz"), delivery["cohort_sha256"], "cohort")
    for name, spec in delivery["sample"]["files"].items():
        require_equal(digest(ROOT / "data/sample" / name), spec["sha256"], "sample." + name)
    return len(manifest["sha256"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Also check source labels and full input byte hashes")
    args = parser.parse_args()
    count = verify_manifest()
    classification = verify_classification(metadata_only=not args.full)
    extraction = verify_extraction_evidence(ROOT / "results/extraction")
    model_scores = verify_comparison_evidence()
    if args.full:
        verify_extraction()
        require_equal(comparison.verify(ROOT / "data/full", ROOT / "results/comparison",
                                        list(comparison.MODEL_NAMES))["status"], "passed", "full comparison")
    summary = load(ROOT / "results/metrics.json")
    cls = load(ROOT / "results/classification/summary.json")
    require_equal(summary["classification"]["macro_f1"],
                  {name: value["macro_f1"] for name, value in cls["results"].items()}, "report classification")
    require_equal(summary["classification"]["hypothesis"], cls["hypothesis"], "report hypothesis")
    require_equal(summary["extraction"]["intervals"], load(ROOT / "results/extraction/paired_intervals.json"), "report intervals")
    require_equal(summary["model_comparison"]["rerun_macro_f1"], model_scores, "report comparison")
    with (ROOT / "results/extraction/metrics.csv").open(encoding="utf-8", newline="") as stream:
        extraction_rows = [{**r, **{k: float(r[k]) for k in ("precision", "recall", "f1")}}
                           for r in csv.DictReader(stream) if r["split"] == "test"]
    require_equal(summary["extraction"]["test"], extraction_rows, "report extraction scores")
    require_equal(summary["extraction"]["optimization"], load(ROOT / "results/extraction/optimization.json"),
                  "report optimization limits")
    print(json.dumps({"status": "passed", "artifacts": count,
                      "classification": classification, "extraction": extraction,
                      "comparison_macro_f1": model_scores,
                      "full_source_labels_checked": args.full}, indent=2))


if __name__ == "__main__":
    main()
