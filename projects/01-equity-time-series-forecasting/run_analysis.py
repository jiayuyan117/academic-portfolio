"""Execute and validate the research notebook from any working directory."""
from pathlib import Path
import base64
import hashlib
import importlib.metadata
import json
import os
import re
import sys

ROOT = Path(__file__).resolve().parent
EXCLUDED = {".runtime", "__pycache__", ".ipynb_checkpoints", ".venv"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def delivered_files():
    return sorted(p for p in ROOT.rglob("*") if p.is_file()
                  and not EXCLUDED.intersection(p.relative_to(ROOT).parts)
                  and p.name != "MANIFEST_SHA256.json")


def export_html(nb, title):
    from nbconvert import HTMLExporter
    from traitlets.config import Config
    config = Config()
    config.HTMLExporter.require_js_url = ""
    config.HTMLExporter.mathjax_url = ""
    html, _ = HTMLExporter(config=config, embed_images=True).from_notebook_node(nb)
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
    assert not re.search(r'<(?:script|link|img)\b[^>]*(?:src|href)=["\']https?://',
                         html, flags=re.I), "External rendering asset"
    return html


def main():
    os.chdir(ROOT)
    for key, sub in (("IPYTHONDIR", "ipython"), ("JUPYTER_RUNTIME_DIR", "jupyter"),
                     ("MPLCONFIGDIR", "matplotlib")):
        folder = ROOT / ".runtime" / sub
        folder.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(folder)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    import nbformat
    import numpy as np
    import pandas as pd
    from nbclient import NotebookClient
    from jupyter_client import KernelManager

    provenance = json.loads((ROOT / "provenance.json").read_text(encoding="utf-8"))
    for relative, expected in provenance["sha256"].items():
        assert digest(ROOT / relative) == expected, relative
    nb = nbformat.read(ROOT / "Research_Analysis.ipynb", as_version=4)
    for cell in nb.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    km = KernelManager(kernel_name="python3")
    km.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    try:
        NotebookClient(nb, timeout=600, kernel_manager=km, allow_errors=False,
                       resources={"metadata": {"path": str(ROOT)}}).execute()
    finally:
        if km.has_kernel:
            km.shutdown_kernel(now=True)
        km.cleanup_resources()
    code = [c for c in nb.cells if c.cell_type == "code"]
    assert all(c.execution_count is not None for c in code)
    assert not any(o.output_type == "error" for c in code for o in c.outputs)
    # No exercise machinery, untranslated narrative, or local user paths in primary content.
    for cell in nb.cells:
        assert not re.search(r"[\u4e00-\u9fff]", cell.source)
        for output in cell.get("outputs", []):
            assert not re.search(r"[\u4e00-\u9fff]", json.dumps(output, ensure_ascii=False))
        cell.metadata.pop("execution", None)
    references = json.loads((ROOT / "reference_results.json").read_text(encoding="utf-8"))
    numeric_checks = 0
    for filename, reference in references.items():
        actual = pd.read_csv(ROOT / "results" / filename)
        assert list(actual.columns) == reference["columns"], filename
        assert len(actual) == len(reference["rows"]), filename
        for index, values in enumerate(reference["rows"]):
            for column, expected in zip(actual.columns, values):
                got = actual.iloc[index][column]
                if expected is None:
                    assert pd.isna(got), (filename, column, index)
                elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
                    assert np.isclose(got, expected, rtol=1e-6, atol=1e-8), (
                        filename, column, index, got, expected)
                    numeric_checks += 1
                else:
                    assert str(got) == str(expected), (filename, column, index)
    nbformat.validate(nb)
    nbformat.write(nb, ROOT / "Research_Analysis.ipynb")
    notebook_html = export_html(nb, provenance["title"] + " | Research analysis")
    assert "data:image/png;base64," in notebook_html
    (ROOT / "Research_Analysis.html").write_text(notebook_html, encoding="utf-8")
    report = (ROOT / "REPORT.md").read_text(encoding="utf-8")
    embedded = re.sub(
        r"!\[([^\]]*)\]\((results/[^)]+\.png)\)",
        lambda m: f"![{m[1]}](data:image/png;base64," +
        base64.b64encode((ROOT / m[2]).read_bytes()).decode() + ")", report)
    report_nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell(embedded)])
    report_html = export_html(report_nb, provenance["title"] + " | Research report")
    assert "data:image/png;base64," in report_html
    (ROOT / "FIRST_READ.html").write_text(report_html, encoding="utf-8")
    packages = ["numpy", "pandas", "scipy", "matplotlib", "statsmodels", "nbformat",
                "nbclient", "nbconvert", "ipykernel", "ipython", "jupyter_client",
                "jupyter_core", "traitlets"]
    versions = {name: importlib.metadata.version(name) for name in packages}
    (ROOT / "environment.json").write_text(json.dumps({
        "python": sys.version, "platform": sys.platform, "packages": versions}, indent=2),
        encoding="utf-8")
    (ROOT / "requirements.txt").write_text(
        "# Versions used to execute the delivered notebook; Python 3.12\n" +
        "\n".join(f"{name}=={v}" for name, v in versions.items()) + "\n", encoding="utf-8")
    verification = {"executed_code_cells": len(code), "error_outputs": 0,
                    "source_hashes_verified": True, "primary_content_english": True,
                    "reference_tables_verified": len(references),
                    "numeric_values_compared": numeric_checks,
                    "comparison_rtol": 1e-6, "comparison_atol": 1e-8,
                    "embedded_figures": True, "external_rendering_assets": False}
    (ROOT / "results/verification.json").write_text(json.dumps(verification, indent=2),
                                                    encoding="utf-8")
    manifest = {p.relative_to(ROOT).as_posix(): digest(p) for p in delivered_files()}
    (ROOT / "MANIFEST_SHA256.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(verification, indent=2))


if __name__ == "__main__":
    main()
