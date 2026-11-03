"""Optional JobStreet evaluation; requires the original external exclusion index.

No external score is certified by this release. The missing index is mandatory:
replacing it with hashes of only the training cohort would change the study.
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from threadpoolctl import threadpool_limits

from classification import PROJECT, prepare, lexicon, lexical_matrix, metrics, bootstrap
from skill_extraction import digest, load, save, write_jsonl, read_jsonl, require_equal

sys.path.insert(0, str(PROJECT / "data"))
from download_data import normalize_text

INDEX_HASH = "33c4deee352890e3b14a87cb4ad9c2bff29e1b3867c19e0d3e07432f2d643444"


def company(value):
    text = normalize_text(value).casefold().replace("&", " and ")
    text = re.sub(r"\b(pty|ltd|limited|inc|incorporated|proprietary)\b", " ", text)
    return " ".join(re.findall(r"[a-z0-9]+", text))


def body_hash(value):
    return hashlib.sha256(normalize_text(value).casefold().encode()).hexdigest()


def run(args):
    if not args.jobstreet or not args.seek_hash_index:
        raise ValueError("External inputs were not supplied. Provide --jobstreet and --seek-hash-index after resolving data rights.")
    for path in (args.jobstreet, args.seek_hash_index):
        if not path.is_file():
            raise ValueError("External input does not exist: " + path.name)
    if digest(args.seek_hash_index) != INDEX_HASH:
        raise ValueError("Archived 115,812-record SEEK exclusion index hash mismatch")
    records, labels = prepare(args.data_dir)
    excluded = set(load(args.seek_hash_index)["hashes"])
    if not {body_hash(row["text"]) for row in records} <= excluded:
        raise ValueError("Exclusion index does not cover the delivered cohort")
    canonical = {" ".join(label.split()).casefold(): label for label in labels}
    source = pd.read_csv(args.jobstreet, keep_default_na=False)
    if not {"descriptions", "category", "company", "job_id"} <= set(source):
        raise ValueError("JobStreet source schema mismatch")
    source["text"] = source["descriptions"].map(normalize_text)
    source["body_hash"] = source["text"].map(body_hash)
    source["group"] = source["company"].map(company)
    source["label_normalized"] = source["category"].map(lambda value: " ".join(str(value).split()).casefold())
    source["label"] = source["label_normalized"].map(canonical)
    conflicting = source[source["text"].ne("")].groupby("body_hash")["label_normalized"].nunique()
    multi_company = source.groupby("body_hash")["group"].nunique()
    seen_groups = {r["group"] for r in records if r["split"] in {"train", "valid"}}
    keep = (source["text"].ne("") & source["label"].notna()
            & ~source["group"].isin({"", "private advertiser", "confidential", "not disclosed", "unknown", "na", "n a"})
            & ~source["body_hash"].isin(set(conflicting[conflicting > 1].index) | excluded)
            & ~source["body_hash"].isin(set(multi_company[multi_company > 1].index))
            & ~source["group"].isin(seen_groups))
    external = source.loc[keep].drop_duplicates("body_hash", keep="first")
    if external.empty:
        raise ValueError("No eligible external rows remain")
    train = [r for r in records if r["split"] == "train"]
    texts = [r["text"] for r in train] + external["text"].tolist()
    target = np.array([r["label"] for r in train])
    split = len(train)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_df=.98,
                                max_features=100000, sublinear_tf=True, dtype=np.float64)
    vectorizer.fit(texts[:split])
    text = vectorizer.transform(texts)
    terms, pattern = lexicon(args.data_dir)
    lexical = lexical_matrix(texts, terms, pattern)
    summary = load(args.classification / "summary.json")
    for name, expected in summary["input_sha256"].items():
        require_equal(digest(args.data_dir / name), expected, "training input " + name)
    outputs = {}
    for name, matrix in (("text", text), ("fusion", sparse.hstack([text, lexical], format="csr"))):
        value = summary["results"][name]["parameters"]["C"]
        model = LinearSVC(C=value, dual="auto", random_state=42, max_iter=5000)
        with threadpool_limits(limits=2):
            model.fit(matrix[:split], target)
            predicted = model.predict(matrix[split:])
        rows = [{"id": row.body_hash, "group": row.group, "true": row.label, "predicted": str(pred)}
                for row, pred in zip(external.itertuples(), predicted)]
        write_jsonl(args.output_dir / f"{name}_predictions.jsonl", rows)
        outputs[name] = {"metrics": metrics(external["label"].tolist(), predicted, labels), "C": value}
    first = [r["predicted"] for r in read_jsonl(args.output_dir / "text_predictions.jsonl")]
    second = [r["predicted"] for r in read_jsonl(args.output_dir / "fusion_predictions.jsonl")]
    with threadpool_limits(limits=2):
        interval = bootstrap(external["label"].tolist(), first, second,
                             external["group"].to_numpy(), labels, 1000, 42)
    save(args.output_dir / "summary.json", {
        "status": "completed", "raw_rows": len(source), "evaluation_rows": len(external),
        "groups": int(external["group"].nunique()), "results": outputs, "hypothesis": interval,
        "input_sha256": {"jobstreet": digest(args.jobstreet), "exclusion_index": INDEX_HASH},
        "scope": "Exploratory external evaluation; no external label used for parameter selection",
        "interval_note": "Same paired cluster estimand; multinomial draw sequence differs from historical external script",
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=PROJECT / "data/full")
    parser.add_argument("--jobstreet", type=Path, default=os.environ.get("JOBSTREET_CSV"))
    parser.add_argument("--seek-hash-index", type=Path, default=os.environ.get("SEEK_HASH_INDEX"))
    parser.add_argument("--classification", type=Path, default=PROJECT / "results/classification")
    parser.add_argument("--output-dir", type=Path, default=PROJECT / ".runtime/external")
    arguments = parser.parse_args()
    try:
        run(arguments)
    except (ValueError, FileNotFoundError) as error:
        parser.exit(1, str(error) + "\n")
