"""Tests target scientific failure modes, not merely execution."""
import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run import FOREIGN, LOCAL, block_interval, features, model, predict


def sample():
    rng = np.random.default_rng(4)
    return pd.DataFrame(rng.normal(0, .01, (400, 9)),
                        columns=["ISE", "ISE_USD", *FOREIGN],
                        index=pd.bdate_range("2000-01-01", periods=400))


class TemporalIntegrity(unittest.TestCase):
    def test_future_perturbation_cannot_change_features(self):
        raw = sample()
        changed = raw.copy()
        changed.iloc[250:] *= 100
        before, after = features(raw), features(changed)
        pd.testing.assert_frame_equal(before.loc[:raw.index[249], LOCAL + FOREIGN],
                                      after.loc[:raw.index[249], LOCAL + FOREIGN])

    def test_foreign_information_is_lagged(self):
        raw = sample()
        s = features(raw)
        self.assertEqual(s.loc[raw.index[100], "SP"], raw.iloc[99].SP)
        self.assertEqual(s.loc[raw.index[100], "return"], raw.iloc[100].ISE)

    def test_label_alignment_and_missing_last_target(self):
        raw = sample()
        s = features(raw)
        self.assertNotIn(raw.index[-1], s.index)
        self.assertEqual(s.loc[raw.index[100], "target_date"], raw.index[101])
        self.assertEqual(s.loc[raw.index[100], "y"], int(raw.iloc[101].ISE > 0))

    def test_purge_excludes_boundary_label(self):
        s = features(sample())
        for start in [150, 200, 250, 300, 350]:
            self.assertLess(s.iloc[:start-1].target_date.max(), s.iloc[start].name)
            self.assertEqual(s.iloc[:start].target_date.max(), s.iloc[start].name)

    def test_scaling_uses_only_training_distribution(self):
        s = features(sample())
        train = s.iloc[:150]
        fit = model("lr_0.1").fit(train[LOCAL], train.y)
        expected = train[LOCAL].mean().to_numpy()
        np.testing.assert_allclose(fit[0].mean_, expected)
        fit.predict_proba(s.iloc[151:][LOCAL] * 1000)
        np.testing.assert_allclose(fit[0].mean_, expected)

    def test_prior_does_not_use_test_labels(self):
        s = features(sample())
        tr, te = s.iloc[:150], s.iloc[151:]
        changed = te.copy()
        changed["y"] = 1 - changed.y
        np.testing.assert_array_equal(predict("prior", tr, te, LOCAL),
                                       predict("prior", tr, changed, LOCAL))

    def test_paired_identity_interval(self):
        self.assertEqual(block_interval(np.zeros(100)), [0, 0])


if __name__ == "__main__":
    unittest.main()
