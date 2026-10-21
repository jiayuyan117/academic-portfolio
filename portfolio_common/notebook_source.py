"""Export analysis.py from the canonical Research_Analysis.ipynb, without execution."""

import argparse
import ast
import copy
import json
from pathlib import Path


def source_text(cell):
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else source


def exported_analysis(notebook):
    # This display-only IPython magic is absent from the plain Python export.
    cells = ["\n".join(line for line in source_text(cell).splitlines()
                       if line.strip() != "%matplotlib inline").rstrip()
             for cell in notebook["cells"] if cell["cell_type"] == "code"]
    if not cells:
        raise ValueError("The research notebook must contain code cells.")
    source = ('"""Numerical source exported from Research_Analysis.ipynb."""\n'
              + "\n\n".join("# %%\n" + source for source in cells) + "\n")
    ast.parse(source)
    return source


def check_analysis_source(root, notebook):
    expected = exported_analysis(notebook)
    if (root / "analysis.py").read_text(encoding="utf-8") != expected:
        raise ValueError(
            "analysis.py differs from the canonical Research_Analysis.ipynb. "
            "Regenerate it with portfolio_common/notebook_source.py <project-directory>."
        )


def update_notebook_code(notebook, source):
    """Import an edited cell-delimited export, preserving narrative and display magic.

    This explicit operation supports text editors that cannot save notebook JSON.
    The notebook remains canonical for execution and subsequent exports.
    """
    ast.parse(source)
    parts = source.split("# %%\n")
    if parts[0] != '"""Numerical source exported from Research_Analysis.ipynb."""\n':
        raise ValueError("Expected the generated analysis.py header and cell markers.")
    updated = copy.deepcopy(notebook)
    cells = [cell for cell in updated["cells"] if cell["cell_type"] == "code"]
    if len(parts) - 1 != len(cells):
        raise ValueError("Code cell count changed; edit the canonical notebook directly.")
    changed = False
    for cell, code in zip(cells, parts[1:]):
        original = source_text(cell)
        magic = "%matplotlib inline\n" if original.startswith("%matplotlib inline\n") else ""
        replacement = magic + code.rstrip()
        if replacement != original:
            changed = True
            cell["source"] = replacement.splitlines(keepends=True)
    if exported_analysis(updated) != source:
        raise ValueError("Imported source does not round-trip to the generated export.")
    if changed:
        for cell in cells:
            cell["outputs"] = []
            cell["execution_count"] = None
            cell.get("metadata", {}).pop("execution", None)
    return updated


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("projects", nargs="+", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Check without writing.")
    mode.add_argument("--update-notebook-code", action="store_true",
                      help="Import edits from analysis.py; clear stale notebook outputs.")
    args = parser.parse_args(argv)
    for root in args.projects:
        root = root.resolve()
        notebook = json.loads((root / "Research_Analysis.ipynb").read_text(encoding="utf-8"))
        if args.update_notebook_code:
            source = (root / "analysis.py").read_text(encoding="utf-8")
            notebook = update_notebook_code(notebook, source)
            (root / "Research_Analysis.ipynb").write_text(
                json.dumps(notebook, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8", newline="\n")
            action = "imported into canonical notebook; execution still required"
        elif args.check:
            check_analysis_source(root, notebook)
            action = "checked"
        else:
            (root / "analysis.py").write_text(
                exported_analysis(notebook), encoding="utf-8", newline="\n")
            action = "exported"
        print(f"{root.name}: analysis source {action}")


if __name__ == "__main__":
    main()
