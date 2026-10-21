"""Generate English figures and a standalone brief from executed evidence."""
import csv
import html
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from skill_extraction import load, save, digest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
COLORS = ("#194d68", "#b87b38", "#387f7c")


def main():
    classification = load(RESULTS / "classification/summary.json")
    with (RESULTS / "extraction/metrics.csv").open(encoding="utf-8", newline="") as stream:
        extraction = [{**row, **{k: float(row[k]) for k in ("precision", "recall", "f1")}}
                      for row in csv.DictReader(stream) if row["split"] == "test"]
    intervals = load(RESULTS / "extraction/paired_intervals.json")
    comparison = {}
    for name in ("fair_tfidf", "cnn", "minilm"):
        config = RESULTS / "comparison" / name / "run_config.json"
        if config.exists() and load(config)["status"] == "completed":
            comparison[name] = load(config.parent / "metrics.json")["test"]["macro_f1"]
    summary = {
        "classification": {
            "macro_f1": {name: result["macro_f1"] for name, result in classification["results"].items()},
            "hypothesis": classification["hypothesis"], "evidence": "Full-cohort rerun with saved predictions",
        },
        "extraction": {"test": extraction, "intervals": intervals,
                       "optimization": load(RESULTS / "extraction/optimization.json")},
        "model_comparison": {"rerun_macro_f1": comparison,
                             "budget_note": "Shared sample IDs; TF-IDF full text, CNN 256 words, MiniLM 256 subwords"},
        "paper_reported": {
            "evidence": "Historical paper values; not substituted for this rerun",
            "ablation": {"text": 0.7406, "lexicon": 0.5003, "fusion": 0.7348},
            "model_comparison": {"fair_tfidf": 0.7272, "cnn": 0.3679, "minilm": 0.6705},
            "extraction_f1": {"skill_lexicon": 0.1001, "skill_context": 0.1185,
                              "knowledge_lexicon": 0.2120, "knowledge_context": 0.4217},
            "jobstreet": {"text_macro_f1": 0.5784, "fusion_macro_f1": 0.5507,
                           "delta": -0.0277, "ci95": [-0.0358, -0.0191],
                           "status": "Not rerun: external CSV and archived exclusion index not supplied"},
        },
    }
    save(RESULTS / "metrics.json", summary)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold"})
    names = ["Text TF-IDF", "Skill + Knowledge\nlexicon", "Fusion"]
    values = [summary["classification"]["macro_f1"][name] for name in ("text", "lexicon", "fusion")]
    fig, ax = plt.subplots(figsize=(9, 4.7))
    bars = ax.bar(names, values, color=COLORS, width=.62)
    ax.bar_label(bars, labels=[f"{v:.4f}" for v in values], padding=5)
    ax.set(ylim=(0, .9), ylabel="Macro-F1", title="A lexicon does not automatically add classification value")
    ax.grid(axis="y", alpha=.18)
    ax.set_axisbelow(True)
    fig.text(.5, .02, "Same 2,944-posting employer-isolated test set; current full-data rerun", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.savefig(RESULTS / "ablation.png", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for axis, channel in zip(axes, ("skill", "knowledge")):
        for i, (method, label) in enumerate((("train_lexicon", "Training lexicon"), ("context_BIO_LR", "Context BIO LR"))):
            row = next(r for r in extraction if r["channel"] == channel and r["method"] == method)
            bars = axis.bar(np.arange(3) + (i - .5) * .36,
                            [row[k] for k in ("precision", "recall", "f1")], width=.36, color=COLORS[i], label=label)
            axis.bar_label(bars, labels=[f"{row[k]:.3f}" for k in ("precision", "recall", "f1")], padding=3, fontsize=9)
        axis.set(xticks=np.arange(3), xticklabels=["Precision", "Recall", "F1"], ylim=(0, .72), title=channel.title())
        axis.grid(axis="y", alpha=.18)
        axis.set_axisbelow(True)
    axes[0].legend(frameon=False)
    fig.text(.5, .015, "Exact spans; 2,757 test sentences / 65 job groups; fixed 300-iteration context-model budget",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .06, 1, 1))
    fig.savefig(RESULTS / "extraction.png", dpi=220)
    plt.close(fig)

    if comparison:
        labels = {"fair_tfidf": "TF-IDF + SVM", "cnn": "TextCNN", "minilm": "Frozen MiniLM + LR"}
        fig, ax = plt.subplots(figsize=(9, 4.5))
        bars = ax.bar([labels[n] for n in comparison], list(comparison.values()), color=COLORS[:len(comparison)], width=.62)
        ax.bar_label(bars, labels=[f"{value:.4f}" for value in comparison.values()], padding=4)
        ax.set(ylim=(0, .9), ylabel="Macro-F1", title="Representation comparison under explicit compute budgets")
        fig.text(.5, .02, "Current reruns only; common sample IDs, unequal text-length and training budgets", ha="center", fontsize=9)
        fig.tight_layout(rect=(0, .06, 1, 1))
        fig.savefig(RESULTS / "model_compare.png", dpi=220)
        plt.close(fig)
    else:
        # A clearly labelled historical chart is useful without implying a rerun.
        fig, ax = plt.subplots(figsize=(9, 4.5))
        values_reported = list(summary["paper_reported"]["model_comparison"].values())
        bars = ax.bar(["TF-IDF + SVM", "TextCNN", "Frozen MiniLM + LR"], values_reported, color=COLORS)
        ax.bar_label(bars, labels=[f"{v:.4f}" for v in values_reported], padding=4)
        ax.set(ylim=(0, .9), ylabel="Macro-F1", title="Paper-reported comparison — not rerun evidence")
        fig.tight_layout()
        fig.savefig(RESULTS / "model_compare.png", dpi=220)
        plt.close(fig)

    hypothesis = classification["hypothesis"]
    lo, hi = hypothesis["ci95"]
    extraction_rows = "".join(
        f"<tr><td>{r['channel'].title()}</td><td>{'Lexicon' if r['method']=='train_lexicon' else 'Context BIO'}</td>"
        f"<td>{r['precision']:.4f}</td><td>{r['recall']:.4f}</td><td>{r['f1']:.4f}</td></tr>"
        for r in extraction)
    interval_rows = "".join(
        f"<li><b>{name.title()}:</b> ΔF1 {v['delta_f1_context_minus_lexicon']:+.4f}; "
        f"95% interval [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}].</li>" for name, v in intervals.items())
    comparison_note = (
        "Current reruns: " + "; ".join(f"{n}: {v:.4f}" for n, v in comparison.items())
        if comparison else "The chart below contains historical paper-reported values, not independently rerun results."
    )
    conclusion = ("The criterion for a practically meaningful improvement is met in this run."
                  if hypothesis["threshold_and_interval_pass"] else
                  "This equal-weight lexicon fusion does not meet the study’s criterion for a meaningful improvement.")
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="An auditable NLP coursework study: employer-isolated classification and exact-span extraction.">
<title>Does the Skill Signal Help? | Jiayu Yan</title>
<style>
:root{{--ink:#183747;--muted:#536775;--accent:#176d72;--paper:#fbfaf6;--line:#dbe3e5}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:17px/1.7 system-ui,sans-serif}}
main{{max-width:1040px;margin:auto;padding:36px 28px 80px}}a{{color:var(--accent);text-underline-offset:4px}}
a:focus-visible{{outline:3px solid #b87b38;outline-offset:4px}}nav{{display:flex;gap:22px;flex-wrap:wrap;font-size:.9rem}}
.eyebrow{{text-transform:uppercase;letter-spacing:.13em;font-size:.78rem;color:var(--accent);margin-top:52px}}
h1{{font:600 clamp(2.4rem,6vw,4.3rem)/1.12 Georgia,serif;max-width:800px;margin:18px 0}}h2{{font:600 1.8rem/1.3 Georgia,serif;margin-top:48px}}
.intro{{font-size:1.2rem;max-width:820px;color:var(--muted)}}.facts{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:32px 0}}
.fact{{padding:20px;border:1px solid var(--line);background:white}}.fact strong{{display:block;font-size:1.8rem}}
.result{{border-left:4px solid var(--accent);padding:20px 24px;background:#eaf2f0;margin:28px 0}}
figure{{margin:28px 0;background:white;border:1px solid var(--line);padding:12px}}img{{width:100%;height:auto;display:block}}
figcaption{{font-size:.85rem;color:var(--muted);padding:8px 12px}}table{{width:100%;border-collapse:collapse;font-size:.94rem}}
th,td{{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left}}.table{{overflow-x:auto}}
.note{{font-size:.92rem;color:var(--muted)}}code{{font-size:.9em;background:#eef1f1;padding:2px 5px}}pre{{overflow-x:auto;padding:18px;background:#eef1f1}}
footer{{margin-top:50px;border-top:1px solid var(--line);padding-top:20px;color:var(--muted);font-size:.9rem}}
@media(max-width:600px){{main{{padding:24px 18px 50px}}.facts{{grid-template-columns:1fr}}.fact strong{{font-size:1.4rem}}}}
@media print{{body{{background:white}}main{{padding:0}}nav{{display:none}}figure,.result{{break-inside:avoid}}}}
</style></head><body><main>
<nav aria-label="Research navigation"><a href="../../index.html">← Portfolio</a>
<a href="https://github.com/jiayuyan117/academic-portfolio/tree/main/projects/08-nlp-job-postings">Code &amp; documentation</a>
<a href="results/metrics.json">Machine-readable results</a></nav>
<p class="eyebrow">08 / Natural language processing · Research brief</p>
<h1>Does the skill signal help?</h1>
<p class="intro">Classifying a job and explaining its requirements are different tasks.
This study tests a Skill + Knowledge phrase lexicon against a strong text baseline,
then evaluates extraction boundaries separately.</p>
<div class="facts"><div class="fact"><strong>21,663</strong>SEEK postings · 20 categories</div>
<div class="fact"><strong>0 overlap</strong>normalized employer groups across splits</div>
<div class="fact"><strong>2,757</strong>held-out SkillSpan sentences</div></div>
<div class="result"><strong>Measured conclusion.</strong> {conclusion}
The current fusion-minus-text difference is <b>{hypothesis['delta_macro_f1']:+.4f}</b> Macro-F1,
with employer-cluster 95% interval <b>[{lo:+.4f}, {hi:+.4f}]</b>.
The recorded study threshold is +0.02. An inconclusive interval is not proof of zero effect.</div>
<h2>01 · Define the decision before the model</h2>
<p>A job platform needs a reliable taxonomy; a careers service needs interpretable requirements.
A dictionary can match common terms without adding category information, and a correct category
does not validate an extracted skills profile.</p>
<p>Use the original employer-isolated train/validation/test partitions. Fit vocabulary and
representations on training data, select regularization on validation data, and compare the
three feature sets on the same test postings. The +0.02 threshold exists in the supplied code;
no independently timestamped preregistration was provided.</p>
<figure><img src="results/ablation.png" alt="Current Macro-F1 for text, Skill plus Knowledge lexicon, and fusion">
<figcaption>Full-data rerun. Phrase matches are counts from both SkillSpan channels, not predictions from the contextual extractor.</figcaption></figure>
<h2>02 · Evaluate explanations directly</h2>
<p>Skill and Knowledge are separate BIO annotation channels. Exact-span scoring requires both
boundaries to match. Sentences seen verbatim in training are excluded from validation and test;
intervals resample test jobs rather than treating every sentence as an independent advertisement.</p>
<figure><img src="results/extraction.png" alt="Precision recall and F1 for two separate span extraction channels">
<figcaption>Current run; fixed 300-iteration logistic-regression budget. Fits reached the iteration limit, so optimizer convergence is not certified.</figcaption></figure>
<div class="table"><table><thead><tr><th>Channel</th><th>Method</th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead>
<tbody>{extraction_rows}</tbody></table></div><ul>{interval_rows}</ul>
<p class="note">These are exploratory intervals without multiplicity correction. Rerun scores differ
from historical paper values (context F1: Skill 0.1185; Knowledge 0.4217); both are retained in metrics.json.
The fixed optimization budget and environment sensitivity are disclosed.</p>
<h2>03 · Put model scores in context</h2>
<p>{html.escape(comparison_note)}. TF-IDF uses full descriptions; CNN and MiniLM use truncated inputs.
The three-epoch CNN and frozen encoder are budgeted comparisons, not exhaustive model tuning.</p>
<figure><img src="results/model_compare.png" alt="Representation comparison with explicit provenance">
<figcaption>Common evaluation design; different length and compute budgets limit broad model-family conclusions.</figcaption></figure>
<h2>04 · What would change a practical decision?</h2>
<p>Retain the text baseline for broad-category routing until a new feature design clears a relevant
gain criterion. Use extracted requirements as source-linked candidates for human review, not as
automatic judgments about a person's competence or suitability.</p>
<p>A next study could filter generic terms using training data, tune fusion weights on validation
data, and reserve a new employer/time holdout for one final comparison. Those experiments
have not been performed here.</p>
<h2>Evidence and limits</h2>
<p>The downloader rebuilds the archived cohort from fixed public releases and checks 22,213 source
references. The selection ledger preserves the delivered membership; it does not recover the
missing original split-generation script. Historical English advertisements do not represent
current US, Singapore or Hong Kong hiring.</p>
<p>The paper reports an exploratory JobStreet fusion decline, but its full CSV and archived
exclusion index were not supplied and its card has conflicting licenses. This release does not
claim to reproduce that external experiment.</p>
<pre><code>python run.py verify
python run.py smoke
python run.py data
python run.py reproduce</code></pre>
<footer>Team coursework credited to 闫佳玉 (Jiayu Yan), 凌泳婷 and 王安娜; supervisor 梁沛.
English portfolio integration and verification used AI assistance.
This is not a peer-reviewed publication. Detailed methods, data rights and attribution are in the repository.</footer>
</main></body></html>"""
    (ROOT / "report.html").write_text(page, encoding="utf-8")
    paths = [p for p in RESULTS.rglob("*") if p.is_file() and p.name != "manifest.json"]
    paths += [ROOT / "data/cohort.jsonl.gz", ROOT / "data/sources.json", ROOT / "report.html"]
    save(RESULTS / "manifest.json", {
        "scope": "Committed predictions, derived metrics, figures, source metadata and report",
        "sha256": {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(paths)},
    })
    print("Generated figures, research brief, metrics and artifact manifest")


if __name__ == "__main__":
    main()
