"""Download fixed source snapshots and reconstruct the archived study cohort.

The selection ledger preserves the delivered row selection and employer splits.
It does not claim to recover an unavailable historical split-generation script.
No new website scraping or synthetic observations are used.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import html
import json
from pathlib import Path
import re
import tempfile
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile

DATA = Path(__file__).resolve().parent
ROOT = DATA.parent
MAX_DOWNLOAD = 200 * 1024 * 1024
JOB_COLUMNS = [
    "id", "text", "label", "company", "group", "split", "source", "source_line",
    "original_id", "date", "source_url", "raw_file_sha256", "provenance_json",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(value: str) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1\s*>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def content_id(text: str) -> str:
    return hashlib.sha256(text.lower().encode("utf-8")).hexdigest()


def check_digest(path: Path, expected: str) -> None:
    require(path.is_file(), f"Missing source file: {path.name}")
    require(sha256(path) == expected, f"SHA-256 mismatch: {path.name}")


def download(url: str, destination: Path) -> None:
    require(url.startswith("https://"), "Source downloads must use HTTPS")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = Request(url, headers={"User-Agent": "academic-portfolio-reproducer/1.0"})
    try:
        with urlopen(request, timeout=45) as response, temporary.open("wb") as stream:
            require(response.geturl().startswith("https://"), "Insecure download redirect")
            received = 0
            for block in iter(lambda: response.read(1024 * 1024), b""):
                received += len(block)
                require(received <= MAX_DOWNLOAD, "Source exceeds download size limit")
                stream.write(block)
        require(received > 0, "Source returned an empty response")
        temporary.replace(destination)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"Could not download {url}. Check network/access requirements; "
            "an HTML login page is not accepted as data."
        ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def ensure_source(spec: dict, cache: Path, offline: bool, archives: Path | None = None) -> Path:
    destination = cache / spec["cache_name"]
    if destination.exists():
        check_digest(destination, spec["sha256"])
        return destination
    cache.mkdir(parents=True, exist_ok=True)
    if "archive_member" in spec:
        with tempfile.TemporaryDirectory(prefix="seek-download-", dir=cache) as folder:
            supplied = archives / (destination.stem + ".zip") if archives else None
            archive_path = supplied if supplied and supplied.is_file() else Path(folder) / "source.zip"
            if not archive_path.is_file():
                require(not offline, f"Offline source missing: {destination.name}")
                download(spec["url"], archive_path)
            require(zipfile.is_zipfile(archive_path), "Expected a Kaggle ZIP, not HTML or an error page")
            with zipfile.ZipFile(archive_path) as archive:
                member = archive.getinfo(spec["archive_member"])
                require(member.file_size == spec["bytes"], "Unexpected source member size")
                raw = archive.read(member)
            require(hashlib.sha256(raw).hexdigest() == spec["sha256"],
                    f"Source member SHA-256 mismatch: {spec['cache_name']}")
            destination.write_bytes(raw)
    else:
        supplied = archives / destination.name if archives else None
        if supplied and supplied.is_file():
            check_digest(supplied, spec["sha256"])
            destination.write_bytes(supplied.read_bytes())
        else:
            require(not offline, f"Offline source missing: {destination.name}")
            download(spec["url"], destination)
    check_digest(destination, spec["sha256"])
    return destination


def read_cohort() -> list[dict]:
    manifest = json.loads((DATA / "delivery_manifest.json").read_text(encoding="utf-8"))
    check_digest(DATA / "cohort.jsonl.gz", manifest["cohort_sha256"])
    with gzip.open(DATA / "cohort.jsonl.gz", "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def reconstruct_jobs(cohort: list[dict], raw_tables: dict[str, list[dict]]) -> tuple[list[dict], int]:
    output = []
    references = 0
    for row in cohort:
        primary_text = None
        evidence = json.loads(row["provenance_json"])
        require(bool(evidence), f"No provenance references for {row['id']}")
        for ref in evidence:
            require(ref["source"] in raw_tables, "Unknown source in selection ledger")
            records = raw_tables[ref["source"]]
            line = int(ref["line"])
            require(1 <= line <= len(records), "Source row is outside the fixed snapshot")
            original = records[line - 1]
            text = normalize_text(original.get("job_description", ""))
            require(content_id(text) == row["id"], f"Source text fingerprint mismatch at {ref['source']}:{line}")
            require(normalize_text(original.get("category", "")) == row["label"], "Source label mismatch")
            require(str(original.get("uniq_id", "")) == ref["original_id"], "Source identifier mismatch")
            require(str(original.get("post_date", "")) == ref["date"], "Source date mismatch")
            require(normalize_text(original.get("company_name", "")).lower()
                    == normalize_text(ref["company"]).lower(), "Source employer mismatch")
            if ref["source"] == row["source"] and line == int(row["source_line"]):
                require(ref["original_id"] == row["original_id"] and ref["date"] == row["date"],
                        "Primary metadata disagrees with provenance")
                require(normalize_text(ref["company"]).lower()
                        == normalize_text(row["company"]).lower(), "Primary employer mismatch")
                require(ref["group"] == row["group"], "Primary employer-group mismatch")
                primary_text = text
            references += 1
        require(primary_text is not None, "Primary source reference is absent")
        output.append({**row, "text": primary_text})
    return output, references


def convert_skillspan(split: str, records: list[dict]) -> list[dict]:
    rows = []
    for i, record in enumerate(records, 1):
        tokens = record["tokens"]
        require(bool(tokens) and all(isinstance(token, str) for token in tokens), "Invalid source tokens")
        for channel in ("tags_skill", "tags_knowledge"):
            require(len(tokens) == len(record[channel]), "Token/BIO alignment mismatch")
            require(set(record[channel]) <= {"B", "I", "O"}, "Unknown BIO tag")
        rows.append({
            "sentence_id": f"{split}:{i}", "split": split,
            "source": record["source"], "idx": record["idx"],
            **{key: json.dumps(record[key], ensure_ascii=False)
               for key in ("tokens", "tags_skill", "tags_knowledge")},
        })
    return rows


def write_csv(path: Path, rows: list[dict], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".csv.part")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns or list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def run(cache: Path, output: Path, offline: bool = False, archives: Path | None = None) -> dict:
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    manifest = json.loads((DATA / "delivery_manifest.json").read_text(encoding="utf-8"))
    raw_tables = {}
    observed_hashes = {}
    for source in sources["seek"]:
        path = ensure_source(source, cache, offline, archives)
        with path.open(encoding="utf-8-sig") as stream:
            raw_tables[source["id"]] = [json.loads(line) for line in stream if line.strip()]
        require(len(raw_tables[source["id"]]) == source["rows"], "Raw SEEK row count changed")
        observed_hashes[path.name] = sha256(path)
    jobs, references = reconstruct_jobs(read_cohort(), raw_tables)
    require(len(jobs) == manifest["jobs"]["rows"], "Cohort size changed")
    require(len({row["id"] for row in jobs}) == len(jobs), "Duplicate cohort IDs")
    require(dict(Counter(row["split"] for row in jobs)) == manifest["jobs"]["splits"], "Split size changed")
    require(len({row["label"] for row in jobs}) == manifest["jobs"]["classes"], "Category count changed")
    groups = {split: {row["group"] for row in jobs if row["split"] == split}
              for split in ("train", "valid", "test")}
    overlaps = {a + "/" + b: len(groups[a] & groups[b])
                for a, b in (("train", "valid"), ("train", "test"), ("valid", "test"))}
    require(not any(overlaps.values()), "Employer groups cross evaluation splits")
    require(references == manifest["jobs"]["source_references"], "Provenance reference count changed")
    write_csv(output / "jobs.csv", jobs, JOB_COLUMNS)
    skill_counts = {}
    for spec in sources["skillspan"]["files"]:
        spec = dict(spec)
        spec["url"] = (
            "https://raw.githubusercontent.com/kris927b/SkillSpan/"
            f"{sources['skillspan']['revision']}/data/json/{spec['split']}.json"
        )
        path = ensure_source(spec, cache, offline, archives)
        with path.open(encoding="utf-8") as stream:
            records = [json.loads(line) for line in stream if line.strip()]
        require(len(records) == spec["rows"], "SkillSpan sentence count changed")
        rows = convert_skillspan(spec["split"], records)
        write_csv(output / f"skillspan_{spec['split']}.csv", rows)
        skill_counts[spec["split"]] = len(rows)
        observed_hashes[path.name] = sha256(path)
    audit = {
        "status": "passed",
        "source_files_sha256": observed_hashes,
        "raw_seek_rows": sum(map(len, raw_tables.values())),
        "jobs": len(jobs),
        "classes": manifest["jobs"]["classes"],
        "splits": manifest["jobs"]["splits"],
        "unique_normalized_content_ids": len({row["id"] for row in jobs}),
        "verified_source_references": references,
        "employer_overlap": overlaps,
        "skillspan_sentences": skill_counts,
        "split_basis": "Archived cohort ledger, independently matched to fixed public source rows",
        "limits": "Hashes and row matching establish integrity/traceability, not truth of every advertisement.",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "source_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=DATA / "raw")
    parser.add_argument("--output", type=Path, default=DATA / "full")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--archives", type=Path, help="Previously downloaded seek_a.zip, seek_b.zip and SkillSpan JSON")
    args = parser.parse_args()
    print(json.dumps(run(args.cache.resolve(), args.output.resolve(), args.offline, args.archives), indent=2))


if __name__ == "__main__":
    main()
