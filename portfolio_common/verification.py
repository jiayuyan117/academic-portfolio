"""Execute and verify research notebooks without changing dependency declarations.

Preflight and regression checks use only the standard library so that failures
can be diagnosed before importing the declared scientific/Jupyter dependencies.
"""

import argparse
import base64
import csv
import hashlib
from html.parser import HTMLParser
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import sys

from portfolio_common.notebook_source import check_analysis_source, source_text


RTOL = 1e-6
ATOL = 1e-8
EXCLUDED = {".runtime", "__pycache__", ".ipynb_checkpoints", ".venv"}
PACKAGES = ("numpy", "pandas", "scipy", "matplotlib", "statsmodels", "nbformat",
            "nbclient", "nbconvert", "ipykernel", "ipython", "jupyter_client",
            "jupyter_core", "traitlets")
CHINESE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U000323af]")


class VerificationError(ValueError):
    """A reproduction invariant failed; never disabled by python -O."""


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify_input_hashes(root, provenance):
    hashes = provenance["sha256"]
    require(bool(hashes), "Input hash list must not be empty.")
    for relative, expected in hashes.items():
        path = root / relative
        require(path.is_file(), f"Missing input: {relative}")
        actual = digest(path)
        require(actual == expected,
                f"Input SHA-256 mismatch: {relative}; expected {expected}, got {actual}")
    return len(hashes)


def declared_versions(text):
    """Read this portfolio's exact pins; fail on unsupported lines, never skip them."""
    pins = {}
    names = set()
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9._-]*)\s*==\s*([A-Za-z0-9.+!-]+)", line)
        require(match is not None,
                f"requirements.txt:{number}: expected an exact package==version pin: {line}")
        name, version = match.groups()
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        require(normalized not in names,
                f"requirements.txt:{number}: duplicate package declaration: {name}")
        pins[name] = version
        names.add(normalized)
    require(bool(pins), "requirements.txt must declare exact package versions.")
    return pins


def verify_environment(root):
    """Always record the observed environment, including failures; requirements is read-only."""
    requirements = root / "requirements.txt"
    report = {
        "python": sys.version,
        "platform": sys.platform,
        "requirements_sha256": digest(requirements),
        "packages": {},
        "declared_versions": {},
        "mismatches": [],
        "status": "failed",
    }
    try:
        pins = declared_versions(requirements.read_text(encoding="utf-8-sig"))
        report["declared_versions"] = pins
        for name in sorted(set(PACKAGES) | set(pins)):
            try:
                actual = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                actual = None
            report["packages"][name] = actual
            if name in pins and actual != pins[name]:
                report["mismatches"].append(
                    {"package": name, "declared": pins[name], "installed": actual})
        differences = "; ".join(
            f"{item['package']}: declared =={item['declared']}, "
            f"installed {item['installed'] or '<missing>'}"
            for item in report["mismatches"])
        require(not differences, "Environment does not match requirements.txt: " + differences)
        report["status"] = "passed"
    except VerificationError as exc:
        report["error"] = str(exc)
        raise
    finally:
        (root / "results").mkdir(exist_ok=True)
        write_json(root / "results" / "environment.json", report)
    return report


def clear_notebook_outputs(notebook):
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
        cell.get("metadata", {}).pop("execution", None)


def verify_notebook(notebook, *, executed=True):
    code = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    require(bool(code), "Notebook must contain code cells.")
    for index, cell in enumerate(notebook["cells"], 1):
        require(not CHINESE.search(source_text(cell)),
                f"Notebook cell {index}: primary source must be English (Chinese text found).")
        for output in cell.get("outputs", []):
            require(not CHINESE.search(json.dumps(output, ensure_ascii=False)),
                    f"Notebook cell {index}: primary output must be English (Chinese text found).")
        if executed and cell["cell_type"] == "code":
            require(cell.get("execution_count") is not None, f"Notebook cell {index} was not executed.")
            require(not any(o["output_type"] == "error" for o in cell["outputs"]),
                    f"Notebook cell {index} has an error output.")
    return len(code)


def verify_reference_tables(root, references):
    """Compare CSV values with the original np.isclose asymmetric tolerance.

    Empty index headers use pandas' exported 'Unnamed: N' names. Missing cells
    remain distinct from zero and string/bool labels are compared exactly.
    """
    require(bool(references), "Reference tables must not be empty.")
    numeric_checks = 0
    for filename, reference in references.items():
        with (root / "results" / filename).open(encoding="utf-8-sig", newline="") as stream:
            records = list(csv.reader(stream))
        require(bool(records), f"{filename}: empty CSV")
        columns = [name or f"Unnamed: {index}" for index, name in enumerate(records[0])]
        require(columns == reference["columns"], f"{filename}: columns differ from reference")
        rows = records[1:]
        require(len(rows) == len(reference["rows"]), f"{filename}: row count differs from reference")
        for index, (actual, expected_row) in enumerate(zip(rows, reference["rows"])):
            require(len(actual) == len(columns) == len(expected_row),
                    f"{filename}, row {index}: column count differs from reference")
            for column, got, expected in zip(columns, actual, expected_row):
                location = f"{filename}, row {index}, column {column}"
                if expected is None:
                    require(got in ("", "NaN", "nan", "NA", "<NA>"),
                            f"{location}: expected a missing value, got {got!r}")
                elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
                    try:
                        value = float(got)
                    except ValueError as exc:
                        raise VerificationError(f"{location}: expected a number, got {got!r}") from exc
                    require(math.isfinite(value) and math.isfinite(expected) and
                            abs(value - expected) <= ATOL + RTOL * abs(expected),
                            f"{location}: got {got}, expected {expected} "
                            f"(rtol={RTOL}, atol={ATOL})")
                    numeric_checks += 1
                else:
                    require(got == str(expected), f"{location}: got {got!r}, expected {expected!r}")
    return numeric_checks


def execute_notebook(notebook, root):
    from nbclient import NotebookClient
    from jupyter_client import KernelManager

    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    try:
        NotebookClient(notebook, timeout=600, kernel_manager=manager, allow_errors=False,
                       resources={"metadata": {"path": str(root)}}).execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
        manager.cleanup_resources()


def verify_embedded_url(url, location):
    url = url.strip()
    require(url.lower().startswith("data:") or url.startswith("#"),
            f"External rendering asset in {location}: {url!r}")


def verify_css_resources(css):
    # tinycss2 is supplied by nbconvert's CSS dependencies. Tokenization handles
    # quoted URLs, CSS escapes and comments that a URL regex would miss.
    import tinycss2

    def inspect(tokens):
        tokens = [token for token in tokens if token.type not in ("comment", "whitespace")]
        for index, token in enumerate(tokens):
            require(token.type != "error", "Invalid CSS rendering resource")
            if token.type == "url":
                verify_embedded_url(token.value, "CSS url()")
            elif token.type == "at-keyword" and token.lower_value == "import":
                require(index + 1 < len(tokens), "Invalid CSS @import")
                target = tokens[index + 1]
                if target.type == "string":
                    verify_embedded_url(target.value, "CSS @import")
                else:
                    require(target.type == "url" or
                            (target.type == "function" and target.lower_name == "url"),
                            "Invalid CSS @import resource")
            elif token.type == "function" and token.lower_name == "url":
                arguments = [item for item in token.arguments
                             if item.type not in ("comment", "whitespace")]
                require(len(arguments) == 1 and arguments[0].type == "string",
                        "Invalid CSS url() resource")
                verify_embedded_url(arguments[0].value, "CSS url()")
            if hasattr(token, "content"):
                inspect(token.content)
            if token.type == "function":
                inspect(token.arguments)

    inspect(tinycss2.parse_component_value_list(css))


def verify_html_resources(html):
    """Require rendering resources to be embedded data or same-document fragments."""
    class ResourceParser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.styles = None

        def handle_starttag(self, tag, attrs):
            for name, value in attrs:
                if value is None:
                    continue
                if (name in ("src", "poster", "background") or
                        (name in ("href", "xlink:href") and
                         tag in ("link", "image", "use", "feimage", "script", "base")) or
                        (tag == "object" and name == "data")):
                    verify_embedded_url(value, f"{tag}[{name}]")
                elif name == "srcset":
                    # URLs end at whitespace; commas within data URLs are legal.
                    remaining = value
                    while remaining.strip(" \t\r\n\f,"):
                        remaining = remaining.lstrip(" \t\r\n\f,")
                        match = re.match(r"\S+", remaining)
                        url = match[0]
                        verify_embedded_url(url.rstrip(","), f"{tag}[srcset]")
                        remaining = remaining[len(url):]
                        if not url.endswith(","):
                            remaining = remaining.partition(",")[2]
                elif name == "style" or "url(" in value.lower():
                    verify_css_resources(value)
            if tag == "style":
                self.styles = []

        def handle_data(self, data):
            if self.styles is not None:
                self.styles.append(data)

        def handle_endtag(self, tag):
            if tag == "style" and self.styles is not None:
                verify_css_resources("".join(self.styles))
                self.styles = None

    parser = ResourceParser()
    parser.feed(html)
    parser.close()
    if parser.styles is not None:
        verify_css_resources("".join(parser.styles))


def export_html(notebook, title):
    from nbconvert import HTMLExporter
    from traitlets.config import Config

    config = Config()
    config.HTMLExporter.require_js_url = ""
    config.HTMLExporter.mathjax_url = ""
    html, _ = HTMLExporter(config=config, embed_images=True).from_notebook_node(notebook)
    html = re.sub(r'<script\b[^>]*\bsrc=["\'][^"\']*["\'][^>]*>.*?</script>',
                  "", html, flags=re.S | re.I)
    html = html.replace("<title>Notebook</title>", f"<title>{title}</title>")
    style = """<style>
body{background:#f2f5f8;color:#203040}
main{max-width:1120px;margin:auto;background:white;padding:24px 32px}
h1,h2,h3{color:#163c61} h1{border-bottom:3px solid #167d8d;padding-bottom:16px}
table{font-variant-numeric:tabular-nums} img{max-width:100%;height:auto}
@media print{body{background:white}main{padding:0}pre{white-space:pre-wrap}}
</style>"""
    html = html.replace("</head>", style + "</head>")
    verify_html_resources(html)
    require("data:image/png;base64," in html, "HTML must contain embedded figures.")
    return html


def preflight(root):
    environment = verify_environment(root)
    provenance = json.loads((root / "provenance.json").read_text(encoding="utf-8"))
    count = verify_input_hashes(root, provenance)
    notebook = json.loads((root / "Research_Analysis.ipynb").read_text(encoding="utf-8"))
    check_analysis_source(root, notebook)
    clear_notebook_outputs(notebook)
    verify_notebook(notebook, executed=False)
    return provenance, environment, count


def run_project(root):
    """Run only this project; all reusable invariants live in this module."""
    root = Path(root).resolve()
    (root / "results").mkdir(exist_ok=True)
    verification_path = root / "results" / "verification.json"
    write_json(verification_path, {"status": "running"})
    try:
        provenance, environment, input_count = preflight(root)
        for key, sub in (("IPYTHONDIR", "ipython"), ("JUPYTER_RUNTIME_DIR", "jupyter"),
                         ("MPLCONFIGDIR", "matplotlib")):
            folder = root / ".runtime" / sub
            folder.mkdir(parents=True, exist_ok=True)
            os.environ[key] = str(folder)
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        import nbformat

        notebook = nbformat.read(root / "Research_Analysis.ipynb", as_version=4)
        clear_notebook_outputs(notebook)
        execute_notebook(notebook, root)
        code_count = verify_notebook(notebook)
        for cell in notebook.cells:
            cell.metadata.pop("execution", None)
        verify_input_hashes(root, provenance)
        require(digest(root / "requirements.txt") == environment["requirements_sha256"],
                "requirements.txt changed during execution.")
        check_analysis_source(root, notebook)
        references = json.loads((root / "reference_results.json").read_text(encoding="utf-8"))
        numeric_checks = verify_reference_tables(root, references)
        nbformat.validate(notebook)
        notebook_html = export_html(notebook, provenance["title"] + " | Research analysis")
        report = (root / "REPORT.md").read_text(encoding="utf-8")
        embedded = re.sub(
            r"!\[([^\]]*)\]\((results/[^)]+\.png)\)",
            lambda m: f"![{m[1]}](data:image/png;base64," +
            base64.b64encode((root / m[2]).read_bytes()).decode() + ")", report)
        report_nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell(embedded)])
        verify_notebook({"cells": notebook["cells"] + report_nb["cells"]})
        report_html = export_html(report_nb, provenance["title"] + " | Research report")
        nbformat.write(notebook, root / "Research_Analysis.ipynb")
        (root / "Research_Analysis.html").write_text(notebook_html, encoding="utf-8")
        (root / "FIRST_READ.html").write_text(report_html, encoding="utf-8")
        verification = {
            "status": "passed", "executed_code_cells": code_count, "error_outputs": 0,
            "source_hashes_verified": True, "source_hash_count": input_count,
            "primary_content_english": True, "analysis_source_synchronized": True,
            "environment_verified": True, "environment_report": "results/environment.json",
            "requirements_sha256": environment["requirements_sha256"],
            "reference_tables_verified": len(references),
            "numeric_values_compared": numeric_checks,
            "comparison_rtol": RTOL, "comparison_atol": ATOL,
            "embedded_figures": True, "external_rendering_assets": False,
        }
        write_json(verification_path, verification)
        files = sorted(p for p in root.rglob("*") if p.is_file()
                       and not EXCLUDED.intersection(p.relative_to(root).parts)
                       and p.name != "MANIFEST_SHA256.json")
        write_json(root / "MANIFEST_SHA256.json",
                   {p.relative_to(root).as_posix(): digest(p) for p in files})
    except Exception as exc:
        write_json(verification_path, {"status": "failed", "error": str(exc)})
        raise
    print(json.dumps(verification, indent=2))
    return verification


def main(root, argv=None):
    parser = argparse.ArgumentParser(description="Execute and verify this project's research notebook.")
    parser.add_argument("--check-only", action="store_true",
                        help="Check environment, input hashes and source sync without executing.")
    args = parser.parse_args(argv)
    try:
        if args.check_only:
            preflight(Path(root).resolve())
            print("Preflight passed; notebook was not executed and numerical results were not revalidated.")
        else:
            run_project(root)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Verification failed: {exc}\n")
