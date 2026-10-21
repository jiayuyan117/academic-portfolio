"""Regression tests for transcription, year joins, provenance and output integrity."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_pipeline import (COLUMNS, TABLES, build_tables, derive, load_inputs,
                           summary_lines, validate_inputs, validate_outputs, validate_provenance,
                           charging_segments, plot_charging_segments)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.frames, self.factor, self.provenance = load_inputs()

    def test_current_inputs_have_mixed_evidence_and_separate_assumption(self):
        counts = validate_provenance(self.frames, self.factor, self.provenance)
        self.assertEqual(sum(counts.values()), 117)
        self.assertEqual(counts["verified_external"], 21)
        self.assertEqual(counts["assumption"], 1)
        self.assertEqual(counts["compiled_from_coursework"], 93)
        self.assertEqual(counts["needs_verification"], 2)
        with self.assertRaisesRegex(ValueError, "External verification incomplete"):
            validate_provenance(self.frames, self.factor, self.provenance, require_verified=True)

    def test_reordered_years_do_not_change_results(self):
        shuffled = {key: df.sample(frac=1, random_state=23) for key, df in self.frames.items()}
        expected = derive(self.frames, self.factor)
        actual = derive(shuffled, self.factor)
        for key in expected:
            pd.testing.assert_frame_equal(actual[key], expected[key])
        charging = actual["charging"].set_index("year")
        self.assertEqual(charging.loc[2020, "nev_fleet_10k"], 492)
        self.assertEqual(charging.loc[2025, "nev_fleet_10k"], 4397)
        self.assertEqual(charging.loc[2020, "vehicles_per_charger"], 2.93)

    def test_duplicate_year_is_rejected(self):
        self.frames["fleet"].loc[1, "year"] = 2015
        with self.assertRaisesRegex(ValueError, "duplicate year"):
            derive(self.frames, self.factor)

    def test_missing_join_year_is_rejected(self):
        self.frames["fleet"] = self.frames["fleet"].query("year != 2022")
        with self.assertRaisesRegex(ValueError, "missing or unexpected year"):
            derive(self.frames, self.factor)

    def test_fractional_year_is_rejected(self):
        self.frames["fleet"] = self.frames["fleet"].astype({"year": float})
        self.frames["fleet"].loc[0, "year"] = 2015.5
        with self.assertRaisesRegex(ValueError, "year must be integer"):
            validate_inputs(self.frames, self.factor)

    def test_extra_and_missing_columns_are_rejected(self):
        for columns in (["year", "nev_fleet_10k"], ["year", "nev_fleet_10k", "bev_fleet_10k", "extra"]):
            frames = copy.deepcopy(self.frames)
            frames["fleet"] = frames["fleet"].reindex(columns=columns)
            with self.assertRaisesRegex(ValueError, "column schema mismatch"):
                validate_inputs(frames, self.factor)

    def test_invalid_numbers_and_zero_denominators_are_rejected(self):
        for value in (np.nan, np.inf, -1, 0):
            with self.subTest(value=value):
                frames = copy.deepcopy(self.frames)
                frames["charging"].loc[0, "chargers_total_10k"] = value
                with self.assertRaises(ValueError):
                    validate_inputs(frames, self.factor)

    def test_subset_exceeding_total_is_rejected(self):
        self.frames["charging"].loc[0, "chargers_public_10k"] = 1000
        with self.assertRaisesRegex(ValueError, "subset exceeds total"):
            validate_inputs(self.frames, self.factor)

    def test_original_rounded_share_is_retained_and_checked(self):
        output = derive(self.frames, self.factor)["sales"].set_index("year")
        self.assertEqual(output.loc[2025, "reported_share_pct"], 47.9)
        self.assertEqual(output.loc[2025, "nev_share_of_new_sales_pct"], 47.94)
        self.frames["sales"].loc[0, "reported_share_pct"] = 3
        with self.assertRaisesRegex(ValueError, "reported percentage"):
            validate_inputs(self.frames, self.factor)

    def test_provenance_detects_changed_numeric_input(self):
        self.frames["fleet"].loc[0, "nev_fleet_10k"] = 59
        with self.assertRaisesRegex(ValueError, "Provenance value mismatch"):
            validate_provenance(self.frames, self.factor, self.provenance)

    def test_missing_and_duplicate_provenance_are_rejected(self):
        for mode in ("missing", "duplicate"):
            provenance = copy.deepcopy(self.provenance)
            if mode == "missing":
                provenance["records"].pop()
            else:
                provenance["records"].append(provenance["records"][0])
            with self.assertRaisesRegex(ValueError, "provenance"):
                validate_provenance(self.frames, self.factor, provenance)

    def test_unknown_and_missing_source_are_rejected(self):
        for source_ids in ([], ["not_a_source"]):
            provenance = copy.deepcopy(self.provenance)
            provenance["records"][0][-1] = source_ids
            with self.assertRaises(ValueError):
                validate_provenance(self.frames, self.factor, provenance)

    def test_unit_schema_is_checked(self):
        self.provenance["fields"]["fleet.nev_fleet_10k"]["unit"] = "vehicles"
        with self.assertRaisesRegex(ValueError, "incorrect unit"):
            validate_provenance(self.frames, self.factor, self.provenance)

    def test_derived_lineage_cannot_be_missing_or_reference_unknown_fields(self):
        provenance = copy.deepcopy(self.provenance)
        provenance["derivations"].pop("charging.vehicles_per_charger")
        with self.assertRaisesRegex(ValueError, "Derived provenance coverage"):
            validate_provenance(self.frames, self.factor, provenance)
        self.provenance["derivations"]["charging.vehicles_per_charger"]["inputs"] = ["unknown.value"]
        with self.assertRaisesRegex(ValueError, "invalid derived lineage"):
            validate_provenance(self.frames, self.factor, self.provenance)

    def test_candidate_citation_cannot_be_promoted_without_exact_evidence(self):
        row = next(row for row in self.provenance["records"] if row[4] == "needs_verification")
        row[4] = "verified_external"
        with self.assertRaisesRegex(ValueError, "observation-specific evidence"):
            validate_provenance(self.frames, self.factor, self.provenance)

    def test_organization_homepage_is_not_a_document_citation(self):
        self.provenance["sources"]["mofcom_2025"]["url"] = "https://cif.mofcom.gov.cn/"
        with self.assertRaisesRegex(ValueError, "exact document URL"):
            validate_provenance(self.frames, self.factor, self.provenance)

    def test_arithmetic_and_carbon_unit_conversion(self):
        f = derive(self.frames, self.factor)
        first = f["powertrain"].set_index("year").loc[2021]
        self.assertEqual(first.phev_sales_10k, 60.3)
        self.assertEqual(first.total_10k, 351.9)
        self.assertEqual(first.phev_share_pct, 17.14)
        self.assertAlmostEqual(f["battery"].total_gwh.iloc[-1], 769.4)
        self.assertAlmostEqual(f["battery"].lfp_share_pct.iloc[-1], 81.27)
        self.assertAlmostEqual(f["powertrain"].phev_share_pct.iloc[-1], 35.56)
        self.assertAlmostEqual(f["exports"].ice_exports_10k.iloc[-1], 448.3)
        self.assertAlmostEqual(f["carbon"].annual_co2_avoided_100mt.iloc[-1], 0.65955)
        self.assertAlmostEqual(f["carbon"].cumulative_co2_avoided_100mt.iloc[-1], 1.968945)
        np.testing.assert_allclose(f["carbon"].annual_co2_avoided_100mt.cumsum(),
                                   f["carbon"].cumulative_co2_avoided_100mt, atol=1e-9)
        doubled = derive(self.frames, self.factor * 2)
        np.testing.assert_allclose(doubled["carbon"].annual_co2_avoided_100mt,
                                   f["carbon"].annual_co2_avoided_100mt * 2)

    def test_verified_records_require_evidence_type_and_date(self):
        for field in ("evidence_type", "published_at"):
            provenance = copy.deepcopy(self.provenance)
            provenance["sources"]["mofcom_2025"].pop(field)
            with self.assertRaisesRegex(ValueError, "observation-specific evidence"):
                validate_provenance(self.frames, self.factor, provenance)
        self.assertEqual(self.provenance["sources"]["fleet_2025"]["evidence_type"], "secondary_media")
        self.assertEqual(self.provenance["sources"]["mofcom_2025"]["evidence_type"], "government_republication")
        self.assertEqual(self.provenance["sources"]["scio_2021"]["published_at"], "2022-01-12")

    def test_assumption_cannot_be_disguised_as_verified_observation(self):
        self.provenance["records"][-1][4] = "verified_external"
        with self.assertRaisesRegex(ValueError, "Assumption classification"):
            validate_provenance(self.frames, self.factor, self.provenance)

    def test_charging_scope_break_is_exported_and_lines_are_disconnected(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        charging = derive(self.frames, self.factor)["charging"]
        before, after = charging_segments(charging)
        self.assertEqual(before.year.max(), 2024)
        self.assertEqual(after.year.min(), 2025)
        self.assertEqual(after.statistical_scope.iloc[0], "NEA_connectors_2025_revised")
        fig, ax = plt.subplots()
        try:
            for field in ("chargers_total_10k", "public_share_pct", "vehicles_per_charger"):
                lines = plot_charging_segments(ax, charging, field)
                self.assertEqual(len(lines), 2)
                for line in lines:
                    years = set(line.get_xdata())
                    self.assertFalse({2024, 2025}.issubset(years))
        finally:
            plt.close(fig)
        self.provenance["series_breaks"]["charging"]["year"] = 2024
        with self.assertRaisesRegex(ValueError, "charging scope break"):
            validate_provenance(self.frames, self.factor, self.provenance)

    def test_tampered_derived_values_fail_even_with_valid_schema(self):
        outputs = derive(self.frames, self.factor)
        outputs["charging"].loc[0, "vehicles_per_charger"] = 7
        with self.assertRaisesRegex(ValueError, "arithmetic"):
            validate_outputs(outputs, self.frames, self.factor)

    def test_summary_changes_when_input_changes(self):
        base = derive(self.frames, self.factor)
        self.frames["exports"].loc[5, "nev_exports_10k"] = 300
        changed = derive(self.frames, self.factor)
        self.assertNotEqual(summary_lines(base, self.factor)[5], summary_lines(changed, self.factor)[5])
        self.assertIn("42.27%", summary_lines(changed, self.factor)[5])

    def test_csv_roundtrip_and_generated_summary(self):
        # Keep all temporary outputs inside this project.
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as directory:
            tables, _ = build_tables(write=True, output_dir=directory)
            path = Path(directory)
            self.assertEqual(len(list(path.glob("*.csv"))), 7)
            inverse = {v: k for k, v in COLUMNS.items()}
            loaded = {key: pd.read_csv(path / filename).rename(columns=inverse)
                      for key, filename in TABLES.items()}
            validate_outputs(loaded, self.frames, self.factor)
            summary = json.loads((path / "analysis_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["findings_en"], summary_lines(tables, self.factor))


if __name__ == "__main__":
    unittest.main()
