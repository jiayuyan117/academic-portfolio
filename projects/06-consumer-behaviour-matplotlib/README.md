# Consumer Transactions: A Segmentation That Isn't There

**The assignment asks which customer groups spend more. On this data, four of five groupings don't differ at all.**

`Python` · `Matplotlib` · `8,000 transactions` · `bootstrap CIs · ANOVA · permutation null`

---

## Headline

The brief is a standard marketing-analytics task: segment customers, rank the
segments, recommend a target. Running the tests first gives a different answer.

| Candidate segmentation | ANOVA *p* | Verdict |
| --- | ---: | --- |
| Age band | 0.445 | no difference |
| Gender | 0.522 | no difference |
| City tier | 0.773 | no difference |
| Payment method | 0.896 | no difference |
| **Membership tier** | **1.0 × 10⁻⁶** | **separates** |

![Segmentation audit](figures/01_segmentation_effect_audit.png)

Four of the five variables a segmentation deck would be built on carry no
information about spending. The ranked bar charts that the original assignment
produced for age band were ranking noise — the highest and lowest age-group means
differ by 11% of the overall mean, and their confidence intervals overlap.


## The null results are precise, not merely absent

With roughly 8,000 observations, "no relationship" is a measurement rather than a
shrug:

| Variable | *r* with amount | 95% CI |
| --- | ---: | --- |
| Monthly income | −0.010 | [−0.032, +0.012] |
| Age | −0.001 | [−0.023, +0.021] |
| Discount rate | +0.003 | [−0.019, +0.025] |
| Rating | +0.014 | [−0.008, +0.036] |
| Quantity | +0.372 | [+0.353, +0.391] |
| Unit price | +0.762 | [+0.753, +0.771] |


The income interval is narrow enough to rule out any association stronger than
0.032. "Weak but present" would therefore be the wrong description — the data
says *absent*, and says it tightly. A discount rate with no relationship to
amount is a particularly strong hint about how this dataset was constructed.

![Correlation forest](figures/02_correlation_forest.png)

## What transaction value actually is here

Amount is essentially the basket arithmetic: regressed on
`price × quantity × (1 − discount)` it gives **R² = 0.878**, *r* = 0.937. The
ratio of recorded amount to that expectation clusters on a few discrete
multipliers (median 1.000, upper quartile 1.100), consistent with a shipping or
service tier rather than any customer decision.

So the variance in this dataset lives in *what was bought*, not in *who bought
it*. That framing is the finding.

![Basket identity](figures/03_basket_identity.png)

## The one real effect, with its caveat attached

Membership tier does separate spending, and it survives scrutiny: ANOVA
*p* = 1.0 × 10⁻⁶ against a Bonferroni threshold of 0.05/5, and
*p* = 1.6 × 10⁻⁹ on 10% trimmed means — so it is a shift of the whole
distribution, not a handful of large orders. Mean amount rises from ¥1,338
(Standard) to ¥1,579 (Platinum), and it runs through unit price (median ¥349 →
¥373) and a higher share of large orders (10.8% → 15.5% above ¥3,000), with mean
basket size flat at 3.0 items.

**Direction is not identified.** Loyalty tiers are normally awarded *for* past
spending, so this result is as consistent with reverse causality as with a tier
effect. Nothing here supports "upgrade customers to increase spend".

![Membership](figures/05_membership_effect.png)

## And there is no seasonality either

Monthly revenue looks like it has a shape. Holding each month's order count fixed
and permuting which amounts land in which month, 500 times, produces a 95% range
that contains **all 12** observed months. Any seasonal narrative fitted to this
series would be fitting noise.

![Monthly trend](figures/07_monthly_trend_vs_noise.png)

## About this dataset

The structure is consistent with a dataset built for a data-cleaning exercise
rather than collected from a live system: exactly **15** missing values in exactly
three columns (`income`, `payment`, `rating`), exactly **20** duplicate rows, and
dates spanning exactly 2025-01-01 to 2025-12-31. The defects are recorded before
they are fixed, and duplicates are removed (8,020 → 8,000 rows).

That provenance is stated plainly because it bounds what the analysis can mean.
The transferable work is not a claim about real shoppers — it is the discipline
of testing a segmentation before presenting it, and reporting a precise null
instead of manufacturing a ranking.

## Reproduce

```bash
pip install -r requirements.txt
python src/analyze.py
```

Writes `figures/*.png`, the tables in `outputs/`, and `outputs/findings.json` —
every number quoted above comes from that file. Bootstrap and permutation draws
use a fixed seed, so results are reproducible exactly.

## Contents

- `src/analyze.py` — the whole pipeline, documented
- `figures/` — seven figures, 200 dpi
- `outputs/` — segmentation tests, group means with intervals, correlation
  intervals, membership detail, category revenue, monthly null band, plus
  `findings.json`
- `data/consumer_transactions.csv` — the source data, unmodified
- `source_materials/` — the original coursework script, the assignment brief and
  the field dictionary

## Provenance

Course-supplied teaching dataset for a Matplotlib visualisation assignment; its
origin and generating process were not documented with it, and no upstream vendor
is claimed. Developed from my own coursework submission, which is retained in
`source_materials/` for comparison. The hypothesis tests, confidence intervals,
permutation null and the decision not to rank the null segmentations are changes
I made for this portfolio version. AI assistance was used for code structuring
and English writing; the analytical decisions and all interpretation are my own.
