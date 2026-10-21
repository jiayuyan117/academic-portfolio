"""Import the supplied research delivery without publishing the full text corpus.

This authoring utility preserves its fixed cohort as a compact selection ledger,
creates a real-data smoke sample and records the delivered file hashes. Public
reproduction uses data/download_data.py instead of requiring the private archive.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
JOB_NAME = "01_岗位分类数据.csv"
SKILL_FILES = {"train": "训练集.csv", "dev": "验证集.csv", "test": "测试集.csv"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sample_jobs(rows: list[dict]) -> list[dict]:
    rng = random.Random(20261021)
    selected = []
    for split in ("train", "valid", "test"):
        pool = [row for row in rows if row["split"] == split]
        chosen = []
        for label in sorted({row["label"] for row in pool}):
            subset = [row for row in pool if row["label"] == label]
            chosen.extend(rng.sample(subset, min(20, len(subset))))
        ids = {row["id"] for row in chosen}
        chosen.extend(rng.sample([row for row in pool if row["id"] not in ids], 400 - len(chosen)))
        selected.extend(chosen)
    ids = {row["id"] for row in selected}
    return [row for row in rows if row["id"] in ids]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Extracted delivery root")
    args = parser.parse_args()
    source = args.source / "02_真实数据"
    jobs_path = source / JOB_NAME
    jobs = read_csv(jobs_path)
    if len(jobs) != 21663 or len({row["id"] for row in jobs}) != 21663:
        raise ValueError("Unexpected supplied cohort size or duplicate IDs")
    if any(hashlib.sha256(row["text"].lower().encode("utf-8")).hexdigest() != row["id"] for row in jobs):
        raise ValueError("A delivered normalized content fingerprint does not match")
    groups = {split: {row["group"] for row in jobs if row["split"] == split}
              for split in ("train", "valid", "test")}
    if any(groups[a] & groups[b] for a, b in (("train", "valid"), ("train", "test"), ("valid", "test"))):
        raise ValueError("Employer groups cross splits")

    data = ROOT / "data"
    data.mkdir(parents=True, exist_ok=True)
    ledger = "".join(json.dumps({k: v for k, v in row.items() if k != "text"},
                               ensure_ascii=False, separators=(",", ":")) + "\n" for row in jobs)
    with (data / "cohort.jsonl.gz").open("wb") as stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as compressed:
            compressed.write(ledger.encode("utf-8"))
    write_csv(data / "full/jobs.csv", jobs)
    write_csv(data / "sample/jobs.csv", sample_jobs(jobs))

    delivered = {"jobs": {"file": JOB_NAME, "sha256": sha256(jobs_path)}}
    skills = {}
    for split, name in SKILL_FILES.items():
        path = source / "02_技能抽取数据" / name
        skills[split] = read_csv(path)
        delivered[f"skillspan_{split}"] = {"file": f"02_技能抽取数据/{name}", "sha256": sha256(path)}
        write_csv(data / f"full/skillspan_{split}.csv", skills[split])
    train_tokens = {tuple(json.loads(row["tokens"])) for row in skills["train"]}
    rng = random.Random(20261022)
    for split, rows in skills.items():
        eligible = rows if split == "train" else [
            row for row in rows if tuple(json.loads(row["tokens"])) not in train_tokens
        ]
        selected = set(rng.sample(range(len(eligible)), 200 if split == "train" else 100))
        write_csv(data / f"sample/skillspan_{split}.csv",
                  [row for i, row in enumerate(eligible) if i in selected])

    manifest = {
        "schema_version": 1,
        "delivered_files": delivered,
        "cohort_sha256": sha256(data / "cohort.jsonl.gz"),
        "content_id_algorithm": "SHA-256 of UTF-8 text.lower(); not the unmodified text hash",
        "jobs": {
            "rows": len(jobs),
            "classes": len({row["label"] for row in jobs}),
            "splits": dict(Counter(row["split"] for row in jobs)),
            "employer_groups": {split: len(value) for split, value in groups.items()},
            "source_references": sum(len(json.loads(row["provenance_json"])) for row in jobs),
        },
        "sample": {
            "purpose": "Small real-data pipeline smoke test; not the reported research evaluation",
            "jobs_per_split": 400,
            "skill_sentences": {"train": 200, "dev": 100, "test": 100},
            "selection_seeds": [20261021, 20261022],
            "files": {
                path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
                for path in sorted((data / "sample").glob("*.csv"))
            },
        },
    }
    (data / "delivery_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
