# Shanghai–Hong Kong Market Linkages

## Research question and principal finding

Do lagged Shanghai and Hong Kong index returns provide useful incremental predictive information,
and how sensitive are apparent market linkages to model specification and shock identification?
This coursework-based study separates stationarity, prediction, Granger testing, and
variance decomposition rather than treating them as interchangeable evidence of causality.
VAR(7) marginally improves Shanghai holdout RMSE relative to zero returns but does not improve
Hong Kong RMSE. Neither Granger direction is significant at 5%. The shock contribution is
highly sensitive to Cholesky ordering, and the separate macro-financial cointegration exercise
does not establish a robust long-run equilibrium.

## Data and research design

| Dataset | Rows | Start | End |
| --- | --- | --- | --- |
| Prices | 2599 | 2011-01-04 | 2021-12-31 |
| VAR training | 2578 | 2011-01-05 | 2021-12-02 |
| VAR holdout | 20 | 2021-12-03 | 2021-12-31 |
| Cointegration levels | 1461 | 2016-01-04 | 2021-12-31 |

The files are course supplied. Their upstream vendor, collection process, redistribution
rights, adjustment conventions, and exact observation timestamps have not been independently
verified. The labels identify Shanghai Composite (SZH) and Hang Seng (XGH) according to the
starter. Dates are sorted and checked for uniqueness; values must be finite and index prices
strictly positive. No missing trading dates are inserted and no interpolation is performed.
The two datasets are not merged.

In VARSJ, returns are 100 × the first difference of natural-log prices. A value of 1 is a
1% log return; forecast errors are in percentage points. The final 20 common trading
observations form a fixed-origin holdout. All return-model lag selection, estimation, ADF,
Granger, IRF, and FEVD calculations use training data only. Forecasts are generated once
from the final seven training observations, without refitting or feeding in realized holdout
returns. The zero-return forecast is a prespecified benchmark, not a fitted model.

XZSJ is a separate in-sample teaching exercise. Its SZH is **already logged** and is not
logged again. SHIBOR is the **7-day rate according to the course**; EX is **yuan per USD**.
The course labels do not independently verify a market-data vendor or daily fixing convention.

## Core empirical results

1. With constant-only ADF, maxlag=12, AIC autolag, training SZH log-price p =
   **0.4050725522**, and return p = **1.061710611e-29**.
   Log prices fail to reject a unit root, whereas returns reject it. This supports using
   returns in a stable VAR; it does not establish independent, Gaussian, or homoskedastic returns.
2. VAR(7) predicts **2021-12-03** log returns of **0.10606119%**
   for SZH and **0.03782405%** for XGH. These are conditional means,
   not confidence bounds or price forecasts.
3. The Johansen trace test with det_order=0, q=2, and 5% significance selects rank
   **2**. The first nonrejection is row **3**
   (null r ≤ 2): trace **2.447203** versus critical
   value **3.841500**. q counts lagged differences and corresponds to
   a level VAR order of q+1.
4. The SZH → XGH system F test gives F = **1.27582348**, p =
   **0.2579153178**. The seven lagged SZH coefficients in the XGH equation are not
   jointly significant at 5%. Failure to reject is not proof of no linkage.
5. In the explicit order [SZH, XGH], `fevd(10).decomp[1, 9, 0] * 100` is
   **32.42815216%**: the contribution of the identified SZH shock to
   XGH's ten-step forecast-error variance. This is neither a share of observed returns
   nor a structural causal effect.

## Forecast evaluation

| Model | Series | RMSE | MAE |
| --- | --- | --- | --- |
| VAR(7) | SZH | 0.71983995 | 0.64486193 |
| VAR(7) | XGH | 1.1110885 | 0.85704404 |
| Zero return | SZH | 0.72113516 | 0.64353441 |
| Zero return | XGH | 1.1039324 | 0.85339218 |

Both RMSE and MAE are in percentage points and use the same 20 held-out observations.
VAR(7) has slightly higher MAE than zero returns for both markets, so its small Shanghai
RMSE advantage does not extend to that market's absolute-error metric.
The mixed performance offers no broad evidence that a seven-lag bivariate model outperforms
the parsimonious benchmark. This is a small single holdout, not repeated external validation.
No claim of statistically significant forecast superiority, profitable trading, or performance
after costs is made. The holdout is not reused to tune lag length.

## Training-only lag diagnostics

Selected orders: **{"aic": 7, "bic": 0, "hqic": 0, "fpe": 7}**. Information criteria are reported
on the common truncated sample used by `select_order(12)`; separate candidate fits use their
own available training observations. VAR(0) is constant-only and has no dynamic roots.

| Lag | AIC_common | BIC_common | Stable | White12_p | White_test_horizon |
| --- | --- | --- | --- | --- | --- |
| 0 | 0.57403074 | 0.57859044 | True | 1.4526753e-05 | 12 |
| 1 | 0.57102357 | 0.58470269 | True | 0.00010732509 | 12 |
| 2 | 0.57024212 | 0.59304065 | True | 0.0021261439 | 12 |
| 3 | 0.57111338 | 0.60303132 | True | 0.0018824832 | 12 |
| 4 | 0.57059886 | 0.61163622 | True | 0.0064582123 | 12 |
| 5 | 0.56907246 | 0.61922923 | True | 0.033103036 | 12 |
| 6 | 0.56582806 | 0.62510424 | True | 0.25162343 | 12 |
| 7 | 0.56408524 | 0.63248084 | True | 0.77091671 | 12 |
| 8 | 0.5651582 | 0.64267321 | True | 0.78397217 | 12 |
| 9 | 0.56707027 | 0.65370469 | True | 0.75123868 | 12 |
| 10 | 0.56864391 | 0.66439775 | True | 0.74983165 | 12 |
| 11 | 0.57121008 | 0.67608334 | True | 0.46189253 | 12 |
| 12 | 0.57368583 | 0.68767849 | True | 0.022296974 | 24 |

The column White12_p uses a 12-lag Portmanteau test except for VAR(12), where 24 is required
because the test horizon must exceed the fitted order. The horizon is explicit in the table.
VAR(7)'s nonrejection of residual autocorrelation does not prove full model adequacy:
conditional heteroskedasticity, heavy tails, breaks, and nonlinear effects remain possible.
Lag diagnostics assess specification sensitivity using training data only.

## Granger inference and identification

| Direction | VAR_lag | F | p_value | Reject_5pct |
| --- | --- | --- | --- | --- |
| SZH -> XGH | 7 | 1.2758235 | 0.25791532 | False |
| XGH -> SZH | 7 | 1.9297855 | 0.060880201 | False |

Granger tests ask whether lagged information improves the specified conditional-mean equation,
not whether intervention in one market causes changes in another. Omitted global factors,
trading-hour differences, and specification error can affect interpretation.

| Order | Response | Shock | Horizon | Share_pct |
| --- | --- | --- | --- | --- |
| SZH, XGH | XGH | SZH | 1 | 32.288951 |
| SZH, XGH | XGH | SZH | 5 | 32.407051 |
| SZH, XGH | XGH | SZH | 10 | 32.428152 |
| SZH, XGH | SZH | XGH | 1 | 0 |
| SZH, XGH | SZH | XGH | 5 | 0.42069601 |
| SZH, XGH | SZH | XGH | 10 | 0.55351682 |
| XGH, SZH | XGH | SZH | 1 | 0 |
| XGH, SZH | XGH | SZH | 5 | 0.29681449 |
| XGH, SZH | XGH | SZH | 10 | 0.35097091 |
| XGH, SZH | SZH | XGH | 1 | 32.288951 |
| XGH, SZH | SZH | XGH | 5 | 32.321964 |
| XGH, SZH | SZH | XGH | 10 | 32.116117 |

For SZH shocks explaining XGH at ten steps, changing [SZH, XGH] to [XGH, SZH] changes the
share from **32.428152% to 0.350971%**. Reordering changes the
contemporaneous zero restrictions and the definition of orthogonal shocks. It does not
represent an economic change in the underlying sample. Responses and shocks are remapped
by variable name when comparing orders. IRF bands in the research notebook are asymptotic
pointwise 95% intervals, not simultaneous path bands.

## Cointegration sensitivity and why the conclusion is limited

Constant-only ADF checks use maxlag=11 and AIC autolag for XZSJ:

| Transform | Series | ADF | p_value | Lags | N_obs |
| --- | --- | --- | --- | --- | --- |
| Level | SZH | -1.7146715 | 0.42356959 | 6 | 1454 |
| Level | SHIBOR | -2.0661528 | 0.25834066 | 11 | 1449 |
| Level | EX | -1.0727374 | 0.72582057 | 0 | 1460 |
| First difference | SZH | -17.636635 | 3.7761063e-30 | 5 | 1454 |
| First difference | SHIBOR | -16.339479 | 3.0057582e-29 | 11 | 1448 |
| First difference | EX | -38.233456 | 0 | 0 | 1459 |

All three level series fail to reject a unit root in this constant-only ADF specification;
all first differences reject. This is consistent with an I(1) system, not proof of integration
order, and the baseline tests do not establish mixed integration. If other justified
specifications indicate a stationary component, that component can contribute to a positive
system rank without establishing a long-run equilibrium among three I(1) variables.
Unit-root tests have limited power and depend on deterministic terms and breaks.

The bivariate SZH/SHIBOR Engle–Granger test gives p = **0.61832824**.
Its variable set differs from the trivariate Johansen system, so their outcomes are not
direct contradictions.

| q | Levels_VAR_order | Rank | White12_p | Deterministic |
| --- | --- | --- | --- | --- |
| 1 | 2 | 2 | 2.0603958e-07 | co |
| 2 | 3 | 2 | 3.2938938e-07 | co |
| 3 | 4 | 2 | 4.6942909e-07 | co |

Johansen uses det_order=0 and the 5% trace rule; VECM estimates use an unrestricted outside
constant (`co`), preserving the course demonstration. The two APIs' deterministic encodings
are not interchangeable; broader deterministic-specification robustness has not been
established. Rank remains 2 across q=1, 2, and 3, but all fitted VECMs reject residual whiteness.
This limited rank stability does not resolve the residual misspecification.
Consequently the cointegration output remains a conditional teaching result,
not a robust investment, policy, or equilibrium claim. The analysis does not deploy a VECM
forecast or select the return VAR using XZSJ.

## Methods, provenance and reproducibility

This analysis develops supplied econometrics coursework and retains its original datasets and teaching notebook in source_materials. AI assistance was used for code completion, analytical organization, verification, and English writing. The data were supplied with the course; upstream vendor and price-adjustment details were not independently established.

The English research notebook is fully executed. The runner verifies source hashes, recomputes the analysis and compares numerical evidence with the established reference results before exporting self-contained HTML and a file manifest. Exact dependency versions and the Python environment are recorded.

Future work could use preregistered rolling-origin evaluation on additional data, robust
inference for financial residuals, structural-break tests, and economically justified shock
identification. These are proposed next steps, not completed analyses.


## Visual evidence

![Fixed-origin forecasts](results/holdout_forecasts.png)

![FEVD ordering sensitivity](results/fevd_order_sensitivity.png)

Methods: statsmodels documentation for [VAR](https://www.statsmodels.org/stable/vector_ar.html), [VECM](https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.vecm.VECM.html), [Johansen rank selection](https://www.statsmodels.org/stable/generated/statsmodels.tsa.vector_ar.vecm.select_coint_rank.html), and [Engle–Granger](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.coint.html).
