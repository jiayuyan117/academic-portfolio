"""Market-sizing backtest: could the NEV share have been forecast in advance?

Input  : data/01_*.csv and data/06_*.csv (rebuilt by the project pipeline)
Output : results/backtest_forecasts.csv     every origin x model x target year
         results/backtest_errors.csv        mean absolute error by model and horizon
         results/ceiling_fits.csv           fitted S-curve ceiling at each origin
         results/denominator_sensitivity.csv  NEV share under two denominators
         results/09_forecast_backtest.png
         results/backtest_findings.json     every number quoted in README.md

A market-sizing deck usually extrapolates a trend. This script asks how well
that would have worked here, using only data available at each forecast origin.

1. Rolling origins 2020-2024. A model fitted at origin T sees 2015..T only and
   forecasts T+1..2025, so every forecast is genuinely out of sample.
2. Candidates: last value (naive), a linear trend over the latest three years,
   and a logistic S-curve with a fitted ceiling. Fixed-ceiling S-curves (50%,
   70%, 100%) show how much the answer depends on that one assumption.
3. Target: NEV share of CAAM all-vehicle sales including exports, the series
   used for the 47.9% headline. A separate table recomputes it on a domestic
   basis (sales minus exports) to show the denominator effect.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
ORIGINS = [2020, 2021, 2022, 2023, 2024]
LAST_YEAR = 2025
FIXED_CEILINGS = [50, 70, 100]
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titleweight": "bold"})


def load_share() -> pd.Series:
    """NEV share of all-vehicle sales including exports, percent, by year."""
    sales = pd.read_csv(next(DATA.glob("01_*.csv")))
    share = 100 * sales["新能源汽车销量_万辆"] / sales["汽车总销量_万辆"]
    return pd.Series(share.to_numpy(), index=sales["年份"].astype(int).to_numpy(), name="share")


def denominators() -> pd.DataFrame:
    """Recompute the share on an all-sales and a domestic (sales minus exports) basis."""
    sales = pd.read_csv(next(DATA.glob("01_*.csv"))).set_index("年份")
    exports = pd.read_csv(next(DATA.glob("06_*.csv"))).set_index("年份")
    years = exports.index
    table = pd.DataFrame({
        "year": years,
        "share_all_sales_incl_exports": 100 * sales.loc[years, "新能源汽车销量_万辆"]
        / sales.loc[years, "汽车总销量_万辆"],
        "share_domestic": 100 * (sales.loc[years, "新能源汽车销量_万辆"] - exports["新能源汽车出口_万辆"])
        / (sales.loc[years, "汽车总销量_万辆"] - exports["汽车出口总量_万辆"]),
    }).reset_index(drop=True)
    table["difference_pp"] = table["share_domestic"] - table["share_all_sales_incl_exports"]
    return table


def logistic(t, ceiling, rate, midpoint):
    return ceiling / (1 + np.exp(-rate * (t - midpoint)))


def fit_logistic(years: np.ndarray, share: np.ndarray, ceiling: float | None):
    """Least-squares S-curve; a fixed ceiling leaves rate and midpoint free."""
    if ceiling is None:
        params, _ = curve_fit(logistic, years, share,
                              p0=[max(60, share.max() + 1), 0.5, years[-1]],
                              bounds=([share.max(), 0.01, 2010], [100, 3, 2045]),
                              maxfev=20000)
        return params

    def fixed(t, rate, midpoint):
        return logistic(t, ceiling, rate, midpoint)
    (rate, midpoint), _ = curve_fit(fixed, years, share, p0=[0.5, years[-1]],
                                    bounds=([0.01, 2010], [3, 2045]), maxfev=20000)
    return np.array([ceiling, rate, midpoint])


def forecasts(share: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Out-of-sample forecasts for every origin, model and target year."""
    rows, ceilings = [], []
    for origin in ORIGINS:
        seen = share.loc[:origin]          # nothing after the origin is visible
        years, values = seen.index.to_numpy(float), seen.to_numpy()
        targets = np.arange(origin + 1, LAST_YEAR + 1)
        recent = seen.iloc[-3:]
        slope, intercept = np.polyfit(recent.index.to_numpy(float), recent.to_numpy(), 1)
        models = {
            "Naive (last value)": np.full(len(targets), values[-1]),
            "Linear trend, last 3 years": np.clip(intercept + slope * targets, 0, 100),
        }
        fitted = fit_logistic(years, values, None)
        ceilings.append({"origin": origin, "fitted_ceiling": fitted[0],
                         "rate": fitted[1], "midpoint": fitted[2]})
        models["S-curve, fitted ceiling"] = logistic(targets, *fitted)
        for ceiling in FIXED_CEILINGS:
            models[f"S-curve, ceiling {ceiling}%"] = logistic(
                targets, *fit_logistic(years, values, ceiling))
        for name, prediction in models.items():
            for target, value in zip(targets, prediction):
                rows.append({"origin": origin, "model": name, "target_year": int(target),
                             "horizon": int(target - origin), "forecast": float(value),
                             "actual": float(share[target]),
                             "error": float(value - share[target])})
    return pd.DataFrame(rows), pd.DataFrame(ceilings)


def figure(share: pd.Series, table: pd.DataFrame, errors: pd.DataFrame,
           ceilings: pd.DataFrame) -> None:
    colours = {"Naive (last value)": "#8a99a8", "Linear trend, last 3 years": "#1f6fb2",
               "S-curve, fitted ceiling": "#e8a33d", "S-curve, ceiling 100%": "#d9534f"}
    fig, (left, right) = plt.subplots(1, 2, figsize=(12.5, 4.9))
    left.plot(share.index, share.values, color="#14252c", linewidth=2.6, marker="o",
              label="Actual", zorder=5)
    ceiling_2021 = float(ceilings.set_index("origin").loc[2021, "fitted_ceiling"])
    for name, colour in colours.items():
        if name == "S-curve, ceiling 100%":
            continue
        part = table[(table["origin"] == 2021) & (table["model"] == name)]
        label = (f"S-curve, fitted ceiling ({ceiling_2021:.0f}%, at the bound)"
                 if name == "S-curve, fitted ceiling" else name)
        left.plot([2021, *part["target_year"]], [share[2021], *part["forecast"]],
                  color=colour, linestyle="--", marker=".", linewidth=1.8, label=label)
    left.axvline(2021, color="#c9d3dc", linewidth=1)
    left.text(2021.1, 2, "forecast made\nwith data to 2021", fontsize=8.5, color="#586c74")
    left.set_ylabel("NEV share of all-vehicle sales incl. exports (%)")
    left.set_title("What a 2021 analyst would have projected\nfor 2022-2025")
    left.legend(fontsize=8, loc="upper left")

    for name, colour in colours.items():
        part = errors[errors["model"] == name]
        right.plot(part["horizon"], part["mae_pp"], marker="o", linewidth=2,
                   color=colour, label=name)
    right.set_xticks([1, 2, 3, 4, 5])
    right.set_xlabel("Forecast horizon (years ahead)")
    right.set_ylabel("Mean absolute error (percentage points)")
    right.set_title("Out-of-sample error, origins 2020-2024\nfewer origins at longer horizons")
    right.legend(fontsize=8, loc="upper left")
    fig.text(0.01, -0.03, "Each forecast uses only data up to its origin year. Horizon h "
             "averages 6-h origins (5 at h=1, 1 at h=5). Annual series: 11 points, "
             "so errors describe this history, not a general accuracy claim.",
             fontsize=8, color="#7a8a99", ha="left", va="top")
    fig.savefig(RESULTS / "09_forecast_backtest.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    share = load_share()
    table, ceilings = forecasts(share)
    errors = (table.assign(abs_error=table["error"].abs())
              .groupby(["model", "horizon"], sort=False)
              .agg(mae_pp=("abs_error", "mean"), origins=("abs_error", "size")).reset_index())
    overall = table.assign(abs_error=table["error"].abs()).groupby("model", sort=False)["abs_error"].mean()
    denominator = denominators()
    figure(share, table, errors, ceilings)

    table.to_csv(RESULTS / "backtest_forecasts.csv", index=False)
    errors.to_csv(RESULTS / "backtest_errors.csv", index=False)
    ceilings.to_csv(RESULTS / "ceiling_fits.csv", index=False)
    denominator.to_csv(RESULTS / "denominator_sensitivity.csv", index=False)
    from_2021 = table[(table["origin"] == 2021) & (table["target_year"] == LAST_YEAR)]
    findings = {
        "target": "NEV share of CAAM all-vehicle sales including exports, percent",
        "origins": ORIGINS,
        "forecast_count_per_model": int(len(table) / table["model"].nunique()),
        "mae_all_horizons_pp": {k: round(float(v), 2) for k, v in overall.items()},
        "mean_error_pp": {k: round(float(v), 2) for k, v in
                          table.groupby("model", sort=False)["error"].mean().items()},
        "mae_horizon_1_pp": {r.model: round(float(r.mae_pp), 2)
                             for r in errors[errors["horizon"] == 1].itertuples()},
        "forecast_2025_from_2021": {r.model: round(float(r.forecast), 1)
                                    for r in from_2021.itertuples()},
        "actual_2025": round(float(share[LAST_YEAR]), 1),
        "fitted_ceiling_by_origin": {int(r.origin): round(float(r.fitted_ceiling), 1)
                                     for r in ceilings.itertuples()},
        "domestic_vs_all_sales_2025_pp": {
            "all_sales_incl_exports": round(float(denominator["share_all_sales_incl_exports"].iloc[-1]), 1),
            "domestic": round(float(denominator["share_domestic"].iloc[-1]), 1)},
    }
    (RESULTS / "backtest_findings.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(json.dumps(findings, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
