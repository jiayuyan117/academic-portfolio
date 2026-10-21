"""SkillSpan train-only lexicons and contextual BIO logistic regression.

Exact token spans are half-open [start, end); skill and knowledge are scored
separately. Only dev/test sentences whose exact tokens occur in train are removed.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import time
import warnings

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "data" / "full"
OUT = PROJECT / "results" / "extraction"
RUNTIME = PROJECT / ".runtime" / "extraction"
SPLIT_FILES = {s: f"skillspan_{s}.csv" for s in ("train", "dev", "test")}
CHANNELS = ("skill", "knowledge")
METHODS = ("train_lexicon", "context_BIO_LR")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=True, allow_nan=False) + "\n")


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        raise ValueError("Cannot export an empty metrics table")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def require_equal(actual, expected, location="result"):
    """Compare persisted evidence without changing it; tolerate CSV float rounding."""
    if isinstance(actual, dict):
        if not isinstance(expected, dict) or actual.keys() != expected.keys():
            raise ValueError(f"Verification mismatch: {location} keys")
        for key in actual:
            require_equal(actual[key], expected[key], f"{location}.{key}")
    elif isinstance(actual, (list, tuple)):
        if not isinstance(expected, (list, tuple)) or len(actual) != len(expected):
            raise ValueError(f"Verification mismatch: {location} length")
        for i, (a, b) in enumerate(zip(actual, expected)):
            require_equal(a, b, f"{location}[{i}]")
    elif isinstance(actual, (float, np.floating)):
        if (not isinstance(expected, (int, float)) or isinstance(expected, bool)
                or not math.isclose(float(actual), expected, rel_tol=0, abs_tol=1e-12)):
            raise ValueError(f"Verification mismatch: {location}")
    elif actual != expected:
        raise ValueError(f"Verification mismatch: {location}")


def positive_int(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("Must be a positive integer")
    return result


def read_split(name, data_dir=DATA):
    records, seen = [], set()
    with (Path(data_dir) / SPLIT_FILES[name]).open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            sid = row["sentence_id"]
            # Sampling preserves original IDs, not a newly numbered row sequence.
            if row["split"] != name or not re.fullmatch(rf"{name}:[1-9][0-9]*", sid) or sid in seen:
                raise ValueError(f"Invalid or duplicate sentence key: {sid}")
            seen.add(sid)
            record = {"sentence_id": sid, "idx": int(row["idx"]), "source": row["source"]}
            if not record["source"]:
                raise ValueError(f"Missing source: {sid}")
            for key in ("tokens", "tags_skill", "tags_knowledge"):
                record[key] = json.loads(row[key])
                if not isinstance(record[key], list) or not all(isinstance(v, str) for v in record[key]):
                    raise ValueError(f"Invalid sequence: {key}, {sid}")
            if not len(record["tokens"]) == len(record["tags_skill"]) == len(record["tags_knowledge"]):
                raise ValueError(f"Token/tag length mismatch: {sid}")
            for key in ("tags_skill", "tags_knowledge"):
                if not set(record[key]) <= {"B", "I", "O"}:
                    raise ValueError(f"Unexpected BIO tag: {sid}")
            records.append(record)
    if not records:
        raise ValueError(f"Empty SkillSpan split: {name}")
    return records


def filter_training_overlap(data):
    train = {tuple(r["tokens"]) for r in data["train"]}
    return {s: [r for r in data[s] if tuple(r["tokens"]) not in train] for s in ("dev", "test")}


def prepare(data_dir=DATA):
    data = {s: read_split(s, data_dir) for s in SPLIT_FILES}
    return data, filter_training_overlap(data)


def spans(tags):
    output, start = [], None
    for i, tag in enumerate(list(tags) + ["O"]):
        prefix = tag.split("-")[0]
        if prefix not in {"B", "I", "O"}:
            raise ValueError(f"Unexpected BIO tag: {tag}")
        if prefix != "I" and start is not None:
            output.append((start, i))
            start = None
        # Preserve the source rule: orphan I starts a span.
        if prefix == "B" or (prefix == "I" and start is None):
            start = i
    return output


def build_lexicon(records, channel):
    phrases = {tuple(w.lower() for w in r["tokens"][a:b])
               for r in records for a, b in spans(r["tags_" + channel])}
    lexicon = {}
    for phrase in sorted(phrases, key=lambda p: (-len(p), p)):
        if phrase:
            lexicon.setdefault(phrase[0], []).append(phrase)
    return phrases, lexicon


def lexical(tokens, lexicon):
    lowered = [w.lower() for w in tokens]
    result, i = [], 0
    while i < len(lowered):
        match = next((p for p in lexicon.get(lowered[i], [])
                      if tuple(lowered[i:i + len(p)]) == p), None)
        if match:
            result.append((i, i + len(match)))
            i += len(match)
        else:
            i += 1
    return result


def features(tokens, i):
    word = tokens[i]
    f = {"word": word.lower(), "capitalized": word[:1].isupper(),
         "all_caps": word.isupper(), "numeric": word.isdigit(),
         "has_digit": any(c.isdigit() for c in word), "length": min(30, len(word)),
         "suffix2": word[-2:].lower(), "suffix3": word[-3:].lower(),
         "prefix2": word[:2].lower()}
    for offset in (-2, -1, 1, 2):
        p = i + offset
        f[f"context{offset}"] = tokens[p].lower() if 0 <= p < len(tokens) else "<boundary>"
    f["prev_pair"] = f["context-1"] + "|" + word.lower()
    f["next_pair"] = word.lower() + "|" + f["context1"]
    return f


def scores(predicted, truth):
    hits = len(predicted & truth)
    return {"precision": hits / len(predicted) if predicted else 0.0,
            "recall": hits / len(truth) if truth else 0.0,
            "f1": 2 * hits / (len(predicted) + len(truth)) if predicted or truth else 0.0,
            "tp": hits, "predicted": len(predicted), "gold": len(truth)}


def token_digest(tokens):
    return hashlib.sha256(json.dumps(tokens, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def prediction_row(record, channel, method, found):
    return {"sentence_id": record["sentence_id"], "source": record["source"],
            "job_idx": record["idx"], "channel": channel, "method": method,
            "token_count": len(record["tokens"]), "tokens_sha256": token_digest(record["tokens"]),
            "gold": spans(record["tags_" + channel]), "prediction": found}


def validate_spans(value, token_count):
    if not isinstance(value, list):
        raise ValueError("Spans must be a list")
    previous_end = 0
    for item in value:
        if (not isinstance(item, (list, tuple)) or len(item) != 2
                or any(type(n) is not int for n in item)):
            raise ValueError("Span boundaries must be integer pairs")
        a, b = item
        if not 0 <= a < b <= token_count or a < previous_end:
            raise ValueError("Invalid, duplicate, unsorted, or overlapping span")
        previous_end = b
    return {tuple(s) for s in value}


def validate_predictions(rows, records, channel, method):
    if len(rows) != len(records):
        raise ValueError("Prediction sentence count mismatch")
    for row, record in zip(rows, records):
        expected = prediction_row(record, channel, method, [])
        for key in expected:
            if key != "prediction":
                require_equal(expected[key], row.get(key), f"prediction.{key}")
        validate_spans(row["prediction"], len(record["tokens"]))


def evaluate_rows(rows, records, phrases):
    gold = {(i, a, b) for i, r in enumerate(rows) for a, b in r["gold"]}
    predicted = {(i, a, b) for i, r in enumerate(rows) for a, b in r["prediction"]}
    unseen = {(i, a, b) for i, a, b in gold
              if tuple(w.lower() for w in records[i]["tokens"][a:b]) not in phrases}
    seen = gold - unseen
    return {**scores(predicted, gold), "unseen_gold_spans": len(unseen),
            "unseen_exact_recall": len(predicted & unseen) / max(1, len(unseen)),
            "seen_gold_spans": len(seen), "seen_exact_recall": len(predicted & seen) / max(1, len(seen))}


def audit_data(data, filtered, data_dir):
    signatures = {s: {tuple(r["tokens"]) for r in rows} for s, rows in data.items()}
    return {"sentences": {s: len(v) for s, v in data.items()},
            "tokens": {s: sum(len(r["tokens"]) for r in v) for s, v in data.items()},
            "train_test_identical_sentences": len(signatures["train"] & signatures["test"]),
            "train_dev_identical_sentences": len(signatures["train"] & signatures["dev"]),
            "dev_test_identical_sentences": len(signatures["dev"] & signatures["test"]),
            "files_sha256": {s: digest(Path(data_dir) / f) for s, f in SPLIT_FILES.items()},
            "evaluation_sentences_after_training_overlap_removal": {s: len(v) for s, v in filtered.items()},
            "note": "Exact token tuple overlap only; train duplicates retained; channels scored separately."}


def run(data_dir=DATA, output_dir=OUT, seed=42):
    data_dir, output_dir = Path(data_dir), Path(output_dir)
    data, filtered = prepare(data_dir)
    if any(not v for v in filtered.values()):
        raise ValueError("No evaluation sentences remain after training overlap removal")
    save(output_dir / "audit.json", audit_data(data, filtered, data_dir))
    start = time.perf_counter()
    vectorizer = DictVectorizer(sparse=True)
    train_x = vectorizer.fit_transform(features(r["tokens"], i)
                                      for r in data["train"] for i in range(len(r["tokens"])))
    feature_seconds = time.perf_counter() - start
    results, lexicons, hashes, optimization = [], {}, {}, {}
    import joblib
    RUNTIME.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, RUNTIME / "vectorizer.joblib")
    for channel in CHANNELS:
        phrases, lexicon = build_lexicon(data["train"], channel)
        lexicons[channel] = [list(p) for p in sorted(phrases)]
        labels = [tag for r in data["train"] for tag in r["tags_" + channel]]
        tick = time.perf_counter()
        classifier = LogisticRegression(C=1.0, max_iter=300, solver="lbfgs", random_state=seed)
        with warnings.catch_warnings(record=True) as caught, threadpool_limits(limits=2):
            warnings.simplefilter("always", ConvergenceWarning)
            classifier.fit(train_x, labels)
        optimization[channel] = {
            "iterations": classifier.n_iter_.tolist(),
            "iteration_limit": 300,
            "convergence_warning": any(issubclass(w.category, ConvergenceWarning) for w in caught),
        }
        if optimization[channel]["convergence_warning"]:
            print(f"{channel}: fixed 300-iteration budget reached; convergence not certified", flush=True)
        training_seconds = time.perf_counter() - tick
        joblib.dump(classifier, RUNTIME / f"{channel}_classifier.joblib")
        for split, records in filtered.items():
            for method in METHODS:
                tick, rows = time.perf_counter(), []
                for record in records:
                    tokens = record["tokens"]
                    if method == "train_lexicon":
                        found = lexical(tokens, lexicon)
                    elif tokens:
                        x = vectorizer.transform(features(tokens, i) for i in range(len(tokens)))
                        found = spans(classifier.predict(x).tolist())
                    else:
                        found = []
                    rows.append(prediction_row(record, channel, method, found))
                filename = f"{split}_{channel}_{method}.json"
                save(output_dir / filename, rows)
                hashes[filename] = digest(output_dir / filename)
                result = {"channel": channel, "split": split, "method": method,
                          **evaluate_rows(rows, records, phrases),
                          "predict_seconds": time.perf_counter() - tick,
                          "train_seconds": training_seconds if method == "context_BIO_LR" else 0.0}
                results.append(result)
                print(json.dumps(result), flush=True)
    write_csv(output_dir / "metrics.csv", results)
    save(output_dir / "train_lexicon.json", lexicons)
    save(output_dir / "optimization.json", optimization)
    save(output_dir / "config.json", {
        "method": "Train-only exact lexicon vs token context LR; separate BIO channels",
        "C": 1.0, "max_iter": 300, "seed": seed, "feature_count": len(vectorizer.feature_names_),
        "shared_feature_fit_seconds": feature_seconds, "prediction_sha256": hashes,
        "limits": ["No CRF transition decoding", "Case-insensitive lexicon",
                   "No test-driven threshold tuning", "English benchmark only",
                   "Intervals condition on fitted models, not training-seed uncertainty"]})
    return results


def verify_outputs(data_dir=DATA, output_dir=OUT):
    """Recompute all eight evaluations from delivered data and saved predictions."""
    output_dir = Path(output_dir)
    data, filtered = prepare(data_dir)
    require_equal(audit_data(data, filtered, data_dir), load(output_dir / "audit.json"), "audit")
    config = load(output_dir / "config.json")
    expected_files = {f"{s}_{c}_{m}.json" for s in ("dev", "test") for c in CHANNELS for m in METHODS}
    require_equal(sorted(expected_files), sorted(config["prediction_sha256"]), "prediction files")
    with (output_dir / "metrics.csv").open(encoding="utf-8", newline="") as stream:
        metrics = list(csv.DictReader(stream))
    indexed = {(r["split"], r["channel"], r["method"]): r for r in metrics}
    if len(metrics) != 8 or len(indexed) != 8:
        raise ValueError("Expected eight distinct extraction evaluations")
    expected_lexicons, recomputed = {}, []
    for channel in CHANNELS:
        phrases, _ = build_lexicon(data["train"], channel)
        expected_lexicons[channel] = [list(p) for p in sorted(phrases)]
        for split, records in filtered.items():
            for method in METHODS:
                filename = f"{split}_{channel}_{method}.json"
                rows = load(output_dir / filename)  # Missing predictions must fail.
                validate_predictions(rows, records, channel, method)
                require_equal(digest(output_dir / filename), config["prediction_sha256"][filename], filename)
                actual = evaluate_rows(rows, records, phrases)
                saved = indexed[(split, channel, method)]
                require_equal(actual, {k: float(saved[k]) for k in actual}, filename + ".metrics")
                recomputed.append({"split": split, "channel": channel, "method": method, **actual})
    require_equal(expected_lexicons, load(output_dir / "train_lexicon.json"), "train lexicons")
    return recomputed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--output-dir", type=Path, default=OUT)
    parser.add_argument("--stage", choices=("train", "verify", "prepare"), default="train")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    if args.stage == "prepare":
        data, filtered = prepare(args.data_dir)
        print(json.dumps(audit_data(data, filtered, args.data_dir), indent=2))
    elif args.stage == "verify":
        results = verify_outputs(args.data_dir, args.output_dir)
        print(json.dumps({"verified": True, "evaluations": len(results)}))
    else:
        run(args.data_dir, args.output_dir, args.seed)


if __name__ == "__main__":
    main()
