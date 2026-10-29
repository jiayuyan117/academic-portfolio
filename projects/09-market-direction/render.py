"""Generate the English research brief and figures from computed evidence."""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
LABELS = {"selected": "Development-selected policy", "prior": "Historical up-rate",
          "half": "Constant 0.5", "local_lr": "Local logistic",
          "return_only": "Return-only logistic", "lagged_global_lr": "Lagged global logistic",
          "pca_lr": "PCA + logistic", "rolling252": "Selected / trailing 252"}


def render():
    out = ROOT / "results"
    meta = json.loads((out / "manifest.json").read_text())
    metrics = pd.read_csv(out / "metrics.csv").set_index("model")
    ci = pd.read_csv(out / "intervals.csv")
    folds = pd.read_csv(out / "fold_metrics.csv")
    dev = pd.read_csv(out / "development.csv").groupby("model").brier.mean().sort_values()
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "#faf9f5", "axes.facecolor": "#faf9f5"})
    plot = ci[(ci.block == 10) & ~ci.model.isin(["prior", "selected"])].copy()
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for i, row in enumerate(plot.itertuples()):
        ax.plot([row.low, row.high], [i, i], color="#16736d", linewidth=3)
        ax.scatter(row.delta_brier, i, color="#172d39", s=55, zorder=3)
    ax.set_yticks(range(len(plot)), [LABELS[x] for x in plot.model])
    ax.axvline(0, color="#ae793b", linestyle="--")
    ax.set_xlabel("Brier difference versus historical up-rate (negative favours candidate)")
    ax.set_title("Small apparent differences, wide uncertainty", loc="left", pad=18)
    fig.text(.02, .015, "216 out-of-sample days · paired circular block bootstrap · 4,000 draws · block = 10 · pointwise 95% intervals", fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.savefig(out / "uncertainty.png", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    dev.plot.barh(ax=axes[0], color=["#16736d" if n == "prior" else "#92aaa8" for n in dev.index])
    axes[0].set(xlabel="Mean development Brier (lower is better)", ylabel="",
                title="Selection includes the simple benchmark")
    for name in ("prior", "local_lr", "return_only", "lagged_global_lr"):
        g = folds[folds.model == name]
        axes[1].plot(g.fold + 1, g.brier, marker="o", label=LABELS[name])
    axes[1].set(xlabel="Chronological test block", ylabel="Brier score",
                title="Performance varies across time", xticks=range(1, 6))
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "selection.png", dpi=180)
    plt.close(fig)
    selected = metrics.loc["selected"]
    local = ci[(ci.model == "local_lr") & (ci.block == 10)].iloc[0]
    simple = ci[(ci.model == "return_only") & (ci.block == 10)].iloc[0]
    table = metrics.rename(index=LABELS).to_html(float_format=lambda x: f"{x:.6f}", border=0)
    dev_table = dev.rename("Mean Brier").to_frame().to_html(float_format=lambda x: f"{x:.6f}", border=0)
    ci_table = ci.replace({"model": LABELS}).to_html(index=False, float_format=lambda x: f"{x:.6f}", border=0)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="A reproducible, course-derived study of market direction: chronological selection, rolling evaluation, ablations and block-bootstrap uncertainty.">
<title>When the baseline wins | Jiayu Yan</title>
<style>
:root{{--ink:#172d39;--teal:#16736d;--paper:#faf9f5;--line:#d5dfda}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:17px/1.7 system-ui,sans-serif}}
main,header,footer{{max-width:1120px;margin:auto;padding:32px}}a{{color:#12645f;text-underline-offset:4px}}
nav{{display:flex;gap:24px;flex-wrap:wrap;font-size:14px}}header{{padding-top:32px;padding-bottom:64px}}
.eyebrow{{text-transform:uppercase;letter-spacing:.15em;font-size:12px;color:var(--teal);font-weight:700;margin-top:48px}}
h1{{font:normal clamp(42px,7vw,78px)/1.05 Georgia,serif;max-width:900px;margin:24px 0}}
h1 em{{color:var(--teal)}}.lede{{font-size:22px;max-width:790px}}h2{{font:32px/1.2 Georgia,serif;margin-top:0}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:32px}}
.stat{{padding:22px;border-top:3px solid var(--teal);background:white}}.stat b{{display:block;font:38px Georgia,serif}}.stat span{{font-size:14px}}
section{{background:white;border:1px solid var(--line);padding:32px;margin-bottom:26px;border-radius:12px}}
.note{{background:#eef3ef;border-left:4px solid var(--teal);padding:18px 24px}}img{{max-width:100%;height:auto}}
figure{{margin:24px 0}}figcaption,.small{{font-size:14px;color:#48606b}}.table{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{text-align:left;padding:10px;border-bottom:1px solid var(--line);white-space:nowrap}}th{{background:#eef3ef}}
code,pre{{font-size:13px}}pre{{padding:18px;background:#eef3ef;overflow:auto}}
summary{{cursor:pointer;font-weight:700;padding:12px 0}}a:focus-visible,summary:focus-visible{{outline:3px solid #ae793b}}
.steps{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}.steps div{{padding:16px;background:#eef3ef}}
@media(max-width:700px){{main,header,footer{{padding:22px}}section{{padding:22px}}.grid,.steps{{grid-template-columns:1fr}}.lede{{font-size:19px}}}}
</style></head><body>
<header><nav aria-label="Navigation"><a href="../../index.html#project-09">Portfolio</a><a href="#method">Study design</a><a href="#results">Results</a><a href="#reproduce">Reproduce</a><a href="#credit">Attribution</a></nav>
<p class="eyebrow">09 / Financial machine learning / Research extension of Lab 6</p>
<h1>When the<br><em>baseline wins.</em></h1>
<p class="lede">Can recent market returns predict tomorrow’s direction well enough to beat historical class frequency? In this small historical sample, model selection says: keep the baseline.</p>
<p>Jiayu Yan · Undergraduate research portfolio · AI-assisted extension · UCI Istanbul Stock Exchange</p>
<div class="grid"><div class="stat"><b>{meta['test_rows']}</b><span>out-of-sample trading days</span></div>
<div class="stat"><b>{selected.brier:.4f}</b><span>selected policy Brier score</span></div>
<div class="stat"><b>5</b><span>chronological test blocks</span></div></div></header>
<main><section><h2>The finding</h2>
<p>The historical up-rate wins the three development windows against logistic regression, a decision tree and random forests.
The locked selection policy therefore remains a frequency estimator during subsequent rolling evaluation. Its
accuracy is {selected.accuracy:.2%}; that figure alone is misleading because always predicting “up” achieves the same accuracy.</p>
<p>Local logistic regression changes Brier loss by <strong>{local.delta_brier:+.6f}</strong>
relative to the up-rate benchmark, with a pointwise 95% block-bootstrap interval
<strong>[{local.low:+.6f}, {local.high:+.6f}]</strong>. Lower is better.
The return-only ablation has a small apparent gain ({simple.delta_brier:+.6f}), but its interval
[{simple.low:+.6f}, {simple.high:+.6f}] crosses zero. These results do not establish either useful predictive skill or equivalence.</p>
<p class="note"><strong>Decision:</strong> retain the simple probabilistic benchmark for this dataset. No trading strategy,
profitability, economic impact, external validation or admissions endorsement is claimed.</p></section>
<section id="method"><h2>Time is part of the model</h2>
<div class="steps"><div><strong>01 · Develop</strong><br>First 300 usable rows. Expanding fits before validation starts 150, 200 and 250; 50 validation rows each.</div>
<div><strong>02 · Lock</strong><br>Select the lowest mean development Brier among six candidates, including the historical prior. Do not select again on the test results.</div>
<div><strong>03 · Walk forward</strong><br>Refit the locked model every 50 rows. Five test blocks: 50, 50, 50, 50 and 16. A one-row purge separates training and evaluation.</div></div>
<p>At an origin after Istanbul close on day <em>t</em>, predict whether the ISE local-currency return on the next observed trading day is positive.
Features are return at <em>t</em> and trailing 5/20-day return means and sample standard deviations.
All rolling features use only the current and previous rows. StandardScaler and PCA are fitted inside each training window.
Every boundary asserts that the last training target date is strictly earlier than the first evaluation origin.</p>
<p>Models: logistic C ∈ {{0.1, 1}}; decision tree depth 3; random forests depth 2 or 4, 200 trees.
Tree models use minimum leaf size 20 and seed {meta['seed']}. Threshold is fixed at 0.5.
The PCA ablation retains two components; all logistic ablations use C=0.1. Hyperparameters and windows
were encoded before the first numerical run, without an independent preregistration.</p>
<p>Secondary comparisons remove all but the current return, compress local features with PCA, add seven
foreign-market returns lagged by one dataset row, and restrict the selected policy to the latest 252 training rows.
Lagging foreign series reduces obvious closing-time leakage; the source does not provide release timestamps or data vintages,
so real-time availability is an assumption, not verified. These comparisons are exploratory; none replaces the locked primary policy.</p>
<figure><img src="results/selection.png" width="1980" height="756" alt="Development Brier comparison and test block performance"><figcaption>Development selection and later test performance are separate evidence. The final test block is shorter.</figcaption></figure></section>
<section id="results"><h2>Every comparison, including the awkward ones</h2>
<p>Brier score is the primary proper probability loss. Log loss, accuracy and AUC are secondary.
Pooled AUC of the refitted prior can differ from 0.5 because its probability changes between blocks;
within every block the prior's AUC is 0.5. This is not within-block ranking skill.</p>
<div class="table">{table}</div>
<figure><img src="results/uncertainty.png" width="1800" height="864" alt="Paired Brier differences with block-bootstrap intervals, all crossing zero"><figcaption>Negative differences favour the candidate. Intervals are conditional on saved predictions, with circular moving blocks preserving short-range dependence. They do not include model-selection or training-sample uncertainty.</figcaption></figure>
<details><summary>Development scores and selection evidence</summary><div class="table">{dev_table}</div></details>
<details><summary>Robustness: block lengths 5, 10 and 20</summary><p>4,000 paired resamples at each block length; seed fixed. Pointwise intervals are not multiplicity-adjusted.
Stationarity within the evaluation period is approximate. Zero-width intervals for “selected” are an identity: it selected the same prior, not certainty about future performance.</p><div class="table">{ci_table}</div></details>
<p><a href="results/predictions.csv">Prediction-level CSV</a> · <a href="results/splits.csv">Time boundaries</a> · <a href="results/metrics.csv">Metrics</a> · <a href="results/manifest.json">Source hash &amp; environment</a></p></section>
<section><h2>Data provenance &amp; limits</h2>
<p>Akbilgic, O. (2013). <em>ISTANBUL STOCK EXCHANGE</em> [Dataset]. UCI Machine Learning Repository.
<a href="https://doi.org/10.24432/C54P4J">doi:10.24432/C54P4J</a>.
The <a href="https://archive.ics.uci.edu/dataset/247/istanbul+stock+exchange">UCI dataset page</a> states
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>, verified 2026-10-29.
The original provider organized returns from imkb.gov.tr and finance.yahoo.com around Istanbul working days.</p>
<p>The workbook contains {meta['source_rows']} dated rows from {meta['source_first']} to {meta['source_last']}.
The catalogue prose says “Jun 5, 2009”; the workbook begins January 5, 2009. This study follows the parsed workbook and records that discrepancy.
Nineteen warm-up rows and one final row without a next-day label are excluded, leaving {meta['usable_rows']} rows.
The two columns named ISE are read positionally as local and USD returns; only the first is the target.
No missing numeric observations or duplicate dates are accepted. Inputs are downloaded into an ignored cache rather than redistributed.</p>
<p>Limitations: one market, approximately two years, only {meta['test_rows']} test days, no modern regime,
no corporate-action or price-feed audit, no execution model, and limited power. The final 16-day block is especially unstable.
Additional markets and a prospective evaluation would be required before generalizing. The original paper is cited as dataset context;
this experiment is not a reproduction of its RBF forecasting model.</p></section>
<section id="reproduce"><h2>Reproduce and challenge the result</h2>
<p>Python {meta['python']}; use an isolated environment and the project-specific pins. Run the following from this project directory:</p>
<pre>python -m pip install -r requirements.txt
python run.py
python -m unittest discover -s tests -v
python verify.py</pre>
<p>The first run downloads the UCI workbook; later runs reuse the ignored cache. Outputs include all per-day probabilities,
development scores, test metrics, split boundaries, uncertainty tables, figures and this report.
Verification recomputes every saved metric, all interval endpoints and development selection, checks source SHA-256,
and compares a fresh complete rerun against committed reference tables. The tests perturb future inputs to detect feature look-ahead.</p>
<p><a href="https://github.com/jiayuyan117/academic-portfolio/tree/main/projects/09-market-direction">Code and reproducibility files on GitHub</a></p></section>
<section id="credit"><h2>Course origin, contributions &amp; AI assistance</h2>
<p>This project grows out of Lab 6, “Traditional Machine Learning in Financial Data Analysis.”
The instructor supplied the original teaching framework: next-day direction classification, logistic/tree/forest examples,
chronological splitting, training-only scaling, K-means/PCA demonstrations and five exercises.
Jiayu Yan's submitted coursework completed those exercises within that framework. The instructor's name was not available in the supplied files.</p>
<p>This public extension uses a new implementation and a different, openly licensed dataset.
The extension adds development-only selection including the baseline, purged rolling evaluation,
probability losses, feature ablations, block-bootstrap sensitivity, reproducibility tests and this English report.
AI assisted research design, coding, execution, analysis, writing and verification. These contributions are not presented as unaided student work.
The original submission remains private and unchanged; neither the instructor's code nor the course dataset is included because redistribution permission was not established.</p>
<p>Original implementation is covered by the repository's MIT license; the source dataset remains CC BY 4.0.
This is an undergraduate portfolio research extension, not a peer-reviewed publication.</p></section>
</main><footer>Jiayu Yan · Evidence before complexity · <a href="../../index.html">Return to portfolio</a></footer></body></html>"""
    (ROOT / "report.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    render()
