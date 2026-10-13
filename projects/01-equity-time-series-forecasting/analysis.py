"""Numerical source exported from Research_Analysis.ipynb."""
# %%
from pathlib import Path
import json
import inspect
from functools import partial
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
if 'result_object' in inspect.signature(adfuller).parameters:
    adfuller = partial(adfuller, result_object=False)
ORDERS = {'AR(2)': (2, 0, 0), 'MA(2)': (0, 0, 2), 'ARMA(2,1)': (2, 0, 1)}
OUT = Path('results')

def save_table(table, name):
    OUT.mkdir(exist_ok=True)
    table.to_csv(OUT / (name + '.csv'), encoding='utf-8-sig')
    display(table)

def save_figure(fig, name):
    OUT.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / (name + '.png'), dpi=170, bbox_inches='tight')
    plt.show()

def fit_model(series, order, trend='c'):
    fit = ARIMA(series.reset_index(drop=True), order=order, trend=trend).fit(method_kwargs={'maxiter': 1000})
    if not fit.mle_retvals['converged']:
        raise RuntimeError(f'Non-converged model: {order}, trend={trend}')
    assert np.isfinite(fit.params).all()
    return fit

def candidates(train):
    fits = {name: fit_model(train, order) for name, order in ORDERS.items()}
    rows = []
    for name, fit in fits.items():
        rows.append(dict(Model=name, Order=str(ORDERS[name]), AIC=fit.aic, BIC=fit.bic, Converged=fit.mle_retvals['converged'], **{f'param_{k}': float(v) for k, v in fit.params.items()}))
    table = pd.DataFrame(rows).set_index('Model').sort_values('BIC')
    return (fits, table, table.index[0])

def metrics(forecasts, actual):
    assert forecasts.index.equals(actual.index)
    assert np.isfinite(forecasts.to_numpy()).all()
    errors = forecasts.sub(actual, axis=0)
    return pd.DataFrame({'MAE': errors.abs().mean(), 'RMSE': np.sqrt(errors.pow(2).mean())})

def residual_check(train, fit, order):
    p, _, q = order
    burn = max(p, q, int(fit.loglikelihood_burn))
    resid = pd.Series(np.asarray(fit.resid)[burn:], index=train.index[burn:])
    lb = acorr_ljungbox(resid, lags=[10, 20], model_df=p + q, return_df=True)
    return (resid, lb)
import warnings
# Keep warning messages while omitting machine-specific filesystem locations.
warnings.formatwarning = lambda message, category, filename, lineno, line=None: (
    f"{category.__name__}: {message}\n")
data = pd.read_csv("GZMTp.csv", usecols=["Time", "close"], parse_dates=["Time"])
data = data.set_index("Time").sort_index()
assert not data.index.has_duplicates and not data.index.hasnans
assert np.isfinite(data.close).all() and (data.close > 0).all()
z = (100 * np.log(data.close)).rename("z")
r = z.diff().dropna().rename("r")
H = 20
train, test = r.iloc[:-H].copy(), r.iloc[-H:].copy()
z_train, z_test = z.iloc[:-H].copy(), z.iloc[-H:].copy()
assert (len(data), len(train), len(test)) == (2911, 2890, 20)
assert train.index[-1] < test.index[0]
display(pd.DataFrame([
    {"Sample": name, "N": len(series), "Start": str(series.index[0].date()),
     "End": str(series.index[-1].date())}
    for name, series in (("Prices", z), ("Training returns", train), ("Holdout returns", test))
]))

# %%
def stationarity_analysis(train, z_train):
    assert len(train) >= 500 and train.index.is_monotonic_increasing
    levels = z_train.loc[train.index]
    print(f'Training interval: {train.index[0].date()} to {train.index[-1].date()}; N={len(train)}')
    rows = []
    for name, series in [('100*log(price)', levels), ('Log return (%)', train)]:
        a = adfuller(series, regression='c', autolag='AIC')
        rows.append({'Series': name, 'Deterministic': 'c', 'ADF': a[0], 'p_value': a[1], 'ADF_lags': a[2], 'Effective_N': a[3]})
    table = pd.DataFrame(rows).set_index('Series')
    save_table(table, 'q1_adf')
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    axes[0].plot(levels.index, levels, lw=1, color='#163c61')
    axes[0].set(title='Training log-price level', ylabel='100 * ln(price)')
    axes[1].plot(train.index, train, lw=0.65, color='#167d8d')
    axes[1].set(title='Training daily log returns', ylabel='Log return (%)')
    save_figure(fig, 'q1_training_series')
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.5))
    plot_acf(train, lags=30, zero=False, ax=axes[0])
    plot_pacf(train, lags=30, zero=False, method='ywm', ax=axes[1])
    save_figure(fig, 'q1_return_correlograms')
    return table
stationarity_analysis(train, z_train);

# %%
def compare_models(train):
    fits, table, selected = candidates(train)
    save_table(table, 'q2_candidates')
    print('Selection criterion fixed before holdout evaluation: BIC')
    print('Selected:', selected)
    save_table(fits[selected].params.to_frame('Estimate'), 'q2_selected_parameters')
    return (table, selected)
compare_models(train);

# %%
def diagnose_residuals(train):
    fits, _, selected = candidates(train)
    resid, lb = residual_check(train, fits[selected], ORDERS[selected])
    save_table(lb, 'q3_ljung_box')
    fig, axes = plt.subplots(2, 1, figsize=(11, 6))
    axes[0].plot(resid.index, resid, lw=0.65, color='#163c61')
    axes[0].axhline(0, color='gray', lw=0.6)
    axes[0].set(title=f'{selected}: training residuals', ylabel='Percentage points')
    plot_acf(resid, lags=30, zero=False, ax=axes[1])
    save_figure(fig, 'q3_residual_diagnostics')
    return lb
diagnose_residuals(train);

# %%
def evaluate_returns(train, test, H):
    fits, _, selected = candidates(train)
    prediction = fits[selected].get_forecast(steps=H)
    forecasts = pd.DataFrame({selected: np.asarray(prediction.predicted_mean), 'Zero return': 0.0, 'Training mean': float(train.mean())}, index=test.index)
    table = metrics(forecasts, test)
    save_table(table, 'q4_return_metrics')
    save_table(forecasts.assign(Actual=test), 'q4_return_forecasts')
    band = np.asarray(prediction.conf_int())
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(test.index, test, 'o-', ms=3, label='Actual', color='#163c61')
    ax.plot(test.index, forecasts[selected], label=selected, color='#d56d36')
    ax.axhline(0, ls='--', color='gray', label='Zero return')
    ax.axhline(train.mean(), ls=':', color='#167d8d', label='Training mean')
    ax.fill_between(test.index, band[:, 0], band[:, 1], alpha=0.12, color='#d56d36', label='95% prediction interval')
    ax.set(title='Fixed-origin 20-observation return forecast', ylabel='Log return (%)')
    ax.legend(ncol=2)
    save_figure(fig, 'q4_return_forecast')
    gain = 100 * (1 - table.loc[selected, 'RMSE'] / table.loc['Zero return', 'RMSE'])
    return table
evaluate_returns(train, test, H);

# %%
def evaluate_log_prices(z_train, z_test, data, H):
    fits = {trend: fit_model(z_train, (1, 1, 1), trend) for trend in ('n', 't')}
    preds = {trend: fit.get_forecast(steps=H) for trend, fit in fits.items()}
    forecasts = pd.DataFrame({'ARIMA(1,1,1), no drift': np.asarray(preds['n'].predicted_mean), 'ARIMA(1,1,1), drift': np.asarray(preds['t'].predicted_mean), 'Last value': float(z_train.iloc[-1])}, index=z_test.index)
    table = metrics(forecasts, z_test).rename(columns={'MAE': 'MAE_z', 'RMSE': 'RMSE_z'})
    save_table(table, 'q5_log_price_metrics')
    save_table(pd.DataFrame({t: f.params for t, f in fits.items()}), 'q5_parameters')
    band_z = np.asarray(preds['t'].conf_int())
    med = np.exp(forecasts.iloc[:, 1] / 100)
    band = np.exp(band_z / 100)
    mean = np.exp(forecasts.iloc[:, 1] / 100 + np.asarray(preds['t'].var_pred_mean) / 20000)
    save_table(pd.DataFrame({'Actual': data.loc[z_test.index, 'close'], 'Median_drift': med, 'Gaussian_mean_drift': mean, 'Lower95': band[:, 0], 'Upper95': band[:, 1]}, index=z_test.index), 'q5_price_forecasts')
    fig, ax = plt.subplots(figsize=(11, 4))
    history = data.loc[:z_train.index[-1], 'close'].iloc[-40:]
    ax.plot(history.index, history, color='#163c61', label='Training history')
    ax.plot(z_test.index, data.loc[z_test.index, 'close'], color='#163c61', ls='--', label='Actual')
    ax.plot(z_test.index, med, color='#d56d36', label='Drift model: price median')
    ax.fill_between(z_test.index, band[:, 0], band[:, 1], color='#d56d36', alpha=0.15, label='95% prediction interval')
    ax.hlines(history.iloc[-1], z_test.index[0], z_test.index[-1], color='#167d8d', ls=':', label='Last price')
    ax.set(title='ARIMA log-price forecasts transformed to price', ylabel='Supplied price units')
    ax.legend(ncol=2)
    save_figure(fig, 'q5_price_forecast')
    return table
evaluate_log_prices(z_train, z_test, data, H);

# %%
fits, comparison, selected = candidates(train)
resid, lb = residual_check(train, fits[selected], ORDERS[selected])
arch = het_arch(resid, nlags=10, ddof=sum(ORDERS[selected]))
stability = []
for fraction in (.6, .8, 1.):
    prefix = train.iloc[:int(len(train) * fraction)]
    _, table, choice = candidates(prefix)
    stability.append({"Training_fraction": fraction, "N": len(prefix),
                      "End": str(prefix.index[-1].date()), "BIC_choice": choice,
                      "BIC": float(table.loc[choice, "BIC"])})
save_table(pd.DataFrame(stability), "training_selection_stability")
save_table(pd.DataFrame([{"ARCH_LM": arch[0], "p_value": arch[1], "Lags": 10}]),
           "arch_diagnostic")
rmetrics = pd.read_csv(OUT / "q4_return_metrics.csv", index_col=0)
pmetrics = pd.read_csv(OUT / "q5_log_price_metrics.csv", index_col=0)
summary = {
    "n_prices": len(data), "n_train_returns": len(train), "n_holdout": H,
    "start": str(data.index[0].date()), "end": str(data.index[-1].date()),
    "train_end": str(train.index[-1].date()), "test_start": str(test.index[0].date()),
    "selected": selected, "selected_bic": float(comparison.loc[selected, "BIC"]),
    "lb_p10": float(lb.iloc[0].lb_pvalue), "lb_p20": float(lb.iloc[1].lb_pvalue),
    "arch_p": float(arch[1]), "return_metrics": rmetrics.to_dict(orient="index"),
    "price_metrics": pmetrics.to_dict(orient="index")}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
assert selected == "MA(2)" and lb.iloc[1].lb_pvalue < .05
assert len(data) == len(train) + H + 1
assert not train.index.intersection(test.index).size
predictions = pd.read_csv(OUT / "q4_return_forecasts.csv", index_col=0, parse_dates=True)
assert predictions.index.equals(test.index)
assert np.allclose(predictions.Actual, test)
recomputed = metrics(predictions.drop(columns="Actual"), test)
assert np.allclose(recomputed, rmetrics)
price_predictions = pd.read_csv(OUT / "q5_price_forecasts.csv", index_col=0)
assert (price_predictions.Lower95 <= price_predictions.Median_drift).all()
assert (price_predictions.Median_drift <= price_predictions.Upper95).all()
assert (price_predictions.Gaussian_mean_drift >= price_predictions.Median_drift).all()
print("Verified: sample accounting, sealed holdout, forecast metrics and transformed intervals.")
