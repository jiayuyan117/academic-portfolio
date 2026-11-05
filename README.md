# Jiayu Yan — Data Analytics Portfolio

**Author: 闫佳玉 / Jiayu Yan**

B.Mgmt. in **Big Data Management and Applications**, Guangdong University of Technology
· Applying for MS programmes in Business Analytics / Data Science (US · Singapore · Hong Kong)

**[→ Browse the portfolio site](https://jiayuyan117.github.io/academic-portfolio/)**

[中文网页](https://jiayuyan117.github.io/academic-portfolio/index.zh-CN.html)

---

## Research focus

I study when a model adds enough value to inform a decision. My projects compare
pollution alerts, market forecasts and job-posting features with simple alternatives,
and examine the data quality behind those comparisons.

This portfolio brings together eight projects developed through undergraduate
coursework and independent study: statistical and NLP research, interactive
visualisation, and a Java engineering project. Reports link to methods, sources
and saved evidence so readers can inspect both the findings and their limits.

Every predictive claim is scored on data held out from fitting and tuning.
Negative findings and methodological corrections are reported alongside the
claims they qualify. Failure to reject a null hypothesis is not proof of no
effect, and an observational association is not an intervention effect.

CI records numerical verification and analysis rebuilds for projects **01–05**.
The two econometrics projects check input SHA-256 hashes and **586 numerical
values** against stored references at `rtol=1e-6`. Project **06** adds an exactly
reconstructed source cohort and prediction-level metric verification.

## A 30-second reading guide

**Business Analytics route: 05 → 03 → 06 → 04.**
**Data Science route: 06 → 07 → 02 → 05.**
Start with one brief below; use the linked predictions and checks for a closer look.

| Selection | Why read it | Evidence entry |
| --- | --- | --- |
| [05 · Next-day alert decision](projects/05-beijing-air-quality-seaborn/FIRST_READ.html) | Cost-based alert rule tested once on 2014 after tuning on 2013; cost per day 0.126 below persistence, 95% CI [0.066, 0.195] | [Test-day predictions](projects/05-beijing-air-quality-seaborn/outputs/08_alert_test_predictions.csv) |
| [03 · Market sizing in advance](projects/03-china-nev-industry-analytics/FIRST_READ.html) | Rolling-origin backtest: every sizing model under-forecast; fitted S-curve ceiling moved 6% → 100% → 54% | [Backtest forecasts](projects/03-china-nev-industry-analytics/results/backtest_forecasts.csv) |
| [06 · NLP evaluation](projects/06-nlp-job-postings/report.html) | Employer-disjoint feature comparison; separate extraction evaluation | [Saved predictions and checks](projects/06-nlp-job-postings/README.md#what-is-independently-checkable) |
| [07 · Temporal ML](projects/07-market-direction/report.html) | Baseline-inclusive selection and uncertainty across later test blocks | [Verification](projects/07-market-direction/verify.py) |
| [02 · Forecast tests and identification](projects/02-shanghai-hongkong-market-linkages/FIRST_READ.html) | 500-origin Diebold–Mariano tests; order-free variance decomposition | [Robustness summary](projects/02-shanghai-hongkong-market-linkages/results/robustness_summary.json) |

**Supplements:** 04 (demand-data reconciliation and interactive charts),
01 (forecast diagnostics) and 08 (persistence, revision-checked pagination and HTTP tests).

<details>
<summary>Full project directory</summary>

| Project | Focus |
| --- | --- |
| [01 · Equity forecasting](projects/01-equity-time-series-forecasting/) | Benchmarks and residual diagnostics |
| [02 · Market linkages](projects/02-shanghai-hongkong-market-linkages/) | Rolling forecast tests and identification sensitivity |
| [03 · NEV transition](projects/03-china-nev-industry-analytics/) | Market-sizing backtest, denominators and source traceability |
| [04 · Bike sharing](projects/04-bike-sharing-interactive-visualization/) | Date reconciliation and interactive charts |
| [05 · Beijing PM2.5](projects/05-beijing-air-quality-seaborn/) | Missing-data audit and a cost-based next-day alert test |
| [06 · Does the Skill Signal Help?](projects/06-nlp-job-postings/README.md) | NLP evaluation, negative findings and reproducibility |
| [07 · When the Baseline Wins](projects/07-market-direction/report.html) | Purged temporal ML, baseline-inclusive selection and block-bootstrap uncertainty |
| [08 · Product catalog](projects/08-product-catalog/PROJECT.html) | Persistent records, stale-edit rejection and HTTP boundary tests |

</details>

### Business Analytics: from question to decision

| Project | Decision question and method | Evidence and action boundary |
| --- | --- | --- |
| [05 · Operational alert](projects/05-beijing-air-quality-seaborn/README.md) | Should a team alert tonight for tomorrow? Fit 2010–2012, tune a cost-based threshold on 2013, test once on 2014. | Model catches 174 of 181 alert days with 103 false alarms versus 168 for persistence. The 3:1 cost ratio is an assumption to confirm with the team that bears it. |
| [03 · Market sizing](projects/03-china-nev-industry-analytics/README.md) | Could the NEV share have been forecast? Refit each sizing model at every origin from 2020 to 2024. | All models under-forecast; the S-curve ceiling is not identified until after the inflection. Present sizing as ceiling scenarios, domestic (50.8%) and export bases separate. |
| [06 · Job-information quality](projects/06-nlp-job-postings/README.md) | Compare text and skill features on held-out employers; evaluate extraction separately. | Fusion Macro-F1 of 0.7348 versus 0.7406 for text does not justify the added features under this study's criterion. Operational value remains unmeasured. |
| [04 · Demand data](projects/04-bike-sharing-interactive-visualization/README.md) | Reconcile hourly and daily demand files before planning. | The naive join matches 0 of 731 days; parsed correctly the files agree exactly. |

Read each project as **question → data and method → result → decision implication
→ limitation**. Recommendations are academic interpretations, not deployed
interventions or measured ROI.

## Supporting project briefs and complete evidence

<details>
<summary>Expand all 8 briefs (start with the selected studies above)</summary>

### 01 · [Equity Time-Series Forecasting](projects/01-equity-time-series-forecasting/)
`statsmodels` · `ARMA/ARIMA` · `fixed-origin holdout` · `252 values verified per run`

Training-only BIC selects MA(2); it beats a zero-return forecast by **0.29% of
RMSE** on an untouched 20-day holdout — while Ljung-Box **rejects** residual
adequacy at lag 20 and ARCH-LM rejects constant variance (*p* = 4e-09).
The small gain on one window does not establish practical forecasting value.

**Decision:** retain the benchmark until time-based validation across more
windows and transaction-cost analysis establish a practically useful gain.

### 02 · [Shanghai–Hong Kong Market Linkages](projects/02-shanghai-hongkong-market-linkages/)
`VAR / VECM` · `Johansen` · `generalized FEVD` · `Diebold–Mariano` · `334 values verified per run`

A Shanghai shock appears to explain **32.4%** of Hong Kong's 10-step
forecast-error variance — until the Cholesky ordering is reversed, when the same
quantity becomes **0.35%**. The order-free generalized FEVD gives **24.6%**, and
the same-day residual correlation (0.568² ≈ 32.3%) accounts for almost all of
it, suggesting that this decomposition mainly reflects same-day co-movement.
It does not establish a causal spillover. Across **500
rolling one-step forecasts**, VAR(7) is significantly worse than a zero-return
forecast in both markets (Diebold–Mariano *p* = 0.042 and 0.012).

**Decision:** investigate the co-movement for contemporaneous risk analysis;
these results do not validate a hedge or a next-day directional signal.

### 03 · [China's NEV Transition, 2015–2025](projects/03-china-nev-industry-analytics/)
`pandas` · `scipy` · `7 compiled tables` · `16 figures, bilingual` · `rolling-origin backtest`

In 2025, NEVs accounted for **47.9%** of CAAM's all-vehicle sales **including
exports**, **50.8%** on a domestic basis. A backtest refits naive, linear-trend
and S-curve sizing models at every origin from 2020 to 2024 using only data
available then. Every model **under-forecast on average** (−3.1 to −20.1 pp),
and the fitted S-curve ceiling moved from **6% to 100% to 54%** as data arrived.
The [source audit](docs/NEV_SOURCE_AUDIT.md) corrects a 2021 PHEV input and
documents the **2025 charging-statistics break**. The carbon calculation is an
illustrative scenario, not measured emissions savings.

**Decision:** present market size as ceiling scenarios re-fitted each year.
Charging investment additionally needs location, utilization and power data.

### 04 · [Bike-Sharing Interactive Visualisation](projects/04-bike-sharing-interactive-visualization/)
`Plotly` · `offline interactive charts` · `17,379 observations` · [live charts](https://jiayuyan117.github.io/academic-portfolio/projects/04-bike-sharing-interactive-visualization/charts/01_sunburst.html)

The two files in the UCI Bike Sharing Dataset store dates as `2011/1/1` and
`2011-01-01`, so the obvious join between them matches **0 of 731 days** — and
any reconciliation check built on it passes while comparing nothing to nothing.
Parsed properly, the files do agree exactly. Four offline-capable interactive
figures each label what every visual channel encodes.

**Decision:** reconcile totals before demand planning. Station-level fleet
rebalancing additionally needs local availability and service-cost data.

### 05 · [Beijing PM2.5: From Missing Data to a Next-Day Alert](projects/05-beijing-air-quality-seaborn/)
`Seaborn` · `statsmodels` · `43,824 hourly observations` · `8 figures` · `block bootstrap`

The audit comes first: 1,341 of the 2,067 missing hours sit inside gaps longer
than a day (the longest is 155 hours), so nothing is interpolated and every
headline uses observed values only. Cumulated wind speed has Spearman ρ =
**−0.360** with PM2.5, and median PM2.5 is **6.3× higher** in the calmest decile.

Those associations become a testable decision. An alert day has a daily mean
above 75 µg/m³ with at least 20 valid hours. A logistic model on same-day data
is fitted on 2010–2012, its cost-minimizing threshold is chosen on 2013 (a missed
alert day assumed to cost three false alarms), and it is tested once on 2014.
It catches **174 of 181** alert days with **103 false alarms**; the best
persistence rule alerts every day and raises 168. Cost per day falls by
**0.126, 95% block-bootstrap CI [0.066, 0.195]**, and the ranking holds for
cost ratios from 1:1 to 10:1. Observed next-day weather, an upper bound for a
perfect forecast, removes another 55 false alarms.

**Decision:** pilot the model in place of persistence, confirm the cost ratio,
and integrate a weather-forecast feed before deployment.

### 06 · [Does the Skill Signal Help?](projects/06-nlp-job-postings/README.md)
`Job-posting NLP` · `SkillSpan` · `21,663 postings` · `20 classes` · `employer-disjoint split`

Adding SkillSpan Skill + Knowledge lexicon features does not clear the study's
improvement criterion: test Macro-F1 is **0.7406** for text, **0.5003** for the
lexicon and **0.7348** for equal-weight fusion. Classification and exact-span
extraction answer different questions and are evaluated separately.

**Evidence status:** the 21,663-posting cohort, 20 classes and employer-disjoint
split were checked against fixed public sources. Full classification, extraction
and TF-IDF/CNN/frozen-MiniLM comparison runs retain predictions for independent
metric verification. Historical paper values are labelled separately where they
differ from this rerun. The `+0.02` absolute Macro-F1 gain is a recorded study
threshold; no independently timestamped preregistration was supplied.

**Decision relevance:** retain the text baseline for broad-category routing.
Evaluate extracted requirements directly before using them in a skills profile.
[Read the research brief](https://jiayuyan117.github.io/academic-portfolio/projects/06-nlp-job-postings/report.html).

### 07 · [When the Baseline Wins](projects/07-market-direction/report.html)

A research extension of a course machine-learning lab, rebuilt on the openly licensed
UCI Istanbul Stock Exchange dataset (Akbilgic, 2013; CC BY 4.0; DOI 10.24432/C54P4J).
The course lab covered classifiers, chronological splitting, scaling, K-means/PCA
and five exercises. The public version implements a new evaluation pipeline;
course data and course code are not redistributed.

Development selection includes the baseline and chooses the historical up-rate.
Five later test blocks contain 216 dates: Brier **0.245605** for the prior versus
**0.246611** for local logistic regression. The paired difference is **+0.001006**
with a pointwise 95% moving-block interval **[−0.002279, +0.004296]**.
Feature ablations and block-length sensitivity do not establish a predictive edge.
These are retrospective results on one market, not a profitability claim.

The project saves predictions and checks all metrics, split boundaries and
24 bootstrap intervals, then reruns the analysis and compares six reference tables.
Seven tests cover scientific failure modes such as future-feature leakage.
Use the project-specific `requirements.txt` in a separate environment, then run
`python run.py`, `python -m unittest discover -s tests -v` and `python verify.py`
from the project directory. The first run downloads the hash-pinned UCI workbook.
The [English research brief](https://jiayuyan117.github.io/academic-portfolio/projects/07-market-direction/report.html)
contains methods, source discrepancies and limitations.

### 08 · [Product Catalog: Protecting Small Data Changes](projects/08-product-catalog/PROJECT.html)

Java engineering project built around a textbook's product-management topic;
the implementation is original and no textbook code is redistributed. Local HTTP CRUD,
exact CNY cents, atomic file snapshots and version checks keep records consistent.
Revision-checked pagination adds deterministic SKU/price ordering and rejects
stale navigation with HTTP 409. Thirteen failure-oriented test groups passed
locally, including real HTTP requests, complete page traversal, restart recovery,
competing edits and failed storage writes. Queries remain scan-based, without a performance claim.

GitHub Pages displays the static brief only; the backend requires a local JDK.
No research results or deployed business system are claimed. See
[setup and evidence](projects/08-product-catalog/README.md)
and [sources](projects/08-product-catalog/PROVENANCE.md).

</details>

## Reproducibility

Each project has checks matched to its claims. The NLP workflow recomputes
committed metrics and runs a real-data sample experiment; full-data model
training is an explicit local command, not a claim about routine CI.

| Project | Recorded CI success and scope | Reproduction command |
| --- | --- | --- |
| 01 Equity forecasting | Windows: 11 tables / 252 reference values, `rtol=1e-6` | `python run_analysis.py` |
| 02 Market linkages | Linux and Windows: 8 tables / 334 reference values, `rtol=1e-6`; rolling-origin and generalized-FEVD extension | `python robustness.py`; `python run_analysis.py` |
| 03 NEV transition | Linux: figure rebuild, data/semantic checks and backtest leakage tests; unresolved source records remain labelled | `python src/nev_visualization.py`; `python src/build_figures_en.py`; `python src/market_backtest.py` |
| 04 Bike sharing | Linux: chart rebuild and date-reconciliation checks | `python src/build_charts.py` |
| 05 Beijing PM2.5 | Linux: analysis/figure rebuild, gap audit and next-day target tests | `python src/analyze.py`; `python src/alert_model.py` |
| 06 Job-posting NLP | Source reconstruction, saved-prediction verification and sample training checks | `python run.py verify`; `python run.py smoke` |
| 07 Market direction | Local full rerun, seven temporal tests and prediction-level verification; dedicated CI workflow | `python verify.py`; `python -m unittest discover -s tests -v` |
| 08 Product catalog | Local Windows / JDK 21, Java 17 compilation target: 13 test groups; no workflow | `powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 test` |

Projects 01 and 02 ship a verifier rather than a runner. It checks the SHA-256 of
every input against `provenance.json`, clears all notebook outputs and
re-executes from scratch, fails on any cell error, and then compares every
regenerated number against stored reference values. A silent change in a library
version shows up as a failed build, not as a quietly different conclusion.

Commands in the table run from the corresponding project directory.
For projects 01–05, dependency declarations and the root `constraints.txt`
define the Python environment; CPython 3.12.10 is the documented environment.
Projects 06 and 07 have dedicated workflows and separate reproduction instructions.
Project 01's Linux optimizer output exceeds the original tolerance; that
platform is not certified against the Windows reference.
See the [workflow runs](https://github.com/jiayuyan117/academic-portfolio/actions/workflows/build.yml)
for the existing evidence, and [REPRODUCING.md](REPRODUCING.md) for setup and limitations.
README text is maintained separately; generated outputs do not update it automatically.

```bash
git clone https://github.com/jiayuyan117/academic-portfolio.git
cd academic-portfolio
python -m venv .venv
# Use Windows for project 01; activate .venv as described in REPRODUCING.md.
python -m pip install -c constraints.txt -r requirements.txt
python tools/rebuild.py --project 05
```

## Skills these projects demonstrate

**Decision analytics** — cost-based alert thresholds chosen on a validation year,
sensitivity to assumed cost ratios, market sizing under stated ceilings, and
explicit separation of what a model supports from what still needs evidence.

**Forecast evaluation** — rolling-origin and strictly temporal splits, simple
baselines kept in every comparison, Diebold–Mariano tests, paired moving-block
bootstrap intervals and leakage tests on targets and features.

**NLP research design** — text-only, lexicon-only and combined-feature comparisons;
employer-disjoint evaluation; distinguishing category accuracy from exact-span extraction.

**Econometrics** — ARMA/ARIMA, VAR/VECM, unit-root and cointegration testing,
Granger causality, Cholesky and generalized variance decompositions, residual
and ARCH diagnostics.

**Data engineering & quality** — hash-verified inputs, join-integrity checks,
gap-length audits before imputation, data-completeness rules, date and unit
normalisation, reconciliation between sources, deterministic pipelines with fixed seeds.

**Visualisation & communication** — Matplotlib, Seaborn and standalone Plotly
charts captioned with source, denominator and caveats; reports that separate
what was measured, estimated and assumed; bilingual (English / Chinese) delivery.

## Authorship

**Author: Jiayu Yan / 闫佳玉.** All projects in this repository are the author's
own work, developed from her undergraduate coursework and independent study.
AI tools assisted with coding, editing and bilingual website presentation.
Verification scope is documented in each project's linked evidence; automated checks
do not establish independent authorship or validate every conclusion.
Original coursework is retained in the source folders of projects 01, 02 and 05.
Project 07 does not redistribute course data or code and uses a new implementation
with CC BY 4.0 data; project 08 does not redistribute textbook code.

Decision notes describe implications and proposed next steps, not interventions
already tested. Estimates, assumed cost ratios and scenarios — including the NEV
carbon scenario — are distinguished from published statistics; unresolved source
verification is explicitly disclosed.

No result in this repository is presented as more certain than the evidence
supports. Where a model fails, the failure is the finding.

## Contact

GitHub: [@jiayuyan117](https://github.com/jiayuyan117)

Code is MIT licensed. Third-party datasets remain under their original terms; see
each project's provenance section.

中文版本：[README.zh-CN.md](README.zh-CN.md)
