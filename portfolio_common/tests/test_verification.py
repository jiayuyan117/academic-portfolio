"""Core regression tests; no scientific packages or notebook execution required."""

import ast
import copy
import csv
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, Mock, patch

REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY))

from portfolio_common import verification as verifier
from portfolio_common.notebook_source import (
    check_analysis_source, exported_analysis, update_notebook_code,
)

PROJECTS = (
    REPOSITORY / "projects" / "01-equity-time-series-forecasting",
    REPOSITORY / "projects" / "02-shanghai-hongkong-market-linkages",
)


class TemporaryProject(unittest.TestCase):
    def setUp(self):
        runtime = REPOSITORY / "portfolio_common" / ".runtime"
        runtime.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=runtime)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "results").mkdir()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


class InputHashTests(TemporaryProject):
    def test_each_input_and_preserved_source_is_verified(self):
        names = ("prices.csv", "source_materials/prices.csv", "source_materials/course.ipynb")
        hashes = {name: verifier.digest(self.write(name, name)) for name in names}
        self.assertEqual(verifier.verify_input_hashes(self.root, {"sha256": hashes}), 3)
        for name in names:
            with self.subTest(name=name):
                self.write(name, "tampered")
                with self.assertRaisesRegex(verifier.VerificationError, "SHA-256 mismatch"):
                    verifier.verify_input_hashes(self.root, {"sha256": hashes})
                self.write(name, name)

    def test_missing_input_and_empty_manifest_fail(self):
        for hashes in ({"missing.csv": "0" * 64}, {}):
            with self.subTest(hashes=hashes), self.assertRaises(verifier.VerificationError):
                verifier.verify_input_hashes(self.root, {"sha256": hashes})


class EnvironmentTests(TemporaryProject):
    def setUp(self):
        super().setUp()
        self.requirements = self.write("requirements.txt", "# Exact pins\nnumpy==1.2.3\n")
        self.original = self.requirements.read_bytes()
        self.write("environment.json", '{"historical": true}\n')

    def report(self):
        return json.loads((self.root / "results" / "environment.json").read_text(encoding="utf-8"))

    def assert_declarations_unchanged(self):
        self.assertEqual(self.requirements.read_bytes(), self.original)
        self.assertEqual((self.root / "environment.json").read_text(), '{"historical": true}\n')

    def test_matching_environment_is_recorded_separately(self):
        with patch.object(importlib.metadata, "version", return_value="1.2.3"):
            verifier.verify_environment(self.root)
        report = self.report()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["declared_versions"], {"numpy": "1.2.3"})
        self.assertEqual(report["packages"]["numpy"], "1.2.3")
        self.assertEqual(report["requirements_sha256"], verifier.digest(self.requirements))
        self.assert_declarations_unchanged()

    def test_drift_fails_and_records_both_versions(self):
        with patch.object(importlib.metadata, "version", return_value="9.9.9"):
            with self.assertRaisesRegex(verifier.VerificationError, "declared ==1.2.3, installed 9.9.9"):
                verifier.verify_environment(self.root)
        self.assertEqual(self.report()["mismatches"],
                         [{"package": "numpy", "declared": "1.2.3", "installed": "9.9.9"}])
        self.assertEqual(self.report()["status"], "failed")
        self.assert_declarations_unchanged()

    def test_missing_package_is_a_clear_failure(self):
        with patch.object(importlib.metadata, "version",
                          side_effect=importlib.metadata.PackageNotFoundError("numpy")):
            with self.assertRaisesRegex(verifier.VerificationError, "<missing>"):
                verifier.verify_environment(self.root)
        self.assertIsNone(self.report()["packages"]["numpy"])
        self.assert_declarations_unchanged()

    def test_invalid_declaration_is_not_silently_ignored(self):
        for text in ("numpy>=1.0\n", "-r elsewhere.txt\n", "numpy==1.*\n", "# no pins\n",
                     "jupyter_client==1.0\nJupyter-Client==1.0\n"):
            with self.subTest(text=text):
                self.write("requirements.txt", text)
                with self.assertRaises(verifier.VerificationError):
                    verifier.verify_environment(self.root)
                self.assertEqual(self.report()["status"], "failed")
                self.assertEqual(self.requirements.read_text(), text)

    def test_bom_and_comments_are_accepted_without_rewriting(self):
        self.write("requirements.txt", "\ufeffnumpy==1.2.3  # declared version\n")
        before = self.requirements.read_bytes()
        with patch.object(importlib.metadata, "version", return_value="1.2.3"):
            verifier.verify_environment(self.root)
        self.assertEqual(before, self.requirements.read_bytes())

    def test_failed_preflight_does_not_execute_or_retain_old_success(self):
        self.write("results/verification.json", '{"status": "passed"}')
        with patch.object(importlib.metadata, "version", return_value="9.9.9"), \
                patch.object(verifier, "execute_notebook") as execute:
            with self.assertRaises(verifier.VerificationError):
                verifier.run_project(self.root)
        execute.assert_not_called()
        result = json.loads((self.root / "results" / "verification.json").read_text())
        self.assertEqual(result["status"], "failed")
        self.assert_declarations_unchanged()


class NumericTests(TemporaryProject):
    def setUp(self):
        super().setUp()
        self.references = {"table.csv": {
            "columns": ["Unnamed: 0", "Estimate", "Missing", "Converged", "Model"],
            "rows": [[0, 100.0, None, True, "MA(2)"]],
        }}

    def table(self, row=None, header=None):
        with (self.root / "results" / "table.csv").open(
                "w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header or ["", "Estimate", "Missing", "Converged", "Model"])
            if row is not False:
                writer.writerow(row or [0, 100.0, "", True, "MA(2)"])

    def test_exact_values_missing_cells_and_boolean_labels_pass(self):
        self.table()
        self.assertEqual(verifier.verify_reference_tables(self.root, self.references), 2)

    def test_relative_tolerance_inside_and_outside_boundary(self):
        for delta, passes in ((0.000099, True), (0.000101, False), (-0.000101, False)):
            with self.subTest(delta=delta):
                self.table([0, 100.0 + delta, "", True, "MA(2)"])
                if passes:
                    self.assertEqual(verifier.verify_reference_tables(self.root, self.references), 2)
                else:
                    with self.assertRaisesRegex(verifier.VerificationError, "column Estimate"):
                        verifier.verify_reference_tables(self.root, self.references)

    def test_absolute_tolerance_is_not_widened_near_zero(self):
        self.references["table.csv"]["rows"][0][1] = 0.0
        for actual, passes in ((0.9e-8, True), (1.1e-8, False)):
            self.table([0, actual, "", True, "MA(2)"])
            if passes:
                verifier.verify_reference_tables(self.root, self.references)
            else:
                with self.assertRaises(verifier.VerificationError):
                    verifier.verify_reference_tables(self.root, self.references)

    def test_nonfinite_missing_and_nonnumeric_values_cannot_pass_numeric_checks(self):
        for value in ("NaN", "inf", "-inf", "", "not a number"):
            with self.subTest(value=value):
                self.table([0, value, "", True, "MA(2)"])
                with self.assertRaises(verifier.VerificationError):
                    verifier.verify_reference_tables(self.root, self.references)

    def test_null_boolean_and_text_changes_fail(self):
        for row in ([0, 100, 0, True, "MA(2)"], [0, 100, "", False, "MA(2)"],
                    [0, 100, "", 1, "MA(2)"], [0, 100, "", True, "AR(2)"]):
            with self.subTest(row=row):
                self.table(row)
                with self.assertRaises(verifier.VerificationError):
                    verifier.verify_reference_tables(self.root, self.references)

    def test_schema_row_count_and_truncated_reference_fail(self):
        self.table(header=["wrong", "Estimate", "Missing", "Converged", "Model"])
        with self.assertRaisesRegex(verifier.VerificationError, "columns differ"):
            verifier.verify_reference_tables(self.root, self.references)
        self.table(row=False)
        with self.assertRaisesRegex(verifier.VerificationError, "row count"):
            verifier.verify_reference_tables(self.root, self.references)
        self.table([0, 100, "", True])
        with self.assertRaisesRegex(verifier.VerificationError, "column count"):
            verifier.verify_reference_tables(self.root, self.references)
        self.table()
        self.references["table.csv"]["rows"][0].pop()
        with self.assertRaisesRegex(verifier.VerificationError, "column count"):
            verifier.verify_reference_tables(self.root, self.references)


class NotebookTests(TemporaryProject):
    def setUp(self):
        super().setUp()
        self.notebook = {"cells": [
            {"cell_type": "markdown", "source": ["# Research\n"], "metadata": {}},
            {"cell_type": "code", "source": ["%matplotlib inline\n", "value = 1\n"],
             "metadata": {"execution": {"old": "timestamp"}}, "execution_count": 7,
             "outputs": [{"output_type": "stream", "name": "stdout", "text": "old result"}]},
        ]}

    def test_clear_removes_prior_outputs_counts_and_execution_metadata(self):
        verifier.clear_notebook_outputs(self.notebook)
        code = self.notebook["cells"][1]
        self.assertEqual(code["outputs"], [])
        self.assertIsNone(code["execution_count"])
        self.assertNotIn("execution", code["metadata"])
        verifier.verify_notebook(self.notebook, executed=False)
        with self.assertRaisesRegex(verifier.VerificationError, "not executed"):
            verifier.verify_notebook(self.notebook)

    def test_chinese_in_narrative_code_or_output_is_rejected(self):
        for location in ("markdown", "code", "output"):
            with self.subTest(location=location):
                notebook = copy.deepcopy(self.notebook)
                if location == "markdown":
                    notebook["cells"][0]["source"] = "\u4e2d\u6587"
                elif location == "code":
                    notebook["cells"][1]["source"] = "# \u4e2d\u6587"
                else:
                    notebook["cells"][1]["outputs"][0]["text"] = "\u4e2d\u6587"
                with self.assertRaisesRegex(verifier.VerificationError, "Chinese text found"):
                    verifier.verify_notebook(notebook)

    def test_error_outputs_and_empty_notebooks_are_rejected(self):
        self.notebook["cells"][1]["outputs"] = [
            {"output_type": "error", "ename": "ValueError", "evalue": "bad data"}]
        with self.assertRaisesRegex(verifier.VerificationError, "error output"):
            verifier.verify_notebook(self.notebook)
        with self.assertRaisesRegex(verifier.VerificationError, "code cells"):
            verifier.verify_notebook({"cells": []})

    def test_export_is_valid_python_and_detects_source_drift(self):
        source = exported_analysis(self.notebook)
        ast.parse(source)
        self.assertNotIn("%matplotlib", source)
        self.write("analysis.py", source)
        check_analysis_source(self.root, self.notebook)
        self.write("analysis.py", source.replace("value = 1", "value = 2"))
        with self.assertRaisesRegex(ValueError, "differs from the canonical"):
            check_analysis_source(self.root, self.notebook)

    def test_import_preserves_narrative_and_magic_but_invalidates_stale_outputs(self):
        source = exported_analysis(self.notebook).replace("value = 1", "value = 2")
        updated = update_notebook_code(self.notebook, source)
        self.assertEqual(updated["cells"][0], self.notebook["cells"][0])
        self.assertEqual(updated["cells"][1]["source"][0], "%matplotlib inline\n")
        self.assertEqual(updated["cells"][1]["outputs"], [])
        self.assertIsNone(updated["cells"][1]["execution_count"])
        self.assertEqual(exported_analysis(updated), source)
        self.assertEqual(self.notebook["cells"][1]["execution_count"], 7)
        with self.assertRaisesRegex(ValueError, "cell count"):
            update_notebook_code(self.notebook, source + "\n# %%\nother = 3\n")

    def test_kernel_uses_current_python_and_project_cwd_and_cleans_up_on_failure(self):
        manager = Mock()
        manager.has_kernel = True
        client = Mock()
        client.execute.side_effect = RuntimeError("kernel failure")
        factory = Mock(return_value=client)
        modules = {
            "nbclient": types.SimpleNamespace(NotebookClient=factory),
            "jupyter_client": types.SimpleNamespace(KernelManager=Mock(return_value=manager)),
        }
        with patch.dict(sys.modules, modules):
            with self.assertRaisesRegex(RuntimeError, "kernel failure"):
                verifier.execute_notebook(self.notebook, self.root)
        self.assertEqual(manager.kernel_spec.argv[0], sys.executable)
        self.assertEqual(factory.call_args.kwargs["resources"]["metadata"]["path"], str(self.root))
        self.assertFalse(factory.call_args.kwargs["allow_errors"])
        manager.shutdown_kernel.assert_called_once_with(now=True)
        manager.cleanup_resources.assert_called_once_with()


class HtmlResourceTests(unittest.TestCase):
    def test_external_html_resources_are_rejected(self):
        for html in (
            '<img src="//cdn.example/image.png">',
            '<IMG SRC=//cdn.example/image.png>',
            '<img src="&#47;&#47;cdn.example/image.png">',
            '<link rel="stylesheet" href="//cdn.example/style.css">',
            '<link rel="stylesheet" href="styles/local.css">',
            '<img src="../images/plot.png">',
            '<img src="/images/plot.png">',
            '<script src="https://cdn.example/script.js"></script>',
            '<svg><image href="plot.svg"></image><use href="//cdn.example/symbols.svg#x"/></svg>',
            '<video poster="poster.png"></video>',
            '<img srcset="data:image/png;base64,AAAA 1x, //cdn.example/image.png 2x">',
        ):
            with self.subTest(html=html), self.assertRaisesRegex(
                    verifier.VerificationError, "External rendering asset"):
                verifier.verify_html_resources(html)

    def test_external_css_resources_are_rejected(self):
        for css in (
            '@import "//cdn.example/style.css";',
            '@import "local.css" screen;',
            '@import url(https://cdn.example/style.css);',
            'body { background: url(../image.png); }',
            'body { background: URL("//cdn.example/image.png"); }',
            '@font-face { src: url("/font.woff2") format("woff2"); }',
            r'@im\70ort "local.css";',
            r'body { background: u\72l(\2f\2f cdn.example/image.png); }',
            '@media screen { body { background: url(local.png); } }',
        ):
            with self.subTest(css=css), self.assertRaisesRegex(
                    verifier.VerificationError, "External rendering asset"):
                verifier.verify_html_resources(f"<style>{css}</style>")
        with self.assertRaisesRegex(verifier.VerificationError, "External rendering asset"):
            verifier.verify_html_resources('<div style="background:url(//cdn.example/image.png)"></div>')

    def test_embedded_resources_fragments_and_navigation_links_are_allowed(self):
        verifier.verify_html_resources("""
            <style>
              /* url(ignored.png) is a comment */
              @import "data:text/css,body%7Bcolor:black%7D";
              .plot { background: url("data:image/png;base64,AAAA"); filter: url(#filter); }
              .label::after { content: 'url(not-a-resource.png)'; }
            </style>
            <link rel="stylesheet" href="data:text/css,body%7Bcolor:black%7D">
            <img src="data:image/png;base64,AAAA">
            <img srcset="data:image/png;base64,AAAA 1x, data:image/png;base64,BBBB 2x">
            <svg><use href="#symbol"/></svg>
            <div style="filter:url('#filter')"></div>
            <a href="https://example.com/reference">Reference</a>
        """)

    def test_export_html_applies_resource_checks_after_export(self):
        exporter = Mock()
        exporter.from_notebook_node.return_value = (
            '<html><head></head><img src="data:image/png;base64,AAAA">'
            '<link rel="stylesheet" href="//cdn.example/style.css"></html>', {})
        with patch.dict(sys.modules, {"nbconvert": types.SimpleNamespace(
                HTMLExporter=Mock(return_value=exporter))}):
            with self.assertRaisesRegex(verifier.VerificationError, "External rendering asset"):
                verifier.export_html({}, "Research")


class RepositoryChecks(unittest.TestCase):
    def test_existing_inputs_and_tables_match_unchanged_references(self):
        for project, count, hashes in zip(PROJECTS, (252, 334), (3, 5)):
            with self.subTest(project=project.name):
                provenance = json.loads((project / "provenance.json").read_text(encoding="utf-8"))
                self.assertEqual(verifier.verify_input_hashes(project, provenance), hashes)
                references = json.loads((project / "reference_results.json").read_text(encoding="utf-8"))
                self.assertEqual(verifier.verify_reference_tables(project, references), count)

    def test_project_sources_are_synchronized_and_syntax_is_valid(self):
        for project in PROJECTS:
            with self.subTest(project=project.name):
                notebook = json.loads((project / "Research_Analysis.ipynb").read_text(encoding="utf-8"))
                check_analysis_source(project, notebook)
                # Edited notebooks may deliberately have no execution outputs yet.
                verifier.verify_notebook(notebook, executed=False)
                ast.parse((project / "analysis.py").read_text(encoding="utf-8"))
                ast.parse((project / "run_analysis.py").read_text(encoding="utf-8"))
        for path in (REPOSITORY / "portfolio_common").rglob("*.py"):
            if ".runtime" not in path.parts:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_entrypoints_import_from_project_and_unrelated_directories(self):
        for project in PROJECTS:
            for cwd in (project, REPOSITORY.parent):
                with self.subTest(project=project.name, cwd=str(cwd)):
                    process = subprocess.run(
                        [sys.executable, "-B", str(project / "run_analysis.py"), "--help"],
                        cwd=cwd, text=True, capture_output=True, timeout=20)
                    self.assertEqual(process.returncode, 0, process.stderr)
                    self.assertIn("--check-only", process.stdout)

    def test_equity_analysis_reuses_fits_and_refits_only_shorter_training_prefixes(self):
        """Exercise actual orchestration with lightweight model/data doubles."""
        source = (PROJECTS[0] / "analysis.py").read_text(encoding="utf-8")
        cells = source.split("# %%\n")[1:]

        def sample(size):
            result = MagicMock()
            result.__len__.return_value = size
            return result

        train = sample(100)
        train.iloc.__getitem__.side_effect = lambda key: sample(key.stop)
        fit = MagicMock()
        comparison = MagicMock()
        comparison.loc.__getitem__.return_value = 123.0
        candidates = Mock(return_value=({"MA(2)": fit}, comparison, "MA(2)"))
        residual_check = Mock(return_value=(MagicMock(), MagicMock()))
        plot = MagicMock()
        plot.subplots.return_value = (MagicMock(), MagicMock())
        scope = {
            "train": train, "test": MagicMock(), "H": 20,
            "candidates": candidates, "ORDERS": {"MA(2)": (0, 0, 2)},
            "save_table": Mock(), "save_figure": Mock(), "metrics": MagicMock(),
            "residual_check": residual_check, "plot_acf": Mock(),
            "np": MagicMock(), "pd": MagicMock(), "plt": plot, "stability": [],
        }
        with patch("builtins.print"):
            for cell in cells[2:5]:  # Model comparison, diagnostics, return forecasts.
                exec(compile(cell, "equity_orchestration", "exec"), scope)
        loop = next(node for node in ast.parse(cells[-1]).body
                    if isinstance(node, ast.For) and node.target.id == "fraction")
        exec(compile(ast.Module(body=[loop], type_ignores=[]), "stability_loop", "exec"), scope)

        self.assertEqual([len(call.args[0]) for call in candidates.call_args_list], [100, 60, 80])
        residual_check.assert_called_once_with(train, fit, (0, 0, 2))
        fit.get_forecast.assert_called_once_with(steps=20)
        self.assertEqual([row["Training_fraction"] for row in scope["stability"]], [.6, .8, 1.])


if __name__ == "__main__":
    unittest.main()
