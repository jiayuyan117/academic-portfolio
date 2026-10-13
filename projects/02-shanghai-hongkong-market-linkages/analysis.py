"""Numerical source exported from Research_Analysis.ipynb."""
# %%
import json
import warnings
warnings.formatwarning = lambda message, category, filename, lineno, line=None: (
    f"{category.__name__}: {message}\n")
from pathlib import Path
from inspect import signature
from functools import partial
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller, coint
from statsmodels.tsa.vector_ar.vecm import select_coint_rank, coint_johansen, VECM
from numpy.exceptions import ComplexWarning
from IPython.display import display, Markdown
if "result_object" in signature(adfuller).parameters:
    adfuller = partial(adfuller, result_object=False)
DATA_DIR = Path(".")
output = Path("results")
output.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})

raw = pd.read_csv(DATA_DIR / "VARSJ.csv", encoding="gbk")
prices = raw[["SZH", "XGH"]].apply(pd.to_numeric)
prices.index = pd.to_datetime(raw.iloc[:, 0])
prices.index.name = "Date"
prices = prices.sort_index()

levels = pd.read_csv(DATA_DIR / "XZSJ.csv", parse_dates=["Time"])
levels = levels.set_index("Time")[["SZH", "SHIBOR", "EX"]].apply(pd.to_numeric).sort_index()
levels.index.name = "Date"
for name, frame in (("Prices", prices), ("Levels", levels)):
    if frame.index.hasnans or frame.index.has_duplicates:
        raise ValueError(f"{name}: dates must be valid and unique.")
    if not np.isfinite(frame.to_numpy()).all():
        raise ValueError(f"{name}: all observations must be finite.")
if (prices <= 0).any().any():
    raise ValueError("Prices must be positive before taking logarithms.")

log_prices = np.log(prices)
returns = 100 * log_prices.diff().dropna()
H = 20
train, test = returns.iloc[:-H].copy(), returns.iloc[-H:].copy()
if len(train) < 500:
    raise ValueError("At least 500 training returns are required.")

sample_rows = []
for name, frame in (("Prices", prices), ("VAR training", train),
                    ("VAR holdout", test), ("Cointegration levels", levels)):
    sample_rows.append({"Dataset": name, "Rows": len(frame),
                        "Start": str(frame.index[0].date()), "End": str(frame.index[-1].date())})
display(pd.DataFrame(sample_rows).set_index("Dataset"))
display(prices.head(3))
assert (len(prices), len(train), len(test), len(levels)) == (2599, 2578, 20, 1461)
assert train.index[-1] < test.index[0]
assert not train.index.intersection(test.index).size

# %%
fig, axes = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
log_prices.loc[:train.index[-1]].plot(ax=axes[0], lw=0.9)
axes[0].set(title="Training sample: log prices", ylabel="Log index")
train.plot(ax=axes[1], lw=0.65)
axes[1].axhline(0, color="gray", lw=0.7)
axes[1].set(title="Training sample: log returns", ylabel="Daily log return (%)", xlabel="Date")
fig.tight_layout()
fig.savefig(output / "training_history.png", dpi=170)
plt.show()
def adf_table(frame, regression="c", maxlag=12):
    rows = []
    for name in frame.columns:
        result = adfuller(frame[name].dropna(), regression=regression,
                          maxlag=maxlag, autolag="AIC")
        rows.append({"Series": name, "Deterministic": regression,
                     "ADF": result[0], "p_value": result[1],
                     "Lags": result[2], "N_obs": result[3]})
    return pd.DataFrame(rows).set_index("Series")

z_train = log_prices.loc[:train.index[-1]]
adf_prices = adf_table(z_train)
adf_returns = adf_table(train)
display(pd.concat({"Log price": adf_prices, "Log return": adf_returns},
                  names=["Transform", "Series"]))
pd.concat({"Log price": adf_prices, "Log return": adf_returns}).to_csv(
    output / "return_system_adf.csv")

# %%
model = VAR(train.reset_index(drop=True))
selection = model.select_order(maxlags=12)
ic_table = pd.DataFrame(selection.ics).rename_axis("Lag")
display(ic_table)
print("Selected lags:", {name: int(value) for name, value in selection.selected_orders.items()})


fits = {p: model.fit(p, trend="c") for p in (1, 7)}
diagnostics = []
for p, fit in fits.items():
    white = fit.test_whiteness(nlags=12)
    diagnostics.append({"Lag": p, "AIC_common": ic_table.loc[p, "aic"],
                        "BIC_common": ic_table.loc[p, "bic"],
                        "Stable": fit.is_stable(), "White_p": white.pvalue})
display(pd.DataFrame(diagnostics).set_index("Lag"))

fit_var = fits[7]
display(fit_var.params.head(5))
lag_rows = []
for p in range(13):
    candidate = VAR(train.reset_index(drop=True)).fit(p, trend='c')
    lag_rows.append({'Lag': p, 'AIC_common': float(ic_table.loc[p, 'aic']), 'BIC_common': float(ic_table.loc[p, 'bic']), 'Stable': bool(candidate.is_stable()) if p else True, 'White12_p': float(candidate.test_whiteness(nlags=12 if p < 12 else 24).pvalue), 'White_test_horizon': 12 if p < 12 else 24})
lag_diagnostics = pd.DataFrame(lag_rows)
display(lag_diagnostics)
fit_var.params.to_csv(output / "var_parameters.csv")

# %%
last_p = train.to_numpy()[-fit_var.k_ar:]
forecast = pd.DataFrame(fit_var.forecast(last_p, steps=H),
                        index=test.index, columns=test.columns)
metrics = []
for label, prediction in (("VAR(7)", forecast),
                          ("Zero return", pd.DataFrame(0.0, index=test.index, columns=test.columns))):
    errors = prediction - test
    for name in test.columns:
        metrics.append({"Model": label, "Series": name,
                        "MAE": errors[name].abs().mean(),
                        "RMSE": np.sqrt(errors[name].pow(2).mean())})
forecast_metrics = pd.DataFrame(metrics).set_index(["Model", "Series"])
display(forecast_metrics)

fig, axes = plt.subplots(2, 1, figsize=(10, 4.8), sharex=True)
for ax, name in zip(axes, test.columns):
    ax.plot(test.index, test[name], "o-", ms=3, label="Actual")
    ax.plot(forecast.index, forecast[name], color="#E07A2D", label="VAR(7)")
    ax.axhline(0, color="gray", ls="--", label="Zero return")
    ax.set(title=name, ylabel="Log return (%)")
    ax.legend(loc="best", ncol=3)
fig.tight_layout()
fig.savefig(output / "holdout_forecasts.png", dpi=170)
plt.show()
display(forecast.head(1))
assert forecast.index.equals(test.index) and forecast.shape == (20, 2)
assert np.isfinite(forecast.to_numpy()).all()
evaluation = test.add_prefix("actual_").join(forecast.add_prefix("forecast_"))
evaluation["zero_SZH"] = 0.0
evaluation["zero_XGH"] = 0.0

# %%
granger_rows = []
for cause, response in (("SZH", "XGH"), ("XGH", "SZH")):
    result = fit_var.test_causality(caused=response, causing=[cause], kind="f")
    granger_rows.append({"Direction": f"{cause} -> {response}",
                         "VAR_lag": fit_var.k_ar, "F": result.test_statistic,
                         "p_value": result.pvalue, "Reject_5pct": result.pvalue < 0.05})
display(pd.DataFrame(granger_rows).set_index("Direction"))
irf = fit_var.irf(periods=10)
orth = irf.orth_irfs
se = irf.stderr(orth=True)
horizons = np.arange(11)

fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
for ax, (response, shock) in zip(axes, ((1, 0), (0, 1))):
    values = orth[:, response, shock]
    error = 1.96 * se[:, response, shock]
    ax.plot(horizons, values, color="#003366", label="Response")
    ax.fill_between(horizons, values - error, values + error,
                    color="#003366", alpha=0.15, label="95% pointwise CI")
    ax.axhline(0, color="gray", lw=0.8)
    ax.set(title=f"{fit_var.names[shock]} shock -> {fit_var.names[response]}",
           xlabel="Horizon (trading observations)", ylabel="Response (percentage points)")
    ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(output / "impulse_responses.png", dpi=170)
plt.show()

# %%
order_rows = []
for order in (['SZH', 'XGH'], ['XGH', 'SZH']):
    ordered_fit = VAR(train[order].reset_index(drop=True)).fit(7, trend='c')
    decomposition = ordered_fit.fevd(10).decomp
    assert np.allclose(decomposition.sum(axis=2), 1.0)
    for response, shock in (('XGH', 'SZH'), ('SZH', 'XGH')):
        for horizon in (1, 5, 10):
            order_rows.append({'Order': ', '.join(order), 'Response': response, 'Shock': shock, 'Horizon': horizon, 'Share_pct': float(decomposition[order.index(response), horizon - 1, order.index(shock)] * 100)})
order_sensitivity = pd.DataFrame(order_rows)
display(order_sensitivity)
fig, ax = plt.subplots(figsize=(8, 4))
for order_label, group in order_sensitivity.query("Response == 'XGH' and Shock == 'SZH'").groupby('Order'):
    ax.plot(group.Horizon, group.Share_pct, 'o-', label=order_label)
ax.set(xlabel='Forecast horizon (trading observations)', ylabel='Share of XGH forecast error variance (%)', title='SZH shock contribution depends on identification')
ax.legend(title='Cholesky order')
fig.tight_layout()
fig.savefig(output / 'fevd_order_sensitivity.png', dpi=180)
plt.show()

# %%
display(pd.concat({
    "Level": adf_table(levels, maxlag=11),
    "First difference": adf_table(levels.diff().dropna(), maxlag=11),
}, names=["Transform", "Series"]))

eg_stat, eg_p, eg_critical = coint(
    levels["SZH"], levels["SHIBOR"], trend="c",
    maxlag=11, autolag="AIC", return_results=False
)
display(pd.DataFrame([{"Pair": "SZH, SHIBOR", "Statistic": eg_stat,
                       "p_value": eg_p, "Critical_5pct": eg_critical[1]}]))
def johansen_rank(frame, k_ar_diff):
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='Casting complex values to real discards the imaginary part', category=ComplexWarning, module='statsmodels\\.tsa\\.vector_ar\\.vecm')
        eigenvalues = coint_johansen(frame, det_order=0, k_ar_diff=k_ar_diff).eig
        if not np.isfinite(eigenvalues).all() or np.iscomplexobj(np.real_if_close(eigenvalues)):
            raise ValueError('Johansen eigenvalues must be finite and real. Check the data and lags.')
        return select_coint_rank(frame, det_order=0, k_ar_diff=k_ar_diff, method='trace', signif=0.05)
rank_rows = []
trace_rows = []
for diff_lag in (1, 2, 3):
    rank_check = johansen_rank(levels, k_ar_diff=diff_lag)
    selected_rank = int(rank_check.rank)
    for row, (stat, critical) in enumerate(zip(rank_check.test_stats, rank_check.crit_vals)):
        trace_rows.append({'q': diff_lag, 'Null_rank_at_most': row, 'Trace': float(stat), 'Critical_5pct': float(critical), 'Reject': bool(stat > critical)})
    sensitivity_fit = VECM(levels.reset_index(drop=True), k_ar_diff=diff_lag, coint_rank=selected_rank, deterministic='co').fit()
    rank_rows.append({'q': diff_lag, 'Levels_VAR_order': diff_lag + 1, 'Rank': selected_rank, 'White12_p': float(sensitivity_fit.test_whiteness(nlags=12).pvalue), 'Deterministic': 'co'})
rank_sensitivity = pd.DataFrame(rank_rows)
level_adf = pd.concat({'Level': adf_table(levels, maxlag=11), 'First difference': adf_table(levels.diff().dropna(), maxlag=11)}, names=['Transform', 'Series'])
display(level_adf)
display(rank_sensitivity)
display(pd.DataFrame(trace_rows))
for name, frame in (('forecast_metrics', forecast_metrics), ('holdout_predictions', evaluation), ('lag_diagnostics', lag_diagnostics), ('fevd_order_sensitivity', order_sensitivity), ('johansen_sensitivity', rank_sensitivity), ('johansen_trace', pd.DataFrame(trace_rows)), ('cointegration_adf', level_adf), ('granger', pd.DataFrame(granger_rows))):
    frame.to_csv(output / f'{name}.csv', index=True, encoding='utf-8')

# %%
rank_check = johansen_rank(levels, k_ar_diff=2)
assert rank_sensitivity.Rank.tolist() == [2, 2, 2]
assert (rank_sensitivity.White12_p < .05).all()
assert fit_var.is_stable()
for row in forecast_metrics.reset_index().itertuples():
    prediction = forecast[row.Series] if row.Model == "VAR(7)" else 0.0
    errors = prediction - test[row.Series]
    assert np.isclose(row.RMSE, np.sqrt(np.mean(errors**2)))
    assert np.isclose(row.MAE, np.mean(np.abs(errors)))
summary = {
    "samples": sample_rows,
    "selected_orders": {k: int(v) for k, v in selection.selected_orders.items()},
    "first_forecast": {"date": str(test.index[0].date()), **forecast.iloc[0].to_dict()},
    "forecast_metrics": forecast_metrics.reset_index().to_dict(orient="records"),
    "granger": pd.DataFrame(granger_rows).to_dict(orient="records"),
    "fevd_sensitivity": order_rows, "johansen": rank_rows,
    "johansen_q2": {"rank": int(rank_check.rank),
                    "trace_first_nonrejection": float(rank_check.test_stats[rank_check.rank]),
                    "critical": float(rank_check.crit_vals[rank_check.rank])},
    "eg": {"statistic": float(eg_stat), "p": float(eg_p)}}
(output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("Verified: chronological holdout, aligned metrics, stable VAR and rank sensitivity.")
