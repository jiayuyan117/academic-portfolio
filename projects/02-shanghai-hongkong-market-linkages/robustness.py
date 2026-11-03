"""Robustness extension: many forecast origins and an order-free variance decomposition.

Input  : VARSJ.csv (the same return data as the main notebook)
Output : results/robustness_rolling_forecasts.csv  one row per evaluated day
         results/robustness_forecast_tests.csv     MSE/MAE and Diebold-Mariano tests
         results/robustness_gfevd.csv              generalized vs Cholesky FEVD
         results/robustness.png
         results/robustness_summary.json           every number quoted in REPORT.md

The main notebook scores one 20-day holdout and shows that a Cholesky variance
decomposition flips from 32.4% to 0.35% with variable order. This script asks
the two follow-up questions a reviewer would ask:

1. Does the forecast verdict survive many origins? The last EVAL_DAYS returns are
   forecast one step ahead. VAR(1) and VAR(7) are re-estimated every REFIT_EVERY
   days on an expanding window that ends before the forecast day, and compared
   with zero-return and historical-mean baselines using Diebold-Mariano tests
   (Newey-West variance, Harvey-Leybourne-Newbold small-sample correction).
2. What does an order-free decomposition say? The generalized FEVD of Pesaran
   and Shin (1998) does not depend on variable order. Its value is compared
   with both Cholesky orderings, with the same-day residual correlation that
   the Cholesky orderings allocate to one market or the other.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.api import VAR

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
EVAL_DAYS = 500
REFIT_EVERY = 20
LAGS = (1, 7)
HOLDOUT = 20            # the main notebook's untouched holdout, kept for comparability
HORIZONS = (1, 5, 10)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})


def load_returns() -> pd.DataFrame:
    """Daily log returns in percent, sorted by date; same construction as the notebook."""
    raw = pd.read_csv(ROOT / "VARSJ.csv", encoding="gbk")
    prices = raw[["SZH", "XGH"]].apply(pd.to_numeric)
    prices.index = pd.to_datetime(raw.iloc[:, 0])
    prices = prices.sort_index()
    return 100 * np.log(prices).diff().dropna()


def rolling_forecasts(returns: pd.DataFrame) -> pd.DataFrame:
    """One-step forecasts for the last EVAL_DAYS days, using only earlier data."""
    start = len(returns) - EVAL_DAYS
    rows, fits = [], {}
    for t in range(start, len(returns)):
        if (t - start) % REFIT_EVERY == 0:
            history = returns.iloc[:t]
            fits = {p: VAR(history.reset_index(drop=True)).fit(p, trend="c") for p in LAGS}
            mean = history.mean()
        row = {"date": returns.index[t].date()}
        for name in returns.columns:
            row[f"actual_{name}"] = returns.iloc[t][name]
            row[f"mean_{name}"] = mean[name]
            row[f"zero_{name}"] = 0.0
        for p, fit in fits.items():
            lagged = returns.iloc[t - p:t].to_numpy()       # strictly before day t
            forecast = fit.forecast(lagged, steps=1)[0]
            for index, name in enumerate(returns.columns):
                row[f"var{p}_{name}"] = forecast[index]
        rows.append(row)
    return pd.DataFrame(rows)


def diebold_mariano(loss_model: np.ndarray, loss_base: np.ndarray, lags: int = 5):
    """DM statistic (HLN-corrected) and two-sided p-value; negative favours the model."""
    d = loss_model - loss_base
    n = len(d)
    centred = d - d.mean()
    variance = centred @ centred / n
    for k in range(1, lags + 1):
        weight = 1 - k / (lags + 1)
        variance += 2 * weight * (centred[k:] @ centred[:-k]) / n
    statistic = d.mean() / np.sqrt(variance / n)
    statistic *= np.sqrt((n - 1) / n)                    # HLN correction for h = 1
    return float(statistic), float(2 * stats.t.sf(abs(statistic), df=n - 1))


def forecast_tests(table: pd.DataFrame, names) -> pd.DataFrame:
    rows = []
    for name in names:
        actual = table[f"actual_{name}"].to_numpy()
        zero_sq = actual ** 2
        for model in ("var1", "var7", "mean"):
            error = table[f"{model}_{name}"].to_numpy() - actual
            for loss, values, base in (("squared", error ** 2, zero_sq),
                                       ("absolute", np.abs(error), np.abs(actual))):
                dm, p = diebold_mariano(values, base)
                rows.append({"series": name, "model": model, "loss": loss,
                             "model_loss": float(values.mean()), "zero_loss": float(base.mean()),
                             "relative_to_zero": float(values.mean() / base.mean()),
                             "dm_stat": dm, "p_value": p})
    return pd.DataFrame(rows)


def generalized_fevd(fit, horizon: int) -> np.ndarray:
    """Pesaran-Shin generalized FEVD, rows normalized to sum to one; [response, horizon, shock]."""
    sigma = fit.sigma_u.to_numpy() if hasattr(fit.sigma_u, "to_numpy") else fit.sigma_u
    phi = fit.ma_rep(horizon - 1)                        # Phi_0 .. Phi_{h-1}
    k = sigma.shape[0]
    out = np.zeros((k, horizon, k))
    for h in range(1, horizon + 1):
        numerator = np.zeros((k, k))
        denominator = np.zeros(k)
        for step in range(h):
            numerator += (phi[step] @ sigma) ** 2
            denominator += np.diag(phi[step] @ sigma @ phi[step].T)
        theta = numerator / np.diag(sigma)[None, :] / denominator[:, None]
        out[:, h - 1, :] = theta / theta.sum(axis=1, keepdims=True)
    return out


def decompositions(train: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    rows = []
    fit = VAR(train.reset_index(drop=True)).fit(7, trend="c")
    general = generalized_fevd(fit, max(HORIZONS))
    names = list(train.columns)
    for order in (["SZH", "XGH"], ["XGH", "SZH"]):
        cholesky = VAR(train[order].reset_index(drop=True)).fit(7, trend="c").fevd(max(HORIZONS)).decomp
        for h in HORIZONS:
            rows.append({"method": f"Cholesky [{', '.join(order)}]", "response": "XGH",
                         "shock": "SZH", "horizon": h,
                         "share_pct": 100 * cholesky[order.index("XGH"), h - 1, order.index("SZH")]})
    for h in HORIZONS:
        rows.append({"method": "Generalized (order-free)", "response": "XGH", "shock": "SZH",
                     "horizon": h,
                     "share_pct": 100 * general[names.index("XGH"), h - 1, names.index("SZH")]})
    residual = fit.resid.to_numpy() if hasattr(fit.resid, "to_numpy") else fit.resid
    correlation = float(np.corrcoef(residual.T)[0, 1])
    return pd.DataFrame(rows), correlation


def figure(tests: pd.DataFrame, fevd: pd.DataFrame, correlation: float) -> None:
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.6))
    sq = tests[(tests["loss"] == "squared")].copy()
    labels = {"var1": "VAR(1)", "var7": "VAR(7)", "mean": "Historical mean"}
    colours = {"SZH": "#1f6fb2", "XGH": "#e8a33d"}
    width = 0.36
    for offset, name in ((-width / 2, "SZH"), (width / 2, "XGH")):
        part = sq[sq["series"] == name].reset_index(drop=True)
        bars = left.bar(np.arange(len(part)) + offset, 100 * (part["relative_to_zero"] - 1),
                        width, color=colours[name], label=name)
        for bar, p in zip(bars, part["p_value"]):
            y = max(bar.get_height(), 0)
            left.text(bar.get_x() + bar.get_width() / 2, y + 0.06,
                      f"p={p:.2f}", ha="center", va="bottom", fontsize=8, color="#425362")
    top = 100 * (sq["relative_to_zero"].max() - 1)
    left.set_ylim(min(-0.3, 100 * (sq["relative_to_zero"].min() - 1) - 0.1), top * 1.18)
    left.axhline(0, color="#425362", linewidth=1)
    left.set_xticks(range(3), [labels[m] for m in ("var1", "var7", "mean")])
    left.set_ylabel("MSE vs zero-return forecast (%)")
    left.set_title(f"{EVAL_DAYS} one-step forecasts, refit every {REFIT_EVERY} days\n"
                   "above 0 is worse than predicting no change; DM p-values")
    left.legend(title="Market")

    for method, colour in (("Cholesky [SZH, XGH]", "#d9534f"), ("Cholesky [XGH, SZH]", "#8a99a8"),
                           ("Generalized (order-free)", "#14252c")):
        part = fevd[fevd["method"] == method]
        right.plot(part["horizon"], part["share_pct"], marker="o", linewidth=2.2,
                   color=colour, label=method)
    right.set_xticks(HORIZONS)
    right.set_xlabel("Forecast horizon (trading days)")
    right.set_ylabel("Share of XGH forecast-error variance\nattributed to SZH shocks (%)")
    right.set_ylim(-1, 38)
    right.set_title("An order-free decomposition sits between\n"
                    f"the Cholesky extremes; same-day residual corr. = {correlation:.2f}")
    right.legend(fontsize=8.5, loc="center right")
    fig.tight_layout()
    fig.savefig(RESULTS / "robustness.png", dpi=170)
    plt.close(fig)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    returns = load_returns()
    train = returns.iloc[:-HOLDOUT]
    table = rolling_forecasts(returns)
    tests = forecast_tests(table, returns.columns)
    fevd, correlation = decompositions(train)
    figure(tests, fevd, correlation)

    table.to_csv(RESULTS / "robustness_rolling_forecasts.csv", index=False)
    tests.to_csv(RESULTS / "robustness_forecast_tests.csv", index=False)
    fevd.to_csv(RESULTS / "robustness_gfevd.csv", index=False)
    summary = {
        "evaluation": {"days": EVAL_DAYS, "first": str(table["date"].iloc[0]),
                       "last": str(table["date"].iloc[-1]), "refit_every_days": REFIT_EVERY,
                       "window": "expanding, ends before each forecast day"},
        "squared_loss": {f"{r.model} {r.series}": {"relative_mse_to_zero": round(r.relative_to_zero, 4),
                                                  "dm_stat": round(r.dm_stat, 3), "p": round(r.p_value, 3)}
                         for r in tests[tests["loss"] == "squared"].itertuples()},
        "absolute_loss": {f"{r.model} {r.series}": {"relative_mae_to_zero": round(r.relative_to_zero, 4),
                                                   "p": round(r.p_value, 3)}
                          for r in tests[tests["loss"] == "absolute"].itertuples()},
        "fevd_xgh_from_szh_h10_pct": {r.method: round(r.share_pct, 2)
                                      for r in fevd[fevd["horizon"] == 10].itertuples()},
        "same_day_residual_correlation": round(correlation, 3),
    }
    (RESULTS / "robustness_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
