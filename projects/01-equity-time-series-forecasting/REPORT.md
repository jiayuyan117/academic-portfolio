# Equity Time-Series Forecasting
## ARMA / ARIMA Diagnostics and Benchmark Evaluation

**Coursework-based quantitative portfolio · Python / statsmodels · Reproducible analysis**

### Research question and main finding

Can parsimonious linear time-series models improve on simple forecasts of the supplied
Kweichow Moutai price series? This study distinguishes a model's fit, its residual adequacy,
and its performance on an untouched forecast window.

Within a pre-specified candidate set, training-only BIC selects **MA(2)**
(BIC **12274.6038**). Its fixed-origin 20-observation return RMSE is
**2.218777 percentage points**, versus **2.225323**
for a zero-return forecast: an RMSE improvement of **0.294%** on this window.
This is a descriptive comparison, not evidence of statistically significant or tradable outperformance.

### Data and audit trail

`GZMTp.csv` is the unmodified course-supplied dataset: **2,911 prices**
from **2010-01-04** through **2021-12-31**. The original notebook identifies the
series as Kweichow Moutai. An independently verified vendor, adjustment policy,
and complete dividend treatment were not supplied. Accordingly, the study describes
the supplied closing-price series, not a total-return investment.

The date field is `Time`; `close` is the supplied positive closing price. Dates are
sorted and checked for uniqueness, missing values and finite positive prices before
log transformation. No synthetic weekends or holidays are inserted.
The transformation is z = 100 ln(P); returns are first differences of z.
A return value of 1 means a 1% log return; forecast errors are measured in percentage points.

There are **2,890 training returns**, ending **2021-12-03**.
The final **20 observations**, starting **2021-12-06**, form
one fixed-origin holdout. The first test return correctly uses the last training
price as its lagged price. No random split or observed-test-value updating is used.

### Methods

1. Diagnose stationarity on the complete training interval with constant-only ADF
   regressions and AIC lag selection; inspect return ACF/PACF.
2. Estimate AR(2), MA(2) and ARMA(2,1) on exactly the same training returns.
   Report parameters, AIC, BIC and convergence. BIC is specified before test evaluation.
3. Refit the BIC-selected model independently. Inspect residual time plots and ACF,
   and use Ljung–Box at lags 10 and 20 with model_df = p + q.
4. Forecast the final 20 returns in one call, with fixed parameters. Compare the
   model with zero-return and training-mean baselines on aligned dates.
5. Fit ARIMA(1,1,1) to undifferenced z with and without drift. Compare with a
   last-value baseline on the same z scale, then transform forecasts to prices.
6. Synthesize the evidence, add ARCH diagnostics, and inspect selection on earlier
   60% and 80% training prefixes without exposing the final holdout to tuning.

The primary research notebook presents the complete numerical analysis in English. Original teaching material is retained separately for provenance.

### Out-of-sample results

Return forecast errors, in percentage points:

| Model | MAE | RMSE |
|---|---:|---:|
| MA(2) | 1.713472 | 2.218777 |
| Zero return | 1.724269 | 2.225323 |
| Training mean | 1.715787 | 2.219527 |

Log-price forecast errors, on the 100 ln(P) scale:

| Model | MAE_z | RMSE_z |
|---|---:|---:|
| ARIMA(1,1,1), no drift | 5.395387 | 5.983584 |
| ARIMA(1,1,1), drift | 4.531076 | 5.147919 |
| Last value | 5.429544 | 6.021481 |

The return and log-price RMSE values answer different questions and cannot be compared
directly. Both trend specifications are reported; neither is selected by repeatedly
optimizing against the final 20 observations.

![Return forecasts](results/q4_return_forecast.png)

### Diagnostics and interpretation

For MA(2), residual Ljung–Box p-values are **0.163988** at lag 10
and **0.0275137** at lag 20. At the 5% level, the decisions are respectively
**do not reject** and **reject** for the joint zero-autocorrelation null.
Thus the BIC winner is a provisional comparison model, not a fully adequate final
specification: the lag-20 check detects remaining linear dependence.
The tests do not establish independence,
normality or constant variance. The supplementary 10-lag ARCH-LM p-value is
**4.03846e-09**; the test rejects its no-ARCH null. Its usual asymptotic
interpretation is a diagnostic, not a guarantee that a specific volatility model is correct.

The earlier-prefix BIC results are in `results/training_selection_stability.csv`.
These describe sensitivity to the estimation period. BIC values from different
sample sizes are not ranked against one another.

`const` in the stationary ARIMA parameterization is the long-run location of returns;
the complete conditional mean also depends on lagged centered returns and innovations.
An MA term represents lagged innovations, not an arithmetic rolling average of prices.
For integrated models, `trend="t"` creates drift after differencing, while `trend="n"`
omits deterministic drift.

Under a conditional Gaussian log-price model, exp(predicted z / 100) is a **price
median**, not a mean. The mean additionally uses exp(forecast variance / 20000).
Transforming the two prediction-interval endpoints preserves their ordering and
produces an asymmetric price interval. These plug-in intervals do not fully account
for parameter uncertainty.

![Price forecasts](results/q5_price_forecast.png)

### Limitations and defensible next steps

One stock and one short holdout do not establish generalization. Market regimes,
corporate actions, price adjustment conventions and volatility clustering can affect
inference. The Gaussian, linear, constant-parameter models do not encode trading costs,
execution, economic identification or investment utility. A small RMSE advantage is
not automatically meaningful, and no strategy return is reported.

A stronger follow-up would pre-register expanding-window evaluation across several
non-overlapping forecast origins, use training-only nested model selection, verify
adjusted prices and dividends, and compare conditional-variance models and calibrated
prediction intervals. These are proposed extensions, not claimed completed experiments.

### Provenance and reproducibility

This analysis develops supplied econometrics coursework and retains its original datasets and teaching notebook in source_materials. AI assistance was used for code completion, analytical organization, verification, and English writing. The data were supplied with the course; upstream vendor and price-adjustment details were not independently established.

`Research_Analysis.ipynb` contains the executed analysis; `Research_Analysis.html` provides the same narrative, code, tables and figures for offline reading. `results/` contains regenerated numerical evidence. The reproduction runner verifies source hashes and compares recomputed tables with the established reference results before exporting the HTML and manifest.

Methods: statsmodels documentation for
[ARIMA](https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMA.html),
[ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html),
[Ljung–Box](https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.acorr_ljungbox.html),
and [ARCH-LM](https://www.statsmodels.org/stable/generated/statsmodels.stats.diagnostic.het_arch.html).
