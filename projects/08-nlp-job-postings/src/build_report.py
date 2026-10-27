"""Generate English figures and a standalone brief from executed evidence."""
import csv
import hashlib
import html
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

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
:root{{--ink:#142834;--body:#354b58;--muted:#536775;--accent:#156b70;--accent-soft:#e6f2f1;--amber:#9a6220;--amber-soft:#f9f1e6;--paper:#fbfaf6;--surface:#ffffff;--line:#d5e0e2;--radius:10px}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--body);font:16.5px/1.72 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}}
.topbar{{background:rgba(251,250,246,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10}}
.topbar nav{{max-width:1080px;margin:auto;padding:14px 28px;display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;font-size:.9rem}}
.nav-links{{display:flex;gap:20px;flex-wrap:wrap}}
main{{max-width:1080px;margin:auto;padding:42px 28px 88px;overflow-wrap:anywhere}}a{{color:var(--accent);text-decoration:none;font-weight:500}}a:hover{{text-decoration:underline}}
a:focus-visible{{outline:3px solid #b87b38;outline-offset:4px}}
.eyebrow{{display:inline-block;text-transform:uppercase;letter-spacing:.12em;font-size:.76rem;font-weight:700;color:var(--accent);background:var(--accent-soft);padding:4px 10px;border-radius:999px;margin:10px 0 14px}}
h1{{font:700 clamp(2.3rem,5.5vw,4rem)/1.1 Georgia,serif;color:var(--ink);letter-spacing:-.025em;max-width:820px;margin:0 0 18px}}
h2{{font:700 1.65rem/1.3 Georgia,serif;color:var(--ink);margin:52px 0 16px;padding-bottom:8px;border-bottom:1px solid var(--line)}}
.intro{{font-size:1.18rem;max-width:76ch;color:var(--ink);margin:0 0 28px}}
.facts{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:28px 0}}
.fact{{padding:18px 20px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);box-shadow:0 6px 20px rgba(20,40,52,.04)}}
.fact strong{{display:block;font:700 1.65rem/1.15 Georgia,serif;color:var(--ink);margin-bottom:4px}}
.fact span{{font-size:.86rem;color:var(--muted)}}
.result{{border-left:4px solid var(--amber);padding:20px 24px;background:var(--amber-soft);border-radius:0 var(--radius) var(--radius) 0;margin:28px 0;color:var(--ink)}}
.grid-2{{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr);gap:22px;align-items:start;margin:24px 0}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:20px 22px}}
figure{{margin:26px 0;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:16px;box-shadow:0 6px 20px rgba(20,40,52,.04)}}
img{{width:100%;height:auto;display:block;border-radius:6px}}
figcaption{{font-size:.86rem;color:var(--muted);padding:10px 4px 2px}}
table{{width:100%;border-collapse:collapse;font-size:.93rem;background:var(--surface)}}
th,td{{padding:10px 14px;border-bottom:1px solid var(--line);text-align:left}}
th{{background:#f1f5f5;color:var(--ink);font-weight:600}}
.table{{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius);margin:18px 0}}
.note{{font-size:.9rem;color:var(--muted)}}
code{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.88em;background:#eaf0f0;color:var(--ink);padding:2px 6px;border-radius:4px}}
pre{{overflow-x:auto;padding:18px 20px;background:#142834;color:#e8f1f2;border-radius:var(--radius);font-size:.9rem}}
pre code{{background:none;color:inherit;padding:0}}
.sim-box{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:20px 22px;margin:24px 0}}
.sim-tabs{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}}
.sim-btn{{border:1px solid var(--line);background:var(--paper);color:var(--ink);padding:6px 12px;border-radius:6px;font-size:.85rem;font-weight:600;cursor:pointer;min-height:44px}}
.sim-btn:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}
.sim-btn.active{{background:var(--accent);border-color:var(--accent);color:#fff}}
footer{{margin-top:56px;border-top:1px solid var(--line);padding-top:22px;color:var(--muted);font-size:.88rem}}
@media(max-width:760px){{main{{padding:24px 18px 50px}}.facts,.grid-2{{grid-template-columns:1fr}}.fact strong{{font-size:1.4rem}}}}
@media print{{body{{background:white}}main{{padding:0}}.topbar{{display:none}}figure,.result{{break-inside:avoid}}}}
</style></head><body>
<header class="topbar"><nav aria-label="Research navigation">
<strong>08 · Job-Posting NLP Evaluation Brief</strong>
<div class="nav-links"><a href="../../index.html">← Portfolio</a>
<a href="https://github.com/jiayuyan117/academic-portfolio/tree/main/projects/08-nlp-job-postings">Code &amp; documentation</a>
<a href="results/metrics.json">Machine-readable results</a></div></nav></header>
<main>
<span class="eyebrow">08 / Natural language processing · Reproducible research brief</span>
<h1>Does the skill signal help?</h1>
<p class="intro">Classifying a job advertisement and extracting its exact skill requirements answer different operational questions.
This study tests a Skill + Knowledge phrase lexicon against a full-text TF-IDF baseline under strict employer isolation,
then evaluates exact-span BIO extraction and representation budgets separately.</p>

<div class="facts">
<div class="fact"><strong>21,663</strong><span>SEEK postings · 20 categories</span></div>
<div class="fact"><strong>0 overlap</strong><span>normalized employer groups across splits</span></div>
<div class="fact"><strong>2,757</strong><span>held-out SkillSpan sentences (65 job clusters)</span></div>
<div class="fact"><strong>22,213</strong><span>verified public source references &amp; SHA-256 ledger</span></div>
</div>

<div class="result"><strong>Measured conclusion.</strong> {conclusion}
The current fusion-minus-text difference is <b>{hypothesis['delta_macro_f1']:+.4f}</b> Macro-F1
(Text: <b>{summary['classification']['macro_f1']['text']:.4f}</b>, Lexicon: <b>{summary['classification']['macro_f1']['lexicon']:.4f}</b>, Fusion: <b>{summary['classification']['macro_f1']['fusion']:.4f}</b>),
with employer-cluster 95% bootstrap interval <b>[{lo:+.4f}, {hi:+.4f}]</b> across {hypothesis['clusters']:,} test employer clusters.
The recorded study threshold is +0.02. An inconclusive interval is not proof of zero effect.</div>

<h2>01 · Define the decision before the model</h2>
<div class="grid-2">
<div>
<p>A job platform needs a reliable taxonomy for routing; a careers service needs interpretable skill requirements.
A dictionary can match frequent phrases without adding category-discriminative signal, and a correct category label
does not validate an extracted skills profile.</p>
<p>Classification uses the archived employer-isolated train/validation/test partitions. Normalized employer groups do not overlap; this does not rule out shared boilerplate between different employers. Task-specific vocabulary is fit on training data, regularization is selected on validation data, and the three feature sets share 2,944 test postings. MiniLM uses a pretrained frozen encoder. The +0.02 threshold exists in supplied code; no independently timestamped preregistration was provided.</p>
</div>
<div class="card">
<strong>Classification Feature Matrix Design</strong>
<ul style="margin:10px 0 0;padding-left:18px;font-size:.92rem">
<li><b>Text baseline:</b> Word (1–2 gram) + char_wb (3–5 gram) TF-IDF, sublinear TF, linear SVM.</li>
<li><b>Lexicon channel:</b> Trie-matched phrase counts from training SkillSpan Skill &amp; Knowledge spans + summary density features.</li>
<li><b>Equal-weight fusion:</b> Horizontal feature concatenation evaluated on identical employer clusters.</li>
</ul>
</div>
</div>
<figure><img src="results/ablation.png" alt="Current Macro-F1 for text, Skill plus Knowledge lexicon, and fusion" width="1980" height="1034">
<figcaption>Figure 1 · Full-data rerun on 2,944 held-out postings. Phrase matches are counts from both SkillSpan channels, not predictions from the contextual extractor.</figcaption></figure>

<h2>02 · Evaluate explanations directly (Exact-Span BIO Extraction)</h2>
<p>Skill and Knowledge are separate BIO annotation channels in SkillSpan. Exact-span evaluation requires both start and end token boundaries to match gold annotations. Sentences seen verbatim in training are removed from dev/test before scoring, and confidence intervals resample 65 job-posting clusters rather than treating sentences as independent.</p>
<figure><img src="results/extraction.png" alt="Precision recall and F1 for two separate span extraction channels" width="2420" height="990">
<figcaption>Figure 2 · Current run under a fixed 300-iteration logistic-regression budget. Fits reached the iteration limit, so optimizer convergence is not certified.</figcaption></figure>
<div class="table"><table><thead><tr><th>Channel</th><th>Method</th><th>Precision</th><th>Recall</th><th>Exact-Span F1</th></tr></thead>
<tbody>{extraction_rows}</tbody></table></div>
<ul>{interval_rows}</ul>
<p class="note">These are exploratory intervals without multiplicity correction. Rerun scores differ
from historical paper values (context F1: Skill 0.1185; Knowledge 0.4217); both are retained in <code>results/metrics.json</code>.
The fixed optimization budget and environment sensitivity are disclosed.</p>

<div class="sim-box">
<strong>Interactive Task-Separation Explorer · Why Category Routing ≠ Span Extraction</strong>
<p class="note" style="margin:6px 0 12px">These invented examples explain evaluation questions. They are not inspected predictions or established explanations for the measured score differences.</p>
<div class="sim-tabs">
<button class="sim-btn active" type="button" onclick="showCase(0, this)">Case A: Generic Professional Verbs (Skill Channel)</button>
<button class="sim-btn" type="button" onclick="showCase(1, this)">Case B: Domain Technical Nouns (Knowledge Channel)</button>
<button class="sim-btn" type="button" onclick="showCase(2, this)">Case C: Employer Boilerplate Leakage Risk</button>
</div>
<div id="case-body" style="font-size:.93rem;background:var(--paper);padding:14px 16px;border-radius:8px;border:1px solid var(--line)">
<b>Illustrative hypothesis:</b> A phrase such as <code>"collaborate with stakeholders"</code> could occur in several categories. A match need not distinguish categories. Testing whether generic phrases explain the fusion result requires a targeted ablation; none is claimed here.
</div>
</div>

<h2>03 · Put model scores in context</h2>
<p>{html.escape(comparison_note)}. TF-IDF uses full descriptions; CNN and MiniLM use truncated inputs (256 tokens/subwords).
The three-epoch CNN and frozen encoder are budgeted comparisons on shared sample IDs, not exhaustive architecture tuning.</p>
<figure><img src="results/model_compare.png" alt="Representation comparison with explicit provenance" width="1980" height="990">
<figcaption>Figure 3 · Common evaluation design; different length and compute budgets limit broad model-family conclusions.</figcaption></figure>

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
<footer>Original coursework independently completed by 闫佳玉 / Jiayu Yan.
Portfolio refinements used AI for analysis design, code, interpretation, writing, translation and verification.
This is not a peer-reviewed publication. Detailed methods, data rights and attribution are in the repository.</footer>
</main>
<script>
const CASES = [
  '<b>Illustrative hypothesis:</b> A phrase such as <code>"collaborate with stakeholders"</code> could occur in several categories. A match need not distinguish categories. Testing whether generic phrases explain the fusion result requires a targeted ablation; none is claimed here.',
  '<b>Illustrative hypothesis:</b> A token such as <code>"SQL"</code> may be represented by both a phrase lexicon and text TF-IDF. Aggregate scores do not establish redundancy or easier boundaries as the mechanism. Inspect held-out span errors and conduct feature ablations before making that claim.',
  '<b>Design rationale:</b> Repeated employer wording could inflate a random-split score. Employer-disjoint evaluation limits that risk, but no random-versus-grouped split experiment is reported and normalization cannot guarantee distinct real-world organizations.'
];
function showCase(idx, btn) {{
  document.getElementById('case-body').innerHTML = CASES[idx];
  document.querySelectorAll('.sim-btn').forEach(b => {{
    b.classList.remove('active');
    b.setAttribute('aria-pressed', String(b === btn));
  }});
  btn.classList.add('active');
}}
document.querySelectorAll('.sim-btn').forEach(b => b.setAttribute('aria-pressed', String(b.classList.contains('active'))));
</script>
</body></html>"""
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
