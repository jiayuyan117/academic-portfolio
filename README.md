# Jiayu Yan — Data Analytics Portfolio

B.Mgmt. in **Big Data Management and Applications**, Guangdong University of Technology
· Applying for MS programmes in Data Science / Business Analytics (US · Singapore · Hong Kong)

**[→ Browse the portfolio site](https://jiayuyan117.github.io/academic-portfolio/)**

---

## What this repository is for

Seven projects, each built around a single question: *does this result survive
being checked?*

Coursework usually ends at the first plausible number. These projects keep going
to the part that decides whether the number means anything — whether a forecast
beats a trivial benchmark, whether a "linkage" survives a change of identifying
assumption, whether two data files that are supposed to agree actually join at
all, whether a customer segment that looks different really is.

**Five of the seven headline findings below are negative or corrective results.**
Those are the ones I would most want to be asked about: a portfolio of seven
confirmed hypotheses would say less about how I work than one honest null.

Every project runs from a clean checkout and regenerates its own figures and
tables. Two of them verify their output numerically against stored reference
values on every run and **fail loudly** if anything drifts.


## Projects

### 1 · [Equity Time-Series Forecasting](projects/01-equity-time-series-forecasting/)
`statsmodels` · `ARMA/ARIMA` · `fixed-origin holdout` · `252 values verified per run`

Training-only BIC selects MA(2); it beats a zero-return forecast by **0.29% of
RMSE** on an untouched 20-day holdout — while Ljung-Box **rejects** residual
adequacy at lag 20 and ARCH-LM rejects constant variance (*p* = 4e-09).
The project is built to make both facts visible at once, because a 0.29% edge on
one window is not a model you would use.

### 2 · [Shanghai–Hong Kong Market Linkages](projects/02-shanghai-hongkong-market-linkages/)
`VAR / VECM` · `Johansen` · `Granger` · `334 values verified per run`

A Shanghai shock appears to explain **32.4%** of Hong Kong's 10-step
forecast-error variance — until the Cholesky ordering is reversed, when the same
quantity becomes **0.35%**. Same data, same model, same sample; only the
identifying assumption changed. VAR(7) also loses to a zero-return benchmark on
MAE in both markets, and neither Granger direction is significant.

### 3 · [China's NEV Transition, 2015–2025](projects/03-china-nev-industry-analytics/)
`pandas` · `matplotlib` · `7 compiled tables` · `16 figures, bilingual`

NEV share of new vehicle sales went from **1.3% to 47.9%** in eleven years. The
findings that complicate the story: charging capacity outgrew the fleet but almost
entirely through **private** chargers (public share fell 48% → 23%); battery
chemistry reversed toward LFP (40% → **81%**); and plug-in hybrids *gained* share
(17% → **36%**). Every denominator, definition change and scenario assumption is
documented, including a 0.3 GWh discrepancy against an official total.

### 4 · [Bike-Sharing Interactive Visualisation](projects/04-bike-sharing-interactive-visualization/)
`Plotly` · `Pyecharts` · `17,379 observations` · [live charts](https://jiayuyan117.github.io/academic-portfolio/projects/04-bike-sharing-interactive-visualization/charts/01_sunburst.html)

The two files in the UCI Bike Sharing Dataset store dates as `2011/1/1` and
`2011-01-01`, so the obvious join between them matches **0 of 731 days** — and
any reconciliation check built on it passes while comparing nothing to nothing.
Parsed properly, the files do agree exactly. Four interactive figures, each
labelling what every visual channel encodes.

### 5 · [Beijing PM2.5, 2010–2014](projects/05-beijing-air-quality-seaborn/)
`Seaborn` · `43,824 hourly observations` · `7 figures`

PM2.5 exceeded China's grade II daily limit in **48.5%** of hours. What explains
the variation is ventilation, not temperature: Spearman ρ = **−0.360** for wind
speed against **+0.011** for temperature, and median PM2.5 is **6.3× higher** in
the calmest wind decile than the windiest. Temperature's Pearson *r* (−0.091) and
Spearman ρ (+0.011) **disagree on the sign**, which is why the coursework version
should not have led with the linear coefficient. Separately, 1,341 of the 2,067
missing hours sit inside gaps longer than a day — the longest is 155 consecutive
hours — so **91% of them are left missing** rather than interpolated into a smooth
ramp through a possible haze episode.

### 6 · [Consumer Transactions: A Segmentation That Isn't There](projects/06-consumer-behaviour-matplotlib/)
`Matplotlib` · `8,000 transactions` · `bootstrap CIs · ANOVA · permutation null`

The brief asks which customer groups spend more. Tested first: **four of the five
candidate segmentations do not differ at all** (age band *p* = 0.45, gender 0.52,
city tier 0.77, payment method 0.90). Income's correlation with spend is −0.010
with a 95% CI of [−0.032, +0.012] — narrow enough to be a measured *absence*, not
a missing finding. Only membership tier separates (*p* = 1.0 × 10⁻⁶, robust to
trimming), and its direction is unidentified because tiers are awarded *for*
spending. Monthly revenue falls inside a permutation null band in **all 12
months**, so there is no seasonality to explain either.

### 7 · [Personal Learning Knowledge Base / Course Materials Workbench](projects/07-workforce-system-java/)
`Java 21` · `embedded Tomcat 9` · `JSP/Servlet/JDBC` · `H2` · `security review`

This course project reframes a materials manager as a bounded personal learning
workspace: users, course materials, keyword retrieval and owner-scoped
attachments. The report confirms password hashing, remember-me tokens, CSRF,
multipart limits, and a reported **66-check integration suite** plus a 390px
mobile check. The original Java Web source is absent from this checkout, so the
portfolio includes an evidence map and runnable manifest rather than claiming a
reconstructed server.


## Reproducibility

| Project | Verifies its own numbers | Command |
| --- | --- | --- |
| 01 Equity forecasting | 11 tables / 252 values, `rtol=1e-6` | `python run_analysis.py` |
| 02 Market linkages | 8 tables / 334 values, `rtol=1e-6` | `python run_analysis.py` |
| 03 NEV transition | — | `python src/nev_visualization.py && python src/build_figures_en.py` |
| 04 Bike sharing | README numbers read from `findings.json` | `python src/build_charts.py` |
| 05 Beijing PM2.5 | README numbers read from `findings.json` | `python src/analyze.py` |
| 06 Consumer transactions | README numbers read from `findings.json`, fixed seeds | `python src/analyze.py` |
| 07 Learning knowledge base | Reported 66 integration checks / 390px mobile check | `javac PortfolioFacts.java && java PortfolioFacts` |


Projects 01 and 02 ship a verifier rather than a runner. It checks the SHA-256 of
every input against `provenance.json`, clears all notebook outputs and
re-executes from scratch, fails on any cell error, and then compares every
regenerated number against stored reference values. A silent change in a library
version shows up as a failed build, not as a quietly different conclusion.

Each project pins its dependencies in its own `requirements.txt` where applicable.
Python 3.12 and Java 21 are used by the corresponding projects.
A GitHub Actions workflow rebuilds projects 03–07 from a clean checkout on every
push, so a pipeline that only works on my laptop cannot go unnoticed.



```bash
git clone https://github.com/jiayuyan117/academic-portfolio.git
cd academic-portfolio/projects/01-equity-time-series-forecasting
pip install -r requirements.txt
python run_analysis.py
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

**Visualisation** — Matplotlib and Seaborn for print, Plotly and Pyecharts for
interaction; explicit encoding of every visual channel; figures captioned with
their source, denominator and known caveats.


**Research communication** — reports that separate what was measured, what was
estimated, and what remains assumed; bilingual (English / Chinese) delivery.

## Academic integrity and AI use

All seven projects originate in my own undergraduate coursework. Original course
submissions and datasets are retained unmodified in each project's
`source_materials/` directory so the development from assignment to portfolio
version can be inspected directly — including, in projects 04 and 05, the places
where the portfolio version corrects a method error in my own earlier work.


AI assistance was used for code structuring, English writing, and verification
tooling. The research questions, the sensitivity and robustness analyses that
produce the findings above, and all interpretation are my own. Where a number is
my estimate rather than a published statistic — most visibly the NEV carbon
scenario — it is labelled as such in the figure itself.

No result in this repository is presented as more certain than the evidence
supports. Where a model fails, the failure is the finding.

## Contact

GitHub: [@jiayuyan117](https://github.com/jiayuyan117)

Code is MIT licensed. Third-party datasets remain under their original terms; see
each project's provenance section.

中文版本：[README.zh-CN.md](README.zh-CN.md)
