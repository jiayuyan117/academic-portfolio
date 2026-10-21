"""Check committed delivery artifacts, homepage links and offline chart resources."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
import hashlib
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from rebuild import PROJECTS, ROOT


class Page(HTMLParser):
    """Collect page IDs, links and resources, rejecting duplicate IDs."""
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.resources: list[str] = []
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        """Record identifiers and resource URLs from an HTML opening tag."""
        attr = dict(attrs)
        if attr.get("id"):
            if attr["id"] in self.ids:
                raise AssertionError(f"{self.path}: duplicate id {attr['id']}")
            self.ids.add(attr["id"])
        if tag == "a" and attr.get("href"):
            self.links.append(attr["href"])
        if tag in {"script", "img", "iframe", "source"} and attr.get("src"):
            self.resources.append(attr["src"])
        if tag == "link" and attr.get("href"):
            self.resources.append(attr["href"])


def check_local_link(page: Page, value: str) -> None:
    """Raise AssertionError if a relative URL is missing or leaves the repository."""
    parts = urlsplit(value)
    if parts.scheme or parts.netloc:
        return
    target = (page.path.parent / unquote(parts.path)).resolve() if parts.path else page.path
    if not target.is_relative_to(ROOT):
        raise AssertionError(f"{page.path}: link leaves repository: {value}")
    if not target.exists():
        raise AssertionError(f"{page.path}: missing link target: {value}")
    if parts.fragment and target.suffix == ".html":
        destination = page if target == page.path else Page(target)
        if unquote(parts.fragment) not in destination.ids:
            raise AssertionError(f"{page.path}: missing fragment: {value}")


def count_files(folder: Path, pattern: str, expected: int) -> None:
    """Require an exact count of nonempty artifacts matching the supplied pattern."""
    files = list(folder.glob(pattern))
    if len(files) != expected or any(p.stat().st_size == 0 for p in files):
        raise AssertionError(f"{folder}: expected {expected} nonempty {pattern}, got {len(files)}")


def findings(folder: Path) -> dict:
    """Load generated findings; propagate missing-file and invalid-JSON errors."""
    return json.loads((folder / "outputs/findings.json").read_text(encoding="utf-8"))


def check_project(number: str) -> None:
    """Check artifacts and recorded invariants for a selected Python project."""
    if number == "08":
        folder = ROOT / "projects/08-nlp-job-postings"
        manifest = json.loads((folder / "results/manifest.json").read_text(encoding="utf-8"))
        for name, expected in manifest["sha256"].items():
            target = (folder / name).resolve()
            if not target.is_relative_to(folder.resolve()):
                raise AssertionError("NLP manifest escapes project")
            if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise AssertionError(f"NLP artifact mismatch: {name}")
        report = Page(folder / "report.html")
        for link in report.links + report.resources:
            check_local_link(report, link)
        source = json.loads((folder / "results/source_audit.json").read_text(encoding="utf-8"))
        assert source["jobs"] == 21663 and source["verified_source_references"] == 22213
        assert source["status"] == "passed" and not any(source["employer_overlap"].values())
        print("Project 08: evidence manifest and report links passed")
        return
    folder = ROOT / "projects" / PROJECTS[number][0]
    if number in {"01", "02"}:
        result = json.loads((folder / "results/verification.json").read_text(encoding="utf-8"))
        tables, values = {"01": (11, 252), "02": (8, 334)}[number]
        expected = {
            "status": "passed",
            "error_outputs": 0,
            "environment_verified": True,
            "analysis_source_synchronized": True,
            "source_hashes_verified": True,
            "primary_content_english": True,
            "reference_tables_verified": tables,
            "numeric_values_compared": values,
            "comparison_rtol": 1e-6,
            "comparison_atol": 1e-8,
        }
        for key, value in expected.items():
            if result.get(key) != value:
                raise AssertionError(f"{folder}: verification {key} != {value!r}: {result}")
        for name in ("FIRST_READ.html", "Research_Analysis.html"):
            if not (folder / name).is_file():
                raise AssertionError(f"{folder}: missing {name}")
    elif number == "03":
        count_files(folder / "data", "*.csv", 7)
        count_files(folder / "charts", "*.png", 8)
        count_files(folder / "charts_en", "*.png", 8)
    elif number == "04":
        count_files(folder / "charts", "*.html", 4)
        data = findings(folder)
        assert data["hourly_rows"] == 17379, data
        assert data["hourly_vs_daily_abs_diff"] == 0, data
        for path in (folder / "charts").glob("*.html"):
            page = Page(path)
            for resource in page.resources:
                if resource.startswith("data:"):
                    continue
                if urlsplit(resource).scheme or resource.startswith("//"):
                    raise AssertionError(f"{path}: network resource {resource}")
                check_local_link(page, resource)
    elif number == "05":
        count_files(folder / "figures", "*.png", 7)
        data = findings(folder)
        assert data["hourly_rows"] == 43824, data
        assert data["longest_gap_hours"] == 155, data
        assert data["hours_left_missing"] == 1891, data
        assert data["observed_pm25_hours"] == 41757, data
        assert data["analysis_excluded_missing_hours"] == 2067, data
    elif number == "06":
        count_files(folder / "figures", "*.png", 7)
        data = findings(folder)
        assert data["rows_after_dedup"] == 8000, data
        assert data["data"]["rows"] == 8020, data
        assert data["not_rejected_segmentations"] == 4, data
        assert data["months_inside_null_band"] == 12, data
    print(f"Project {number}: delivery checks passed")


def main() -> None:
    """Check dependency encoding, selected artifacts, and homepage local links."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", choices=[*PROJECTS, "08"])
    args = parser.parse_args()
    for path in [ROOT / "requirements.txt", *sorted((ROOT / "projects").glob("*/requirements.txt"))]:
        data = path.read_bytes()
        if data.startswith(b"\xef\xbb\xbf"):
            raise AssertionError(f"{path}: UTF-8 BOM is not permitted")
        data.decode("utf-8")
    for number in [args.project] if args.project else [*PROJECTS, "08"]:
        check_project(number)
    if not args.project:
        page = Page(ROOT / "index.html")
        expected = {f"project-{n:02}" for n in range(1, 9)}
        actual = {value for value in page.ids if re.fullmatch(r"project-\d+", value)}
        assert actual == expected, (actual, expected)
        for link in page.links + page.resources:
            check_local_link(page, link)
        print("Homepage: eight project anchors and all local links checked")


if __name__ == "__main__":
    main()
