# Methods, evidence levels and interpretation

## Primary ablation

Train a word 1–2 gram TF-IDF representation on training descriptions only:
`min_df=3`, `max_df=.98`, maximum 100,000 features, sublinear term frequency
and row L2 normalization. Separately, combine SkillSpan training Skill and
Knowledge labelled phrases into a case-insensitive, longest, non-overlapping
whole-word lexicon. Apply `log1p` to its counts and normalize each row.

Fit LinearSVC to text, lexicon and sparse concatenation (lexicon weight 1).
Select `C` from 0.1, 1 and 10 by validation Macro-F1. Evaluate all three on
the same 2,944 employer-isolated test postings. The archived split is retained,
not reselected in response to performance.

For fusion minus text, resample employer clusters with replacement 1,000 times,
using the same weights for both sets of predictions and a fixed 20-label
Macro-F1 definition. Report the percentile 95% interval, observed difference
and the supplied code's +0.02 decision threshold. A claim of practical gain
requires both a difference ≥0.02 and a positive interval lower bound.

The paper says the threshold preceded test inspection. No independently
timestamped protocol accompanies the package, so this is described as a
**recorded study criterion**, not independently verified preregistration.

## Extraction and optimization budget

Fit separate token-context logistic regressions for Skill and Knowledge:
word, neighbouring words, word pairs, prefixes/suffixes, capitalization,
numeric indicators and clipped word length. Preserve the source study's
`C=1`, `max_iter=300`, L-BFGS and seed 42. Compare with training-only exact
phrase lexicons. Convert BIO outputs into half-open token spans; an orphan
`I` begins a span, consistently with the supplied implementation.

The 300-iteration budget can produce convergence warnings. These models are
reported as **budget-limited fits**, not certified optimizer convergence.
Different numerical environments can alter boundary predictions. Current
rerun scores and the source paper's scores remain separate; neither is
silently substituted for the other. No iteration count is selected using
test performance.

An exact match requires the same sentence, channel, start and end. Estimate
context-minus-lexicon F1 intervals by paired resampling of 65 test job groups.
The two intervals are exploratory and do not have a multiplicity correction.
The same entity may receive labels in both channels; they are not a mutually
exclusive hard-skill/soft-skill classifier.

## Representation comparison

The source design uses stratified subsets of 12,000 training and 2,000
validation rows, with the original 2,944 test rows. Sample IDs are saved.
TF-IDF consumes complete descriptions; the CNN uses the first 256 words;
MiniLM uses at most 256 subword tokens. The CNN trains for a fixed three
epochs; MiniLM is frozen and uses attention-mask mean pooling followed by L2
normalization and a validation-selected logistic regression.

The pinned MiniLM revision is
`c9745ed1d9f207416be6d2e6f8de32d1f16199bf`. The comparison measures these
particular configurations and budgets. It does not establish that linear
models generally outperform neural models.

## Evidence levels

- **Source-checked:** fixed downloads, byte hashes, normalized source-row matches,
  delivered split membership and SkillSpan token/tag fidelity.
- **Rerun:** newly trained models with saved predictions and recorded package
  versions. Current metrics are generated from those predictions.
- **Prediction-verified:** independent recomputation of metrics and intervals;
  it does not prove that stored predictions were produced by the named model.
- **Paper-reported:** historical scores where original run artifacts are absent,
  especially JobStreet. They are clearly labelled and excluded from a claim of
  complete external reproduction.

No label or source metadata establishes a causal mechanism. Differences across
platforms combine changes in location, time, labels and text distributions.
