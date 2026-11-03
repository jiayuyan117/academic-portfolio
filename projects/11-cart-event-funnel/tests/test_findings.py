"""Invariants that the committed findings must satisfy; run after analysis/analyze.py."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F = json.loads((ROOT / "results" / "findings.json").read_text(encoding="utf-8"))


class FindingsTest(unittest.TestCase):
    def test_accepted_log_reproduces_simulated_truth(self):
        self.assertEqual(F["sessions_where_accepted_log_differs_from_truth"], 0)

    def test_counts_reconcile(self):
        self.assertEqual(F["raw_attempts"], F["accepted_events"] + F["rejected_attempts"])
        self.assertEqual(sum(F["rejections_by_reason"].values()), F["rejected_attempts"])

    def test_event_counting_overstates_purchases(self):
        self.assertGreater(F["event_count_purchase_rate"], F["session_rates"]["ordered"])
        self.assertGreater(F["mean_event_count_bias_pp"], 0)

    def test_session_intervals_cover_population_rates(self):
        for stage, (lo, hi) in F["session_rates_ci95"].items():
            self.assertLessEqual(lo, F["population_rates"][stage], stage)
            self.assertGreaterEqual(hi, F["population_rates"][stage], stage)

    def test_coverage_is_near_nominal_only_for_session_counting(self):
        # 200 replicates: a 95% interval should cover between roughly 91% and 98% of the time.
        self.assertGreaterEqual(F["session_interval_coverage"], 0.91)
        self.assertLessEqual(F["session_interval_coverage"], 0.98)
        self.assertLess(F["event_count_interval_coverage"], 0.80)

    def test_clock_skew_audit_is_nested(self):
        audit = F["timestamp_audit"]
        self.assertLessEqual(audit["sessions_with_impossible_funnel_order"], audit["sessions_reordered_by_client_ts"])
        self.assertGreater(audit["sessions_with_impossible_funnel_order"], 0)


if __name__ == "__main__":
    unittest.main()
