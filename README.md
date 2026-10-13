# Jiayu Yan — Data Analytics Portfolio

B.Mgmt. in **Big Data Management and Applications**, Guangdong University of Technology
· Applying for MS programmes in Data Science / Business Analytics (US · Singapore · Hong Kong)

**[→ Browse the portfolio site](https://jiayuyan117.github.io/academic-portfolio/)**

---

## What this repository is for

Four projects, each built around a single question: *does this result survive
being checked?*

Coursework usually ends at the first plausible number. These projects keep going
to the part that decides whether the number means anything — whether a forecast
beats a trivial benchmark, whether a "linkage" survives a change of identifying
assumption, whether two data files that are supposed to agree actually join at
all. Two of the four headline findings below are **negative results**, and they
are the ones I would most want to be asked about.

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

## Reproducibility

| Project | Verifies its own numbers | Command |
| --- | --- | --- |
| 01 Equity forecasting | 11 tables / 252 values, `rtol=1e-6` | `python run_analysis.py` |
| 02 Market linkages | 8 tables / 334 values, `rtol=1e-6` | `python run_analysis.py` |
| 03 NEV transition | — | `python src/nev_visualization.py && python src/build_figures_en.py` |
| 04 Bike sharing | README numbers read from `findings.json` | `python src/build_charts.py` |

Projects 01 and 02 ship a verifier rather than a runner. It checks the SHA-256 of
every input against `provenance.json`, clears all notebook outputs and
re-executes from scratch, fails on any cell error, and then compares every
regenerated number against stored reference values. A silent change in a library
version shows up as a failed build, not as a quietly different conclusion.

Each project pins its dependencies in its own `requirements.txt`. Python 3.12.
A GitHub Actions workflow rebuilds projects 03 and 04 from a clean checkout on
every push, so a pipeline that only works on my laptop cannot go unnoticed.


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

**Data engineering & quality** — hash-verified inputs, join-integrity checks,
date and unit normalisation, reconciliation between independent sources,
deterministic end-to-end pipelines.

**Visualisation** — Matplotlib for print, Plotly and Pyecharts for interaction;
explicit encoding of every visual channel; figures captioned with their source,
denominator and known caveats.

**Research communication** — reports that separate what was measured, what was
estimated, and what remains assumed; bilingual (English / Chinese) delivery.

## Academic integrity and AI use

All four projects originate in my own undergraduate coursework. Original course
submissions and datasets are retained unmodified in each project's
`source_materials/` directory so the development from assignment to portfolio
version can be inspected directly.

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
