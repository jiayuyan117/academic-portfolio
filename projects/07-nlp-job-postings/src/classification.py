"""Employer-isolated SEEK ablation with independently verifiable predictions.

Lexicon features combine SkillSpan TRAIN Skill and Knowledge phrases. The
0.02 effect threshold is recorded in the supplied code; no timestamped public
preregistration was supplied. Training never uses test labels for selection.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import html
import importlib.metadata
import json
from pathlib import Path
import re
import time
import unicodedata

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import normalize
from sklearn.svm import LinearSVC
from threadpoolctl import threadpool_limits

from skill_extraction import digest, load, read_jsonl, read_split, require_equal, save, write_jsonl

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "data/full"
OUT = PROJECT / "results/classification"
NAMES = ("text", "lexicon", "fusion")


def prepare(data_dir):
    with (Path(data_dir) / "jobs.csv").open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream))
    if not records or len({r["id"] for r in records}) != len(records):
        raise ValueError("Missing data or duplicate content identifiers")
    for row in records:
        if not all(row[k] for k in ("id", "text", "label", "group", "split")):
            raise ValueError("Missing classification field")
        if row["split"] not in {"train", "valid", "test"}:
            raise ValueError("Unknown split")
        if hashlib.sha256(row["text"].lower().encode()).hexdigest() != row["id"]:
            raise ValueError("Normalized text/content ID mismatch")
    groups = {s: {r["group"] for r in records if r["split"] == s} for s in ("train", "valid", "test")}
    if any(not g for g in groups.values()) or any(
        groups[a] & groups[b] for a, b in (("train", "valid"), ("train", "test"), ("valid", "test"))
    ):
        raise ValueError("Missing split or employer overlap")
    labels = sorted({r["label"] for r in records})
    if any({r["label"] for r in records if r["split"] == s} != set(labels) for s in groups):
        raise ValueError("Each evaluation split must represent the fixed category set")
    return records, labels


def trie_pattern(terms):
    trie = {}
    for term in terms:
        node = trie
        for char in term:
            node = node.setdefault(char, {})
        node[""] = None
    def emit(node):
        branches = [re.escape(char) + emit(child) for char, child in sorted(node.items()) if char]
        if "" in node:
            branches.append("")
        return branches[0] if len(branches) == 1 else "(?:" + "|".join(branches) + ")"
    if not trie:
        raise ValueError("No training phrases available")
    return re.compile(r"(?<!\w)" + emit(trie) + r"(?!\w)", re.I)


def lexicon(data_dir):
    terms = Counter()
    for row in read_split("train", data_dir):
        for channel in ("tags_skill", "tags_knowledge"):
            current = []
            for token, tag in list(zip(row["tokens"], row[channel])) + [("", "O")]:
                if tag.startswith("B") or tag == "O":
                    if current:
                        phrase = html.unescape(" ".join(current))
                        phrase = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", phrase, flags=re.S | re.I)
                        phrase = " ".join(unicodedata.normalize("NFKC", re.sub(r"<[^>]+>", " ", phrase)).split()).casefold()
                        phrase = re.sub(r"\s+([.,;:!?)])", r"\1", phrase)
                        phrase = re.sub(r"([(])\s+", r"\1", phrase)
                        if re.search("[a-z]", phrase):
                            terms[phrase] += 1
                    current = []
                if tag != "O":
                    current.append(token)
    return sorted(terms), trie_pattern(sorted(terms))


def lexical_matrix(texts, terms, pattern):
    term_index = {term: i for i, term in enumerate(terms)}
    rows, columns, values = [], [], []
    for i, text in enumerate(texts):
        hits = Counter(match.group().casefold() for match in pattern.finditer(text.casefold()))
        for term, count in hits.items():
            rows.append(i)
            columns.append(term_index[term])
            values.append(count)
    matrix = sparse.csr_matrix((values, (rows, columns)), shape=(len(texts), len(terms)), dtype=float)
    matrix.data = np.log1p(matrix.data)
    return normalize(matrix)


def metrics(truth, predicted, labels):
    return {
        "macro_f1": float(f1_score(truth, predicted, labels=labels, average="macro", zero_division=0)),
        "accuracy": float(accuracy_score(truth, predicted)),
        "per_class": classification_report(truth, predicted, labels=labels, output_dict=True, zero_division=0),
        "confusion": confusion_matrix(truth, predicted, labels=labels).tolist(),
    }


def fit_select(matrix, labels, train, valid, test, seed=42):
    grid, best, best_score = [], None, -1.0
    for value in (0.1, 1.0, 10.0):
        classifier = LinearSVC(C=value, dual="auto", random_state=seed, max_iter=5000)
        classifier.fit(matrix[train], labels[train])
        score = float(f1_score(labels[valid], classifier.predict(matrix[valid]), average="macro", zero_division=0))
        grid.append({"C": value, "valid_macro_f1": score})
        if score > best_score:
            best, best_score = classifier, score
    return best.predict(matrix[test]), {"C": best.C, "validation_grid": grid, "seed": seed}


def bootstrap(truth, first, second, groups, labels, replicates=1000, seed=42):
    if not (len(truth) == len(first) == len(second) == len(groups)) or not len(truth):
        raise ValueError("Paired bootstrap inputs must have equal nonzero lengths")
    if replicates < 1:
        raise ValueError("Bootstrap replicates must be positive")
    unique_groups, inverse = np.unique(groups, return_inverse=True)
    index = {label: i for i, label in enumerate(labels)}
    k = len(labels)
    y = np.array([index[v] for v in truth])
    matrices = []
    for predictions in (first, second):
        counts = np.zeros((len(unique_groups), k, k), dtype=np.int64)
        np.add.at(counts, (inverse, y, [index[v] for v in predictions]), 1)
        # Counts are exact small integers; float64 enables fast BLAS multiplication.
        matrices.append(counts.reshape(len(unique_groups), -1).astype(np.float64))
    def macro(matrix):
        matrix = matrix.reshape(-1, k, k)
        denominator = matrix.sum(1) + matrix.sum(2)
        return np.divide(2 * np.diagonal(matrix, axis1=1, axis2=2), denominator,
                         out=np.zeros_like(denominator, dtype=float), where=denominator != 0).mean(1)
    rng = np.random.default_rng(seed)
    deltas = []
    for start in range(0, replicates, 50):
        weights = rng.multinomial(len(unique_groups), np.full(len(unique_groups), 1 / len(unique_groups)),
                                  size=min(50, replicates - start))
        deltas.extend((macro(weights @ matrices[1]) - macro(weights @ matrices[0])).tolist())
    observed = float(macro(matrices[1].sum(0))[0] - macro(matrices[0].sum(0))[0])
    interval = np.quantile(deltas, [0.025, 0.975]).tolist()
    return {
        "delta_macro_f1": observed, "ci95": interval, "replicates": replicates,
        "clusters": len(unique_groups), "seed": seed, "decision_threshold": 0.02,
        "threshold_and_interval_pass": bool(observed >= 0.02 and interval[0] > 0),
        "method": "Paired employer-cluster percentile bootstrap; fixed category set",
    }


def run(data_dir=DATA, output_dir=OUT, replicates=1000, seed=42, reuse_text=False):
    records, labels = prepare(data_dir)
    output_dir = Path(output_dir)
    texts = [r["text"] for r in records]
    y = np.array([r["label"] for r in records])
    train, valid, test = [np.array([i for i, r in enumerate(records) if r["split"] == s])
                          for s in ("train", "valid", "test")]
    terms, pattern = lexicon(data_dir)
    lex = lexical_matrix(texts, terms, pattern)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_df=0.98,
                               max_features=100000, sublinear_tf=True, dtype=np.float64)
    vectorizer.fit([texts[i] for i in train])
    text = vectorizer.transform(texts)
    summary = {
        "status": "running", "n": len(records), "labels": labels,
        "split_counts": dict(Counter(r["split"] for r in records)),
        "input_sha256": {name: digest(Path(data_dir) / name) for name in ("jobs.csv", "skillspan_train.csv")},
        "versions": {p: importlib.metadata.version(p) for p in ("numpy", "pandas", "scipy", "scikit-learn")},
        "lexicon": {"channels": ["Skill", "Knowledge"], "phrases": len(terms),
                    "source": "SkillSpan training labels only", "transform": "log1p count, row L2"},
        "seed": seed, "results": {}, "prediction_sha256": {},
    }
    predictions = {}
    previous = load(output_dir / "summary.json") if reuse_text else None
    for name, matrix in (("text", text), ("lexicon", lex), ("fusion", sparse.hstack([text, lex], format="csr"))):
        filename = name + "_predictions.jsonl"
        if name == "text" and previous is not None:
            require_equal(previous["input_sha256"], summary["input_sha256"], "reused inputs")
            require_equal(previous["seed"], seed, "reused seed")
            rows = read_jsonl(output_dir / filename)
            require_equal([r["id"] for r in rows], [records[i]["id"] for i in test], "reused test IDs")
            require_equal(digest(output_dir / filename), previous["prediction_sha256"][filename], "reused predictions")
            predictions[name] = np.array([r["predicted"] for r in rows])
            actual = metrics(y[test], predictions[name], labels)
            require_equal(actual, {k: previous["results"][name][k] for k in actual}, "reused metrics")
            summary["results"][name] = previous["results"][name]
            summary["prediction_sha256"][filename] = digest(output_dir / filename)
            continue
        start = time.perf_counter()
        with threadpool_limits(limits=2):
            predicted, parameters = fit_select(matrix, y, train, valid, test, seed)
        predictions[name] = predicted
        summary["results"][name] = {**metrics(y[test], predicted, labels),
                                    "parameters": parameters, "fit_select_predict_seconds": time.perf_counter() - start}
        write_jsonl(output_dir / filename, [
            {"id": records[i]["id"], "group": records[i]["group"], "true": str(y[i]), "predicted": str(p)}
            for i, p in zip(test, predicted)
        ])
        summary["prediction_sha256"][filename] = digest(output_dir / filename)
        print(name, summary["results"][name]["macro_f1"], flush=True)
    with threadpool_limits(limits=2):
        summary["hypothesis"] = bootstrap(y[test], predictions["text"], predictions["fusion"],
                                          np.array([records[i]["group"] for i in test]), labels, replicates, seed)
    summary["status"] = "passed"
    save(output_dir / "summary.json", summary)
    save(output_dir / "lexicon.json", {"terms": terms, **summary["lexicon"]})
    return summary


def verify_outputs(data_dir=DATA, output_dir=OUT, metadata_only=False):
    output_dir = Path(output_dir)
    summary = load(output_dir / "summary.json")
    if metadata_only:
        with gzip.open(PROJECT / "data/cohort.jsonl.gz", "rt", encoding="utf-8") as stream:
            records = [json.loads(line) for line in stream]
    else:
        records, _ = prepare(data_dir)
        for name, expected in summary["input_sha256"].items():
            require_equal(digest(Path(data_dir) / name), expected, name)
    labels = sorted({r["label"] for r in records})
    require_equal(labels, summary["labels"], "category set")
    require_equal(len(records), summary["n"], "row count")
    require_equal(dict(Counter(r["split"] for r in records)), summary["split_counts"], "splits")
    require_equal(sorted(summary["results"]), sorted(NAMES), "model set")
    require_equal(sorted(summary["prediction_sha256"]), sorted(n + "_predictions.jsonl" for n in NAMES), "predictions")
    test = [r for r in records if r["split"] == "test"]
    predictions = {}
    for name in NAMES:
        filename = name + "_predictions.jsonl"
        require_equal(digest(output_dir / filename), summary["prediction_sha256"][filename], filename)
        rows = read_jsonl(output_dir / filename)
        require_equal(len(rows), len(test), name + ".test count")
        for row, expected in zip(rows, test):
            for key, field in (("id", "id"), ("group", "group"), ("true", "label")):
                require_equal(row[key], expected[field], name + "." + key)
            if row["predicted"] not in labels:
                raise ValueError("Unknown predicted category")
        predictions[name] = [r["predicted"] for r in rows]
        actual = metrics([r["label"] for r in test], predictions[name], labels)
        require_equal(actual, {key: summary["results"][name][key] for key in actual}, name)
    hypothesis = summary["hypothesis"]
    with threadpool_limits(limits=2):
        actual = bootstrap([r["label"] for r in test], predictions["text"], predictions["fusion"],
                            np.array([r["group"] for r in test]), labels, hypothesis["replicates"], hypothesis["seed"])
    require_equal(actual, hypothesis, "paired bootstrap")
    require_equal(summary["status"], "passed", "status")
    return {"status": "passed", "models": 3, "predictions": len(test) * 3,
            "bootstrap_replicates": hypothesis["replicates"],
            "data_check": "cohort metadata only" if metadata_only else "full input hashes and content IDs"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--output-dir", type=Path, default=OUT)
    parser.add_argument("--stage", choices=("train", "verify"), default="train")
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--reuse-text", action="store_true", help="Reuse hash-verified text predictions while rebuilding lexicon models")
    args = parser.parse_args()
    if args.stage == "verify":
        print(json.dumps(verify_outputs(args.data_dir, args.output_dir, args.metadata_only), indent=2))
    else:
        run(args.data_dir, args.output_dir, args.bootstrap, args.seed, args.reuse_text)


if __name__ == "__main__":
    main()
