"""Next-day pollution alert: does a model beat simple persistence out of sample?

Input  : data/PRSA_data_2010.1.1-2014.12.31.csv
Output : figures/08_next_day_alert.png
         outputs/07_alert_metrics.csv          test-year metrics for every rule
         outputs/08_alert_test_predictions.csv one row per test day
         outputs/alert_findings.json           every number quoted in README.md

Decision framed: at the end of day d, should an operations team issue an alert
for day d+1 (for example, moving outdoor shifts or issuing masks)? An alert day
is one whose daily mean PM2.5 exceeds 75 ug/m3, the GB 3095-2012 grade II
*daily* limit, so the reference value is used on the time scale it defines.

Design choices:

1. Daily means need at least MIN_HOURS observed hours (GB 3095-2012 validity
   rule). Days below that are excluded as targets and as feature days; nothing
   is interpolated.
2. Strict temporal split: fit on 2010-2012, choose the alert threshold on 2013,
   evaluate once on 2014. No 2014 information is used for any choice.
3. Features use only day d observations. The dataset has no archived weather
   forecasts, so a separate "perfect weather forecast" variant adds day d+1
   observed meteorology. It is an upper bound on what a forecast could add,
   not a deployable model.
4. The baseline is a two-state persistence rule fitted on training data:
   P(alert tomorrow | alert today) and P(alert tomorrow | no alert today).
5. Uncertainty: paired moving-block bootstrap over test days (7-day blocks)
   for the difference between each model and persistence.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "PRSA_data_2010.1.1-2014.12.31.csv"
FIGURES = ROOT / "figures"
OUTPUTS = ROOT / "outputs"

LIMIT = 75          # GB 3095-2012 grade II daily PM2.5 limit, ug/m3
MIN_HOURS = 20      # minimum valid hours for a daily mean
COST_RATIO = 3      # assumed cost of a missed alert day / cost of a false alarm
COST_RATIOS = [1, 2, 3, 5, 10]
BLOCK = 7
BOOTSTRAP = 2000
SEED = 20260103

TODAY = ["pm_mean", "pm_last", "pm_evening", "iws_last", "dewp_mean",
         "pres_mean", "pres_change", "temp_mean", "calm_last", "nw_last",
         "month_sin", "month_cos"]
TOMORROW = ["next_iws_max", "next_dewp_mean", "next_pres_change", "next_nw_share"]


def daily_frame() -> pd.DataFrame:
    """One row per day: today's features, tomorrow's weather and target."""
    df = pd.read_csv(DATA, na_values=["NA"])
    df["timestamp"] = pd.to_datetime(df[["year", "month", "day", "hour"]])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df.loc[df["pm2.5"] < 0, "pm2.5"] = np.nan
    df["date"] = df["timestamp"].dt.normalize()
    groups = df.groupby("date")
    day = pd.DataFrame({
        "valid_hours": groups["pm2.5"].count(),
        "pm_mean": groups["pm2.5"].mean(),
        "pm_last": groups["pm2.5"].last(),
        "pm_evening": df[df["hour"] >= 18].groupby("date")["pm2.5"].mean(),
        "iws_last": groups["Iws"].last(),
        "iws_max": groups["Iws"].max(),
        "dewp_mean": groups["DEWP"].mean(),
        "pres_mean": groups["PRES"].mean(),
        "pres_change": groups["PRES"].last() - groups["PRES"].first(),
        "temp_mean": groups["TEMP"].mean(),
        "calm_last": groups["cbwd"].last().eq("cv").astype(float),
        "nw_last": groups["cbwd"].last().eq("NW").astype(float),
        "nw_share": groups["cbwd"].apply(lambda s: s.eq("NW").mean()),
    })
    day.loc[day["valid_hours"] < MIN_HOURS, "pm_mean"] = np.nan
    month = day.index.month
    day["month_sin"] = np.sin(2 * np.pi * month / 12)
    day["month_cos"] = np.cos(2 * np.pi * month / 12)
    day["alert_today"] = (day["pm_mean"] > LIMIT).astype(float).where(day["pm_mean"].notna())

    nxt = day.shift(-1)
    # shift(-1) is only "tomorrow" if the next row is the next calendar day.
    consecutive = (day.index.to_series().shift(-1) - day.index.to_series()) == pd.Timedelta(days=1)
    day["target"] = nxt["alert_today"].where(consecutive)
    day["next_iws_max"] = nxt["iws_max"]
    day["next_dewp_mean"] = nxt["dewp_mean"]
    day["next_pres_change"] = nxt["pres_change"]
    day["next_nw_share"] = nxt["nw_share"]
    day = day.dropna(subset=["target", *TODAY, *TOMORROW, "alert_today"])
    day["year"] = day.index.year
    return day


def fit_logit(train: pd.DataFrame, columns: list[str]):
    """Fit a standardized logistic regression; return a predict function."""
    mean, std = train[columns].mean(), train[columns].std().replace(0, 1)
    design = sm.add_constant((train[columns] - mean) / std)
    model = sm.Logit(train["target"], design).fit(disp=False, maxiter=200)

    def predict(frame: pd.DataFrame) -> np.ndarray:
        x = sm.add_constant((frame[columns] - mean) / std, has_constant="add")
        return model.predict(x).to_numpy()
    return predict


def persistence(train: pd.DataFrame):
    """Two-state persistence probabilities estimated on the training years."""
    rates = train.groupby("alert_today")["target"].mean()
    return lambda frame: frame["alert_today"].map(rates).to_numpy()


def expected_cost(y: np.ndarray, alert: np.ndarray, ratio: float) -> float:
    """Average cost per day; a false alarm costs 1, a missed alert day costs ratio."""
    missed = (y == 1) & ~alert
    false_alarm = (y == 0) & alert
    return float((ratio * missed + false_alarm).mean())


def best_threshold(y: np.ndarray, p: np.ndarray, ratio: float) -> float:
    """Validation-year threshold minimizing expected cost."""
    grid = np.round(np.arange(0.05, 0.951, 0.01), 2)
    costs = [expected_cost(y, p >= t, ratio) for t in grid]
    return float(grid[int(np.argmin(costs))])


def auc(y: np.ndarray, p: np.ndarray) -> float:
    """Rank-based ROC AUC (ties share the average rank)."""
    ranks = pd.Series(p).rank().to_numpy()
    positives = y == 1
    n_pos, n_neg = positives.sum(), (~positives).sum()
    return float((ranks[positives].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def block_indices(n: int, rng: np.random.Generator) -> np.ndarray:
    """Moving-block bootstrap sample of n positions."""
    starts = rng.integers(0, n - BLOCK + 1, size=int(np.ceil(n / BLOCK)))
    return np.concatenate([np.arange(s, s + BLOCK) for s in starts])[:n]


def main() -> None:
    FIGURES.mkdir(exist_ok=True)
    OUTPUTS.mkdir(exist_ok=True)
    day = daily_frame()
    train, valid, test = (day[day["year"] <= 2012], day[day["year"] == 2013],
                          day[day["year"] == 2014])

    rules = {
        "Persistence (baseline)": persistence(train),
        "Logistic, today's data": fit_logit(train, TODAY),
        "Logistic + perfect weather forecast": fit_logit(train, TODAY + TOMORROW),
    }
    y_valid, y_test = valid["target"].to_numpy(), test["target"].to_numpy()
    rng = np.random.default_rng(SEED)
    samples = [block_indices(len(test), rng) for _ in range(BOOTSTRAP)]

    rows, predictions = [], pd.DataFrame({"date": test.index.date, "alert_day": y_test})
    base_p = rules["Persistence (baseline)"](test)
    base_t = best_threshold(y_valid, rules["Persistence (baseline)"](valid), COST_RATIO)
    base_cost = expected_cost(y_test, base_p >= base_t, COST_RATIO)
    for name, rule in rules.items():
        p_test = rule(test)
        threshold = best_threshold(y_valid, rule(valid), COST_RATIO)
        alert = p_test >= threshold
        brier = (p_test - y_test) ** 2
        base_brier = (base_p - y_test) ** 2
        cost_day = COST_RATIO * ((y_test == 1) & ~alert) + ((y_test == 0) & alert)
        base_cost_day = (COST_RATIO * ((y_test == 1) & ~(base_p >= base_t))
                         + ((y_test == 0) & (base_p >= base_t)))
        d_brier = [float((brier[s] - base_brier[s]).mean()) for s in samples]
        d_cost = [float((cost_day[s] - base_cost_day[s]).mean()) for s in samples]
        hits = int(((y_test == 1) & alert).sum())
        rows.append({
            "rule": name,
            "threshold": threshold,
            "brier": float(brier.mean()),
            "auc": auc(y_test, p_test),
            "alert_days_caught": hits,
            "alert_days_total": int(y_test.sum()),
            "recall": hits / y_test.sum(),
            "false_alarms": int(((y_test == 0) & alert).sum()),
            "alerts_issued": int(alert.sum()),
            "cost_per_day": float(cost_day.mean()),
            "brier_diff_vs_baseline": float(brier.mean() - base_brier.mean()),
            "brier_diff_ci_low": float(np.quantile(d_brier, 0.025)),
            "brier_diff_ci_high": float(np.quantile(d_brier, 0.975)),
            "cost_diff_vs_baseline": float(cost_day.mean() - base_cost),
            "cost_diff_ci_low": float(np.quantile(d_cost, 0.025)),
            "cost_diff_ci_high": float(np.quantile(d_cost, 0.975)),
        })
        predictions[name] = np.round(p_test, 6)
    metrics = pd.DataFrame(rows)

    # Cost sensitivity: threshold re-chosen on 2013 for every assumed ratio.
    sensitivity = []
    for ratio in COST_RATIOS:
        for name, rule in rules.items():
            t = best_threshold(y_valid, rule(valid), ratio)
            sensitivity.append({"ratio": ratio, "rule": name,
                                "cost": expected_cost(y_test, rule(test) >= t, ratio)})
    sensitivity = pd.DataFrame(sensitivity)
    figure(metrics, sensitivity)

    metrics.to_csv(OUTPUTS / "07_alert_metrics.csv", index=False)
    predictions.to_csv(OUTPUTS / "08_alert_test_predictions.csv", index=False)
    by_rule = metrics.set_index("rule")
    findings = {
        "target": f"next-day daily mean PM2.5 > {LIMIT} ug/m3, days with >= {MIN_HOURS} valid hours",
        "split": "fit 2010-2012, threshold 2013, test 2014",
        "days": {"train": len(train), "validation": len(valid), "test": len(test)},
        "test_alert_days": int(y_test.sum()),
        "cost_ratio_missed_to_false_alarm": COST_RATIO,
        "bootstrap": f"paired moving-block, block {BLOCK} days, {BOOTSTRAP} resamples, seed {SEED}",
        "rules": {name: {key: (round(value, 4) if isinstance(value, float) else value)
                         for key, value in row.items()}
                  for name, row in by_rule.to_dict(orient="index").items()},
        "cost_sensitivity": {f"{r['rule']} @ {r['ratio']}:1": round(r["cost"], 4)
                             for r in sensitivity.to_dict(orient="records")},
    }
    (OUTPUTS / "alert_findings.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(json.dumps(findings, indent=2))


def figure(metrics: pd.DataFrame, sensitivity: pd.DataFrame) -> None:
    """Left: cost difference vs persistence with 95% CI. Right: cost by assumed ratio."""
    colours = {"Persistence (baseline)": "#8a99a8", "Logistic, today's data": "#1f6fb2",
               "Logistic + perfect weather forecast": "#e8a33d"}
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.8),
                                      gridspec_kw={"width_ratios": [1, 1.15]})
    models = metrics[metrics["rule"] != "Persistence (baseline)"].reset_index(drop=True)
    for index, row in models.iterrows():
        left.errorbar(row["cost_diff_vs_baseline"], index,
                      xerr=[[row["cost_diff_vs_baseline"] - row["cost_diff_ci_low"]],
                            [row["cost_diff_ci_high"] - row["cost_diff_vs_baseline"]]],
                      fmt="o", color=colours[row["rule"]], capsize=5, markersize=8)
    left.axvline(0, color="#425362", linewidth=1)
    left.set_yticks(range(len(models)), [r.replace(" + ", "\n+ ") for r in models["rule"]])
    left.set_ylim(-0.6, len(models) - 0.4)
    left.set_xlabel(f"Cost per day minus persistence (2014, {COST_RATIO}:1 miss : false alarm)")
    left.set_title("Change in alert cost vs persistence\n95% block-bootstrap interval; left of 0 is better")

    for name, group in sensitivity.groupby("rule", sort=False):
        right.plot(group["ratio"], group["cost"], marker="o", linewidth=2,
                   color=colours[name], label=name)
    right.set_xscale("log")
    right.set_xticks(COST_RATIOS, [f"{r}:1" for r in COST_RATIOS])
    right.set_xlabel("Assumed cost of a missed alert day : a false alarm")
    right.set_ylabel("Cost per test day (2014)")
    right.set_title("Ranking under other cost assumptions\nthreshold re-chosen on 2013 for each ratio")
    right.legend(fontsize=8.5, loc="lower right")
    fig.suptitle("Next-day PM2.5 alert, Beijing: fit 2010-2012, tune 2013, test 2014",
                 fontweight="bold", y=1.02)
    fig.text(0.01, -0.03, "Alert day = daily mean PM2.5 > 75 ug/m3 (GB 3095-2012 grade II), "
             f">= {MIN_HOURS} valid hours. 'Perfect weather forecast' uses observed next-day "
             "meteorology: an upper bound, not a deployable model.",
             fontsize=8, color="#7a8a99", ha="left", va="top")
    fig.savefig(FIGURES / "08_next_day_alert.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
