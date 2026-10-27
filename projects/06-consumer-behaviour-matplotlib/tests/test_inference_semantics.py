"""Statistical/report regressions without rebuilding the seven production figures."""

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from scipy import stats


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("consumer_analysis", PROJECT / "src" / "analyze.py")
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)


class InferenceSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df, cls.defects = analysis.load()
        cls.tests = analysis.group_tests(cls.df)

    def test_raw_to_deduplicated_count_and_repeated_users(self):
        self.assertEqual(self.defects["rows"], 8020)
        self.assertEqual(self.defects["duplicate_rows"], 20)
        self.assertEqual(len(self.df), 8000)
        self.assertEqual(self.defects["rows_after_dedup"], 8000)
        self.assertEqual(self.defects["unique_users_after_dedup"], 3997)
        self.assertGreater(self.defects["users_with_multiple_transactions"], 0)
        self.assertEqual(self.df.duplicated().sum(), 0)

    def test_welch_yuen_matches_independent_scipy_two_group_reference(self):
        rng = np.random.default_rng(817)
        groups = [rng.lognormal(0, 1.3, 107), rng.lognormal(0.5, 0.7, 86)]
        for trim in (0.0, 0.1, 0.2):
            with self.subTest(trim=trim):
                actual_f, actual_p = analysis.welch_test(groups, trim=trim)
                reference = stats.ttest_ind(*groups, equal_var=False, trim=trim)
                self.assertAlmostEqual(actual_f, reference.statistic ** 2, places=10)
                self.assertAlmostEqual(actual_p, reference.pvalue, places=12)

    def test_welch_multigroup_matches_scipy_reference(self):
        rng = np.random.default_rng(82)
        groups = [rng.lognormal(mean, scale, n) for mean, scale, n in
                  [(0, 1, 150), (0.6, 0.4, 210), (-0.5, 1.7, 320)]]
        # SciPy >=1.16 offers an independent multi-group Welch implementation.
        reference = stats.f_oneway(*groups, equal_var=False)
        actual_f, actual_p = analysis.welch_test(groups)
        self.assertAlmostEqual(actual_f, reference.statistic, places=10)
        self.assertAlmostEqual(actual_p, reference.pvalue, places=12)

    def test_trimming_is_per_tail_and_reduces_extreme_value_sensitivity(self):
        base = np.arange(1.0, 101.0)
        altered = base.copy()
        altered[-1] = 1e9
        reference = analysis.welch_test([base, base + 3], trim=0.1)
        actual = analysis.welch_test([altered, base + 3], trim=0.1)
        np.testing.assert_allclose(actual, reference, rtol=1e-12)

    def test_missing_labels_denominators_and_familywise_adjustment(self):
        indexed = self.tests.set_index("variable")
        payment = indexed.loc["payment"]
        self.assertEqual(payment.n_used, self.df["payment"].notna().sum())
        self.assertEqual(payment.n_missing_group, self.df["payment"].isna().sum())
        for method in ("anova", "welch", "kruskal", "trimmed_welch"):
            np.testing.assert_allclose(
                self.tests[f"{method}_p_bonferroni"],
                np.minimum(1, self.tests[f"{method}_p"] * len(analysis.GROUPINGS)))
        self.assertGreater(indexed.loc["membership", "anova_p"], 0)
        self.assertLess(indexed.loc["membership", "anova_p"], 0.01)
        self.assertNotIn("user_mean_welch_p", indexed.columns)
        self.assertFalse(indexed.loc["age_group", "significant_bonferroni"])

    def test_generated_report_states_estimands_counts_and_unperformed_experiment(self):
        correlations = analysis.correlation_table(self.df)
        membership = self.df.groupby("membership")["amount"].mean().reset_index(
            name="mean_amount")
        findings = {
            "user_cluster_sensitivity": analysis.cluster_sensitivity(self.df, draws=20).to_dict("records"),
            "data": self.defects, "rows_after_dedup": len(self.df),
            "not_rejected_segmentations": int((~self.tests.significant_bonferroni).sum()),
            "basket_identity": {"r_vs_expected": 0.937, "r2_vs_expected": 0.878,
                                "ratio_median": 1.0, "ratio_q75": 1.1},
            "top_two_category_revenue_share": 0.5854,
            "months_inside_null_band": 12, "months_total": 12,
        }
        report = analysis.render_readme(findings, self.tests, correlations, membership)
        for required in ("8,020 raw rows", "8,000 analysed transactions", "20 exact duplicates",
                         "arithmetic means", "trimmed means", "comparable distribution shapes",
                         "User-cluster bootstrap sensitivity", "not rejected",
                         "no pairwise comparisons", "proposed, not performed",
                         "No A/B test", "intention to treat"):
            self.assertIn(required, report)
        for overclaim in ("don't differ at all", "the data says *absent*",
                          "no seasonality either", "shift of the whole distribution"):
            self.assertNotIn(overclaim, report)
        changed = self.tests.copy()
        changed.loc[changed["variable"] == "membership", "trimmed_welch_p"] = 0.4321
        self.assertIn("trimmed Welch-Yuen 0.432",
                      analysis.render_readme(findings, changed, correlations, membership))

    def test_membership_caption_uses_computed_p_values(self):
        changed = self.tests.copy()
        changed.loc[changed["variable"] == "membership", "trimmed_welch_p"] = 0.4321
        with patch.object(analysis, "save") as save:
            analysis.fig_membership(self.df, changed)
        figure, _, caption = save.call_args.args
        analysis.plt.close(figure)
        self.assertIn("0.43", caption)
        self.assertNotIn("1.6e-09", caption)
        self.assertIn("Different estimands", caption)

    def test_cluster_draws_match_literal_whole_user_resampling(self):
        # Unequal transaction counts distinguish transaction vs customer weighting.
        frame = pd.DataFrame({
            "user_id": ["a", "a", "a", "b", "b", "c", "c"],
            "segment": ["A", "A", "B", "A", "B", "A", "B"],
            "amount": [0., 6., 13., 30., 40., 60., 70.]})
        levels, means, actual = analysis.cluster_mean_draws(frame, "segment", draws=40, seed=8)
        self.assertEqual(levels, ["A", "B"])
        np.testing.assert_allclose(means, [24., 41.])
        self.assertNotAlmostEqual(means[0], (3 + 30 + 60) / 3)
        rng = np.random.default_rng(8)
        expected = []
        users = frame.user_id.unique()
        for _ in range(40):
            selected = rng.choice(users, size=len(users), replace=True)
            expanded = pd.concat([frame.loc[frame.user_id == user] for user in selected])
            expected.append(expanded.groupby("segment").amount.mean().reindex(levels))
        np.testing.assert_allclose(actual, expected)

    def test_cross_group_shared_customer_variation_cancels(self):
        # Every user's B value is A+7: whole-cluster draws must preserve that contrast.
        frame = pd.DataFrame({
            "user_id": np.repeat(np.arange(8), 2),
            "segment": ["A", "B"] * 8,
            "amount": np.repeat(np.arange(8) * 100., 2) + np.tile([0., 7.], 8)})
        with patch.object(analysis, "GROUPINGS", [("segment", "Segment")]):
            result = analysis.cluster_sensitivity(frame, draws=100).iloc[0]
        self.assertEqual(result.users_crossing_groups, 8)
        np.testing.assert_allclose([result.mean_difference, result.ci_low, result.ci_high], 7.)
        # Independent group resampling would introduce spurious contrast variation.

    def test_empty_groups_missing_labels_and_invalid_ids(self):
        frame = pd.DataFrame({"user_id": ["a", "b", "c"],
                              "segment": ["A", "B", None], "amount": [1., 8., 99.]})
        with patch.object(analysis, "GROUPINGS", [("segment", "Segment")]):
            result = analysis.cluster_sensitivity(frame, draws=100).iloc[0]
        self.assertEqual(result.n_users, 3)
        self.assertEqual(result.n_used, 2)
        self.assertEqual(result.n_missing_group, 1)
        self.assertLess(result.valid_draws, 100)
        self.assertTrue(pd.isna(result.ci_low))
        self.assertIn("undefined", result.status)
        frame.loc[0, "user_id"] = None
        with self.assertRaises(ValueError):
            analysis.cluster_mean_draws(frame, "segment")

    def test_cluster_reproducibility_and_percentiles(self):
        with patch.object(analysis, "GROUPINGS", [("membership", "Membership tier")]):
            table = analysis.cluster_sensitivity(self.df, draws=60, seed=23)
            analysis.RNG = np.random.default_rng(999)
            repeated = analysis.cluster_sensitivity(self.df, draws=60, seed=23)
        pd.testing.assert_frame_equal(table, repeated)
        levels, means, draws = analysis.cluster_mean_draws(
            self.df, "membership", draws=60, seed=23)
        for row in table.itertuples():
            i, j = levels.index(row.reference), levels.index(row.comparison)
            self.assertAlmostEqual(row.mean_difference, means[j] - means[i])
            np.testing.assert_allclose([row.ci_low, row.ci_high],
                                       np.percentile(draws[:, j] - draws[:, i], [2.5, 97.5]))


if __name__ == "__main__":
    unittest.main()
