# Jiayu Yan — Data Analytics Portfolio

**Author: 闫佳玉 / Jiayu Yan**

B.Mgmt. in **Big Data Management and Applications**, Guangdong University of Technology
· Applying for MS programmes in Data Science / Business Analytics (US · Singapore · Hong Kong)

**[→ Browse the portfolio site](https://jiayuyan117.github.io/academic-portfolio/)**

---

## What this repository is for

These projects connect statistical analysis with decisions: *does this result
survive being checked, and what should we do with it?*

The nine projects develop undergraduate coursework into reproducible studies. They
examine whether skill features improve job-category classification, whether a
forecast beats a simple benchmark, how market-linkage estimates depend on
identifying assumptions, whether data quality supports a business conclusion,
and whether small systems keep their data consistent under change.

Negative findings and methodological corrections are reported alongside the
claims they qualify. Failure to reject a null hypothesis is not proof of no
effect, and an observational association is not an intervention effect.

CI has recorded successful numerical verification, analysis/figure rebuilds or
Java tests for projects **01–05 and 07**, as appropriate to each project. The two
econometrics projects check input SHA-256 hashes and **586 numerical values**
against stored references at `rtol=1e-6`. Project **08** adds an exactly
reconstructed source cohort and prediction-level metric verification.

## A 30-second reading guide

I study Big Data Management and Applications and am applying for Data Science /
Business Analytics master's programmes in the **US, Singapore and Hong Kong**.
This portfolio connects evaluation, data quality and analytical communication
with decisions whose limits are made explicit.

Start with three selected studies: **08 → 09 → 05**. They demonstrate NLP
evaluation, temporal validation and missing-data judgment with traceable evidence.
For a quantitative/econometrics programme, substitute **02** for 05.

| Selection | Why read it | Evidence entry |
| --- | --- | --- |
| [08 · NLP evaluation](projects/08-nlp-job-postings/report.html) | Employer-disjoint feature comparison; separate extraction evaluation | [Saved predictions and checks](projects/08-nlp-job-postings/README.md#what-is-independently-checkable) |
| [09 · Temporal ML](projects/09-market-direction/report.html) | Baseline-inclusive selection and uncertainty across later test blocks | [Verification](projects/09-market-direction/verify.py) |
| [05 · Missing data](projects/05-beijing-air-quality-seaborn/FIRST_READ.html) | Gap audit before imputation; observed-only conclusions | [Findings](projects/05-beijing-air-quality-seaborn/outputs/findings.json) |
| [02 · Identification alternative](projects/02-shanghai-hongkong-market-linkages/FIRST_READ.html) | Same-model results change with shock ordering | [Numerical evidence](projects/02-shanghai-hongkong-market-linkages/results/verification.json) |

**DS route: 08 → 09 → 05 → 02. BA route: 08 → 05 → 03 → 04.**
The BA route moves from feature value and data quality to market denominators and
demand-data reconciliation. These routes reflect programme emphasis, not a uniform
admissions standard across countries.

**Engineering supplements:** choose **10** for persistence, revision-checked
pagination and HTTP tests, or **07** for data structures and invariants.
**Further supplements:** 01 (forecast diagnostics), 03 (market sources) and 04
(visual communication).

<details>
<summary>Full project directory — selected studies and supplements</summary>

| Project | Focus |
| --- | --- |
| [01 · Equity forecasting](projects/01-equity-time-series-forecasting/) | Benchmarks and residual diagnostics |
| [02 · Market linkages](projects/02-shanghai-hongkong-market-linkages/) | Sensitivity to identifying assumptions |
| [03 · NEV transition](projects/03-china-nev-industry-analytics/) | Source traceability and market denominators |
| [04 · Bike sharing](projects/04-bike-sharing-interactive-visualization/) | Date reconciliation and interactive charts |
| [05 · Beijing PM2.5](projects/05-beijing-air-quality-seaborn/) | Missingness and observational associations |
| [07 · Java workforce system](projects/07-workforce-system-java/) | Data structures and invariant testing |
| [08 · Does the Skill Signal Help?](projects/08-nlp-job-postings/README.md) | NLP evaluation, negative findings and reproducibility |
| [09 · When the Baseline Wins](projects/09-market-direction/report.html) | Purged temporal ML, baseline-inclusive selection and block-bootstrap uncertainty |
| [10 · Product catalog](projects/10-product-catalog/PROJECT.html) | Persistent records, stale-edit rejection and HTTP boundary tests |

</details>

### Business Analytics: from question to decision

| Project | Decision question and method | Evidence and action boundary |
| --- | --- | --- |
| [03 · Market assessment](projects/03-china-nev-industry-analytics/README.md) | Reconcile public sales, battery and charging statistics before assessing market transition. | 47.9% NEV share uses all-vehicle sales including exports. Site investment still needs local utilization, power and cost data. |
| [05 · Data quality](projects/05-beijing-air-quality-seaborn/README.md) | Audit missing hourly measurements before interpreting associations. | Long gaps remain unfilled; observational patterns support further validation, not intervention effects. |
| [08 · Job-information quality](projects/08-nlp-job-postings/README.md) | Compare text and skill features on held-out employers; evaluate extraction separately. | Fusion Macro-F1 of 0.7348 versus 0.7406 for text does not justify the added features under this study's criterion. Operational value remains unmeasured. |

Read each project as **question → data and method → result → decision implication
→ limitation**. The recommendations are academic interpretations, not deployed
interventions or measured ROI. The environmental study (05) demonstrates transferable
missing-data analysis and uncertainty communication; the Java project (07)
demonstrates data consistency rather than a measured business improvement.

## Supporting project briefs and complete evidence

<details>
<summary>Expand all 9 briefs (start with the selected studies above)</summary>

### 01 · [Equity Time-Series Forecasting](projects/01-equity-time-series-forecasting/)
`statsmodels` · `ARMA/ARIMA` · `fixed-origin holdout` · `252 values verified per run`

Training-only BIC selects MA(2); it beats a zero-return forecast by **0.29% of
RMSE** on an untouched 20-day holdout — while Ljung-Box **rejects** residual
adequacy at lag 20 and ARCH-LM rejects constant variance (*p* = 4e-09).
The project is built to make both facts visible at once, because a 0.29% edge on
one window is not a model you would use.

**Decision:** retain the benchmark until time-based validation across more
windows and transaction-cost analysis establish a practically useful gain.

### 02 · [Shanghai–Hong Kong Market Linkages](projects/02-shanghai-hongkong-market-linkages/)
`VAR / VECM` · `Johansen` · `Granger` · `334 values verified per run`

A Shanghai shock appears to explain **32.4%** of Hong Kong's 10-step
forecast-error variance — until the Cholesky ordering is reversed, when the same
quantity becomes **0.35%**. Same data, same model, same sample; only the
identifying assumption changed. VAR(7) also loses to a zero-return benchmark on
MAE in both markets, and neither Granger direction is significant.

**Decision:** do not derive a directional hedge or causal shock attribution
from a result that changes this much under an alternative identification order.

### 03 · [China's NEV Transition, 2015–2025](projects/03-china-nev-industry-analytics/)
`pandas` · `matplotlib` · `7 compiled tables` · `16 figures, bilingual`

In 2025, NEVs accounted for **47.9%** of CAAM's all-vehicle sales **including
exports**, a different denominator from domestic sales or registrations.
The [source audit](docs/NEV_SOURCE_AUDIT.md) corrects a 2021 PHEV input and
documents the **2025 charging-statistics break**, battery-chemistry subtotals,
rounded inputs and unresolved historical verification. The carbon calculation
is an illustrative scenario, not measured emissions savings.

**Decision:** charging investment needs location, utilization and power data.
National counts and a reporting break cannot establish where capacity is scarce.

### 04 · [Bike-Sharing Interactive Visualisation](projects/04-bike-sharing-interactive-visualization/)
`Plotly` · `offline interactive charts` · `17,379 observations` · [live charts](https://jiayuyan117.github.io/academic-portfolio/projects/04-bike-sharing-interactive-visualization/charts/01_sunburst.html)

The two files in the UCI Bike Sharing Dataset store dates as `2011/1/1` and
`2011-01-01`, so the obvious join between them matches **0 of 731 days** — and
any reconciliation check built on it passes while comparing nothing to nothing.
Parsed properly, the files do agree exactly. Four offline-capable interactive
figures each label what every visual channel encodes.

**Decision:** reconcile totals before demand planning. Station-level fleet
rebalancing additionally needs local availability and service-cost data.

### 05 · [Beijing PM2.5, 2010–2014](projects/05-beijing-air-quality-seaborn/)
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

### 07 · [Workforce System in Java](projects/07-workforce-system-java/)
`Java 17` · `department tree` · `balanced employee index` · `JUnit 5`

An organization tree and an employee search index must describe the same people.
The system validates transfers, deletion, membership and ordering after every
operation. Immutable records and integer salary cents make state changes explicit.
Reference-model tests cover random operations as well as ordered IDs, deletion,
transfers and structural invariants.

**Decision:** consistent membership supports trustworthy headcount reporting.
Production use would also require persistence, authorization and audit history.


### 08 · [Does the Skill Signal Help?](projects/08-nlp-job-postings/README.md)
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
[Read the research brief](https://jiayuyan117.github.io/academic-portfolio/projects/08-nlp-job-postings/report.html).

### 09 · [When the Baseline Wins](projects/09-market-direction/report.html)

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
The [English research brief](https://jiayuyan117.github.io/academic-portfolio/projects/09-market-direction/report.html)
contains methods, source discrepancies and limitations.

### 10 · [Product Catalog: Protecting Small Data Changes](projects/10-product-catalog/PROJECT.html)

Java engineering project built around a textbook's product-management topic;
the implementation is original and no textbook code is redistributed. Local HTTP CRUD, exact CNY cents,
atomic file snapshots and version checks complement project 07's in-memory structures.
Revision-checked pagination adds deterministic SKU/price ordering and rejects
stale navigation with HTTP 409. Thirteen failure-oriented test groups passed
locally, including real HTTP requests, complete page traversal, restart recovery,
competing edits and failed storage writes. Queries remain scan-based, without a performance claim.

GitHub Pages displays the static brief only; the backend requires a local JDK.
No research results or deployed business system are claimed. See
[setup and evidence](projects/10-product-catalog/README.md)
and [sources](projects/10-product-catalog/PROVENANCE.md).

</details>

## Reproducibility

Each project has checks matched to its claims. The NLP workflow recomputes
committed metrics and runs a real-data sample experiment; full-data model
training is an explicit local command, not a claim about routine CI.

| Project | Recorded CI success and scope | Reproduction command |
| --- | --- | --- |
| 01 Equity forecasting | Windows: 11 tables / 252 reference values, `rtol=1e-6` | `python run_analysis.py` |
| 02 Market linkages | Linux and Windows: 8 tables / 334 reference values, `rtol=1e-6` | `python run_analysis.py` |
| 03 NEV transition | Linux: figure rebuild and data/semantic checks; unresolved source records remain labelled | `python src/nev_visualization.py` then `python src/build_figures_en.py` |
| 04 Bike sharing | Linux: chart rebuild and date-reconciliation checks | `python src/build_charts.py` |
| 05 Beijing PM2.5 | Linux: analysis/figure rebuild, hourly-index and gap audit | `python src/analyze.py` |
| 07 Workforce system | Linux / Java 17: Maven verification, JUnit and reference-model tests | `mvn verify` |
| 08 Job-posting NLP | Source reconstruction, saved-prediction verification and sample training checks | `python run.py verify`; `python run.py smoke` |
| 09 Market direction | Local full rerun, seven temporal tests and prediction-level verification; dedicated CI workflow | `python verify.py`; `python -m unittest discover -s tests -v` |
| 10 Product catalog | Local Windows / JDK 21, Java 17 compilation target: 13 test groups; no workflow | `powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 test` |


Projects 01 and 02 ship a verifier rather than a runner. It checks the SHA-256 of
every input against `provenance.json`, clears all notebook outputs and
re-executes from scratch, fails on any cell error, and then compares every
regenerated number against stored reference values. A silent change in a library
version shows up as a failed build, not as a quietly different conclusion.

Commands in the table run from the corresponding project directory.
For projects 01–05, dependency declarations and the root `constraints.txt`
define the Python environment; CPython 3.12.10 and JDK 17 are the documented
environments for 01–07. Their CI covers notebook re-execution, analysis/figure
rebuilds and Java tests according to each project's task. Projects 08 and 09 have
dedicated workflows and separate reproduction instructions.
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
python tools/rebuild.py --project 01
```

## Skills these projects demonstrate

**NLP research design** — text-only, lexicon-only and combined-feature comparisons;
employer-disjoint evaluation; distinguishing category accuracy from exact-span
extraction. Current reproduction status is stated separately from the original report.

**Econometrics & forecasting** — ARMA/ARIMA, VAR/VECM, unit-root and cointegration
testing, Granger causality, impulse responses and variance decomposition,
residual and ARCH diagnostics, fixed-origin out-of-sample evaluation against
pre-specified benchmarks.

**Inference discipline** — employer-cluster and moving-block bootstrap intervals,
paired model comparisons against pre-specified baselines, residual whiteness and
ARCH tests, identification-sensitivity checks, and the judgement to report
uncertainty and limits on detectable differences.

**Data engineering & quality** — hash-verified inputs, join-integrity checks,
gap-length audits before imputation, date and unit normalisation, reconciliation
between independent sources, deterministic end-to-end pipelines with fixed seeds.

**Visualisation** — Matplotlib and Seaborn for print, standalone Plotly charts for
interaction; original Pyecharts coursework retained for comparison; explicit encoding
of every visual channel; figures captioned with
their source, denominator and known caveats.


**Research communication** — reports that separate what was measured, what was
estimated, and what remains assumed; bilingual (English / Chinese) delivery.

## Authorship

**Author: Jiayu Yan / 闫佳玉.** All projects in this repository are the author's
own work, developed from her undergraduate coursework and independent study.
AI tools were used for coding support and English editing; the author reviewed
and verified all code, results and conclusions. Course materials and textbook
code are not redistributed; project 09 uses a new implementation and CC BY 4.0 data.

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
