"""Temporal-integrity checks for the next-day alert model."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import alert_model  # noqa: E402


class AlertModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.day = alert_model.daily_frame()

    def test_target_is_next_calendar_day(self):
        """Each target must equal the following calendar day's own alert flag."""
        day = self.day
        nxt = day.index + pd.Timedelta(days=1)
        both = nxt.isin(day.index)
        expected = day.loc[nxt[both], "alert_today"].to_numpy()
        self.assertTrue(np.array_equal(day.loc[both, "target"].to_numpy(), expected))

    def test_today_features_exclude_tomorrow(self):
        """No same-day feature may equal tomorrow's daily mean by construction."""
        self.assertNotIn("next_pm_mean", alert_model.TODAY)
        self.assertTrue(all(not c.startswith("next_") for c in alert_model.TODAY))

    def test_daily_mean_needs_valid_hours(self):
        """Days with too few valid hours never enter as feature days."""
        self.assertTrue((self.day["valid_hours"] >= alert_model.MIN_HOURS).all())

    def test_years_are_disjoint_and_ordered(self):
        years = sorted(self.day["year"].unique())
        self.assertEqual(years, [2010, 2011, 2012, 2013, 2014])

    def test_threshold_minimizes_validation_cost(self):
        y = np.array([0, 0, 1, 1])
        p = np.array([0.1, 0.2, 0.8, 0.9])
        self.assertLessEqual(alert_model.best_threshold(y, p, 3), 0.8)
        self.assertEqual(alert_model.expected_cost(y, p >= 0.5, 3), 0.0)


if __name__ == "__main__":
    unittest.main()
