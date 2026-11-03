"""Out-of-sample integrity checks for the market-sizing backtest."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import market_backtest  # noqa: E402


class MarketBacktestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.share = market_backtest.load_share()
        cls.table, cls.ceilings = market_backtest.forecasts(cls.share)

    def test_forecasts_ignore_data_after_origin(self):
        """Changing a post-origin value must not change any forecast from that origin."""
        altered = self.share.copy()
        altered.loc[2022:] = altered.loc[2022:] + 5
        table, _ = market_backtest.forecasts(altered)
        for origin in (2020, 2021):
            before = self.table[self.table["origin"] == origin]["forecast"].to_numpy()
            after = table[table["origin"] == origin]["forecast"].to_numpy()
            np.testing.assert_allclose(before, after)

    def test_only_future_targets(self):
        self.assertTrue((self.table["target_year"] > self.table["origin"]).all())
        self.assertTrue((self.table["horizon"] >= 1).all())

    def test_share_matches_headline(self):
        self.assertAlmostEqual(round(float(self.share[2025]), 1), 47.9)

    def test_domestic_basis_removes_exports(self):
        table = market_backtest.denominators()
        self.assertEqual(round(float(table["share_domestic"].iloc[-1]), 1), 50.8)


if __name__ == "__main__":
    unittest.main()
