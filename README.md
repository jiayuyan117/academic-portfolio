# Jiayu Yan — Data Analytics Portfolio

B.Mgmt. in **Big Data Management and Applications**, Guangdong University of Technology
· Applying for MS programmes in Data Science / Business Analytics (US · Singapore · Hong Kong)

**[→ Browse the portfolio site](https://jiayuyan117.github.io/academic-portfolio/)**

---

## What this repository is for

These projects connect statistical analysis with decisions: *does this result
survive being checked, and what should we do with it?*

Coursework usually ends at the first plausible number. These projects keep going
to the part that decides whether the number means anything — whether a forecast
beats a trivial benchmark, whether a "linkage" survives a change of identifying
assumption, whether two data files that are supposed to agree actually join at
all, whether a customer segment that looks different really is.

Negative findings and methodological corrections are reported alongside the
claims they qualify. Failure to reject a null hypothesis is not proof of no
effect, and an observational association is not an intervention effect.

The Python projects regenerate their figures and tables; the Java project runs
behavioural tests. The two econometrics projects check input SHA-256 hashes
and **586 numerical values** against stored references at `rtol=1e-6`.

## A 30-second reading guide

I study Big Data Management and Applications and use these coursework-based
projects to demonstrate analysis, communication and engineering discipline.
Start with **06** for a business question carried through to a decision note.
Read **01 → 02** for forecasting and identification; **03 → 04 → 05** for
industry-data traceability, visual communication and data quality; and **07**
for data structures and invariant testing. No causal experiment is claimed.

## Projects

### 1 · [Equity Time-Series Forecasting](projects/01-equity-time-series-forecasting/)
`statsmodels` · `ARMA/ARIMA` · `fixed-origin holdout` · `252 values verified per run`

Training-only BIC selects MA(2); it beats a zero-return forecast by **0.29% of
RMSE** on an untouched 20-day holdout — while Ljung-Box **rejects** residual
adequacy at lag 20 and ARCH-LM rejects constant variance (*p* = 4e-09).
The project is built to make both facts visible at once, because a 0.29% edge on
one window is not a model you would use.

**Decision:** retain the benchmark until time-based validation across more
windows and transaction-cost analysis establish a practically useful gain.

### 2 · [Shanghai–Hong Kong Market Linkages](projects/02-shanghai-hongkong-market-linkages/)
`VAR / VECM` · `Johansen` · `Granger` · `334 values verified per run`

A Shanghai shock appears to explain **32.4%** of Hong Kong's 10-step
forecast-error variance — until the Cholesky ordering is reversed, when the same
quantity becomes **0.35%**. Same data, same model, same sample; only the
identifying assumption changed. VAR(7) also loses to a zero-return benchmark on
MAE in both markets, and neither Granger direction is significant.

**Decision:** do not derive a directional hedge or causal shock attribution
from a result that changes this much under an alternative identification order.

### 3 · [China's NEV Transition, 2015–2025](projects/03-china-nev-industry-analytics/)
`pandas` · `matplotlib` · `7 compiled tables` · `16 figures, bilingual`

In 2025, NEVs accounted for **47.9%** of CAAM's all-vehicle sales **including
exports**, a different denominator from domestic sales or registrations.
The [source audit](docs/NEV_SOURCE_AUDIT.md) corrects a 2021 PHEV input and
documents the **2025 charging-statistics break**, battery-chemistry subtotals,
rounded inputs and unresolved historical verification. The carbon calculation
is an illustrative scenario, not measured emissions savings.

**Decision:** charging investment needs location, utilization and power data.
National counts and a reporting break cannot establish where capacity is scarce.

### 4 · [Bike-Sharing Interactive Visualisation](projects/04-bike-sharing-interactive-visualization/)
`Plotly` · `offline interactive charts` · `17,379 observations` · [live charts](https://jiayuyan117.github.io/academic-portfolio/projects/04-bike-sharing-interactive-visualization/charts/01_sunburst.html)

The two files in the UCI Bike Sharing Dataset store dates as `2011/1/1` and
`2011-01-01`, so the obvious join between them matches **0 of 731 days** — and
any reconciliation check built on it passes while comparing nothing to nothing.
Parsed properly, the files do agree exactly. Four offline-capable interactive
figures each label what every visual channel encodes.

**Decision:** reconcile totals before demand planning. Station-level fleet
rebalancing additionally needs local availability and service-cost data.

### 5 · [Beijing PM2.5, 2010–2014](projects/05-beijing-air-quality-seaborn/)
`Seaborn` · `43,824 hourly observations` · `7 figures`

**48.5% of observed hourly readings** exceed 75 µg/m³, used here as a
daily-standard reference value, not an hourly compliance threshold. Spearman
ρ is **−0.360** for cumulated wind speed and **+0.011** for temperature.
Median PM2.5 is **6.3× higher** in the lowest cumulated-wind-speed decile than
the highest. Temperature's Pearson *r* (−0.091) and Spearman ρ (+0.011)
have different signs; conditional-median plots reveal more of the shape.
Separately, 1,341 of the 2,067
missing hours sit inside gaps longer than a day — the longest is 155 consecutive
hours. A short-gap policy audit leaves **91% unfilled**; the headline analysis
uses observed values only and excludes all 2,067 missing hours.

**Decision:** evaluate ventilation indicators for outdoor-work warnings using
later data and local monitoring. These associations do not identify the effect
of changing emissions or schedules.

### 6 · [Consumer Transactions: Testing Segmentation Claims](projects/06-consumer-behaviour-matplotlib/)
`Matplotlib` · `8,000 transactions` · `bootstrap CIs · ANOVA · permutation null`

The brief asks which customer groups spend more. Tested first: **four of the five
candidate groupings show no detectable mean-spend difference** (age band *p* = 0.44, gender 0.52,
city tier 0.77, payment method 0.90). Income's correlation with spend is −0.010
with a 95% CI of [−0.032, +0.012], constraining the linear association in this
sample without proving independence. Only membership tier separates (*p* = 1.0 × 10⁻⁶, robust to
trimming), and its direction is unidentified: the undocumented assignment rule
may depend on prior spending. Monthly revenue falls inside a permutation null band in **all 12
months**, so this analysis does not establish a seasonal pattern.
The source has **8,020 rows → 20 exact duplicates removed → 8,000 transactions**.
These transaction-level tests and intervals do not adjust for repeated customers,
so inferential results remain exploratory pending customer-level validation.

**Decision:** avoid demographic budget reallocation from these rankings alone.
Evaluate a randomized offer experiment using incremental contribution margin;
this is a proposed next step, not an experiment already performed.

### 7 · [Workforce System in Java](projects/07-workforce-system-java/)
`Java 17` · `department tree` · `balanced employee index` · `JUnit 5`

An organization tree and an employee search index must describe the same people.
The system validates transfers, deletion, membership and ordering after every
operation. Immutable records and integer salary cents make state changes explicit.
Reference-model tests cover random operations as well as ordered IDs, deletion,
transfers and structural invariants.

**Decision:** consistent membership supports trustworthy headcount reporting.
Production use would also require persistence, authorization and audit history.


## Reproducibility

| Project | Verifies its own numbers | Command |
| --- | --- | --- |
| 01 Equity forecasting | 11 tables / 252 values, `rtol=1e-6` | `python run_analysis.py` |
| 02 Market linkages | 8 tables / 334 values, `rtol=1e-6` | `python run_analysis.py` |
| 03 NEV transition | Source records, year alignment and arithmetic audit | `python src/nev_visualization.py` then `python src/build_figures_en.py` |
| 04 Bike sharing | Date reconciliation; outputs in `outputs/findings.json` | `python src/build_charts.py` |
| 05 Beijing PM2.5 | Hourly-index and gap audit; `outputs/findings.json` | `python src/analyze.py` |
| 06 Consumer transactions | Inference and fixed seeds; `outputs/findings.json` | `python src/analyze.py` |
| 07 Workforce system | JUnit tests and deterministic reference model | `mvn verify` |


Projects 01 and 02 ship a verifier rather than a runner. It checks the SHA-256 of
every input against `provenance.json`, clears all notebook outputs and
re-executes from scratch, fails on any cell error, and then compares every
regenerated number against stored reference values. A silent change in a library
version shows up as a failed build, not as a quietly different conclusion.

Commands in the table run from the corresponding project directory.
Each Python project has read-only dependency declarations; the root
`constraints.txt` fixes the resolved versions. CPython 3.12.10 and JDK 17
are the documented environments. GitHub Actions is configured to rebuild
**01–07**, including the full 01–02 numerical verifiers on Linux and Windows.
See the [actual workflow runs](https://github.com/jiayuyan117/academic-portfolio/actions/workflows/build.yml)
for execution status and [REPRODUCING.md](REPRODUCING.md) for setup and limitations.



```bash
git clone https://github.com/jiayuyan117/academic-portfolio.git
cd academic-portfolio
python -m venv .venv
# Activate .venv as described in REPRODUCING.md.
python -m pip install -c constraints.txt -r requirements.txt
python tools/rebuild.py --project 01
```

## Skills these projects demonstrate

**Econometrics & forecasting** — ARMA/ARIMA, VAR/VECM, unit-root and cointegration
testing, Granger causality, impulse responses and variance decomposition,
residual and ARCH diagnostics, fixed-origin out-of-sample evaluation against
pre-specified benchmarks.

**Inference discipline** — bootstrap and Fisher-z confidence intervals,
one-way ANOVA and Kruskal-Wallis with Bonferroni correction for multiple
groupings, permutation null bands, trimmed-mean robustness checks, and the
judgement to report a precise null instead of a ranking.

**Data engineering & quality** — hash-verified inputs, join-integrity checks,
gap-length audits before imputation, date and unit normalisation, reconciliation
between independent sources, deterministic end-to-end pipelines with fixed seeds.

**Visualisation** — Matplotlib and Seaborn for print, standalone Plotly charts for
interaction; original Pyecharts coursework retained for comparison; explicit encoding
of every visual channel; figures captioned with
their source, denominator and known caveats.


**Research communication** — reports that separate what was measured, what was
estimated, and what remains assumed; bilingual (English / Chinese) delivery.

## Academic integrity and AI use

All seven projects originate in my own undergraduate coursework. Original course
submissions and datasets are retained unmodified in each project's
`source_materials/` directory so the development from assignment to portfolio
version can be inspected directly — including, in projects 04 and 05, the places
where the portfolio version corrects a method error in my own earlier work.


AI assistance was used for code structuring, English writing, verification
tooling and review-driven revisions. Original coursework is retained separately.
Decision notes describe implications and proposed next steps, not interventions
already tested. Estimates and scenarios — including the NEV carbon scenario —
are distinguished from published statistics; unresolved source verification is
explicitly disclosed.

No result in this repository is presented as more certain than the evidence
supports. Where a model fails, the failure is the finding.

## Contact

GitHub: [@jiayuyan117](https://github.com/jiayuyan117)

Code is MIT licensed. Third-party datasets remain under their original terms; see
each project's provenance section.

中文版本：[README.zh-CN.md](README.zh-CN.md)
