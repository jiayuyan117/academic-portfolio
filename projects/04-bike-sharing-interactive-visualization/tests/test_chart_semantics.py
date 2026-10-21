"""Focused checks; build tiny charts in a temporary directory, not shipped outputs."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bike_charts", PROJECT / "src" / "build_charts.py")
charts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(charts)


class ChartSemanticsTests(unittest.TestCase):
    def test_registered_share_uses_label_not_position(self):
        users = pd.DataFrame(
            {"user_type": ["Registered", "Casual"], "share": [0.812, 0.188]},
            index=[37, 1])
        self.assertEqual(charts.registered_share(users), 0.812)
        self.assertEqual(charts.registered_share(users.iloc[::-1]), 0.812)
        with self.assertRaises(KeyError):
            charts.registered_share(users.loc[[1]])
        with self.assertRaises(ValueError):
            charts.registered_share(pd.concat([users, users]))

    def test_reconciliation_joins_actual_dates_and_rejects_missing_days(self):
        hourly = charts.load_hourly()
        daily = charts.daily_crosscheck(hourly)
        self.assertEqual(len(daily), 731)
        self.assertEqual(daily["crosscheck_diff"].abs().sum(), 0)
        incomplete = hourly[hourly["date"] != hourly["date"].min()]
        with self.assertRaisesRegex(ValueError, "unmatched"):
            charts.daily_crosscheck(incomplete)

    def test_offline_validator_rejects_external_resources_and_missing_runtime(self):
        for resource in (
            '<script src="https://cdn.example/plotly.js"></script>',
            '<script src="assets/echarts.js"></script>',
            '<link rel="stylesheet" href="https://example/style.css">',
            '<iframe src="https://example/chart"></iframe>',
        ):
            with self.subTest(resource=resource), self.assertRaises(ValueError):
                charts.validate_offline_html(resource)
        with self.assertRaises(ValueError):
            charts.validate_offline_html("<html><body>empty chart</body></html>")

    def test_reconciliation_rejects_duplicate_daily_dates(self):
        hourly = charts.load_hourly()
        day = pd.read_csv(charts.DATA / "day.csv")
        for adjustment in (0, 1):
            duplicate = day.iloc[[0]].copy()
            duplicate["cnt"] += adjustment
            corrupted = pd.concat([day, duplicate], ignore_index=True)
            with self.subTest(adjustment=adjustment), patch.object(
                    charts.pd, "read_csv", return_value=corrupted):
                with self.assertRaises(pd.errors.MergeError):
                    charts.daily_crosscheck(hourly)

    def test_four_exports_embed_runtime_and_preserve_visual_encodings(self):
        hourly = pd.DataFrame({
            "season_label": np.repeat(charts.SEASON_ORDER, 3),
            "weather_label": ["Clear"] * 12,
            "time_period": ["Morning peak"] * 12,
            "temp": np.linspace(0.1, 0.8, 12),
            "windspeed": np.linspace(0.05, 0.6, 12),
            "hum": np.linspace(0.2, 0.9, 12),
            "cnt": np.arange(12) + 10,
        })
        dates = pd.to_datetime(["2011-01-01", "2011-01-03", "2012-01-01", "2012-01-02"])
        daily = pd.DataFrame({
            "date": dates, "year": dates.year, "day_csv_cnt": [10, 20, 30, 40],
            "workingday": [0, 1, 0, 1], "holiday": [1, 0, 1, 0]})
        exported = {}
        real_writer = charts.write_offline_html

        def capture(figure, filename):
            exported[filename] = figure
            real_writer(figure, filename)

        with tempfile.TemporaryDirectory(dir=PROJECT) as temporary:
            with patch.object(charts, "CHARTS", Path(temporary)), patch.object(
                    charts, "write_offline_html", side_effect=capture):
                charts.build_sunburst(charts.sunburst_table(hourly))
                charts.build_density_contour(hourly)
                charts.build_calendar_heatmap(daily)
                charts.build_season_timeline(hourly)
            self.assertEqual(len(exported), 4)
            for name in exported:
                html = (Path(temporary) / name).read_text(encoding="utf-8")
                charts.validate_offline_html(html)
                self.assertIn("Offline supported", html)

        self.assertEqual(exported["01_sunburst.html"].data[0].type, "sunburst")
        self.assertEqual(exported["02_density_contour.html"].data[0].type, "histogram2dcontour")
        calendar = exported["03_calendar_heatmap.html"]
        for trace, expected in zip(calendar.data, ([10, 20], [30, 40])):
            matrix = np.asarray(trace.z)
            self.assertEqual(matrix.shape[0], 7)
            np.testing.assert_array_equal(np.sort(matrix[np.isfinite(matrix)]), expected)
            self.assertEqual(trace.zmax, 40)
        animation = exported["04_season_timeline.html"]
        self.assertEqual([frame.name for frame in animation.frames], charts.SEASON_ORDER)
        self.assertEqual(tuple(animation.layout.xaxis.range), (0, 1))
        self.assertEqual(tuple(animation.layout.yaxis.range), (0, 1))
        for frame in animation.frames:
            scatter = frame.data[0]
            self.assertEqual(np.asarray(scatter.customdata).shape[1], 2)
            self.assertTrue(np.all(np.asarray(scatter.marker.size) > 0))
            self.assertTrue(np.all(np.asarray(scatter.marker.opacity) <= 0.9))
        self.assertEqual(animation.layout.updatemenus[0].buttons[0].label, "Play")
        self.assertEqual(len(animation.layout.sliders[0].steps), 4)

    def test_generated_report_carries_computed_share_and_offline_contract(self):
        report = charts.render_readme({
            "hourly_rows": 123, "zero_count_hours": 0, "severe_weather_hours": 2,
            "registered_share": 0.75, "hourly_vs_daily_abs_diff": 0,
            "busiest_day": {"date": "2012-01-01", "rides": 400},
            "rides_by_time_period": {"Evening peak": 300, "Morning peak": 100}})
        self.assertIn("75.0%", report)
        self.assertIn("3.00 times", report)
        self.assertIn("Offline", report)
        self.assertIn("No pilot or causal evaluation has been run", report)


if __name__ == "__main__":
    unittest.main()
