# Consumer Transactions: Evidence for a Segmentation Decision

**8,020 raw rows → remove 20 exact duplicates →
8,000 analysed transactions. Non-significance does not prove equality.**

`Python` · `Matplotlib` · `ANOVA / Welch / Kruskal-Wallis / trimmed means`

## Business question and metric

Should a marketing team prioritise a demographic segment or a membership offer?
The primary metric here is **mean recorded amount per transaction** (sum of amount
divided by included transactions), relevant to revenue per order. Median amount
describes a typical order; a 10%-per-tail trimmed mean describes the central 80%.
These are different estimands. None measures margin, conversion, purchase frequency
or lifetime value. The unit is a transaction, not a customer.

## Evidence and statistical scope

The table uses the 8,000 deduplicated transactions, dropping
missing labels separately for each grouping; `n` is the included count.
4 of 5 primary ANOVA hypotheses are
not rejected at Bonferroni 0.05/5 = 0.01. This does not prove no difference or
establish that any segment is commercially equivalent.

| Grouping | n | ANOVA p | ANOVA adjusted p | Welch p | Kruskal-Wallis p | Trimmed Welch-Yuen p | Primary decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Age band | 8,000 | 0.445 | 1 | 0.363 | 0.693 | 0.542 | not rejected |
| Gender | 8,000 | 0.522 | 1 | 0.523 | 0.783 | 0.938 | not rejected |
| City tier | 8,000 | 0.773 | 1 | 0.773 | 0.303 | 0.58 | not rejected |
| Payment method | 7,985 | 0.896 | 1 | 0.892 | 0.439 | 0.722 | not rejected |
| Membership tier | 8,000 | 1.04e-06 | 5.2e-06 | 1.33e-05 | 0.000112 | 0.000355 | reject equal means (nominal) |

**These are nominal, exploratory transaction-level tests.** There are
3,997 unique user IDs and
2,372 IDs with repeated transactions.
Independence is therefore unverified; no customer-cluster correction is implemented.
P-values and confidence intervals must not be treated as calibrated customer-level
evidence or as causal estimates.

- **ANOVA** asks whether arithmetic means are equal. The classical F reference
  assumes independent errors, common within-group variance and normal errors for
  exact finite-sample inference. Large groups can help the mean approximation under
  finite variance, but do not remove skew, heteroskedasticity or dependence.
  Group sizes, variance ratios and median-centred Levene (Brown-Forsythe) p-values
  are exported as diagnostics; a non-significant diagnostic does not prove assumptions.
- **Welch ANOVA** also targets means and relaxes equal variances. Its p-value is an
  approximation and it still requires independent observations.
- **Kruskal-Wallis** is a rank-based test of equality of group distributions.
  A location/median interpretation requires comparable distribution shapes;
  different spread or shape can change the result. It is not a robust test of
  the same arithmetic-mean null.
- **Welch-Yuen** tests equality of 10%-per-tail trimmed means using winsorised
  variances and retained sample sizes. It checks sensitivity to extremes and
  changes the estimand; it does not prove a shift of the entire distribution.
- **Multiplicity:** the five primary ANOVA tests form one Bonferroni family.
  Each sensitivity family also has five-test adjusted p-values in the CSV, but
  there is no joint correction over all methods. Sensitivity checks are exploratory,
  not extra opportunities to declare a discovery. Omnibus rejection does not
  identify which tiers differ; no pairwise comparisons are claimed.
- **Intervals:** bootstrap mean intervals and Fisher-z correlation intervals are
  pointwise and assume independent observations. They are not simultaneous,
  cluster-adjusted or pairwise difference intervals. Overlap is not a hypothesis test.

![Segmentation audit](figures/01_segmentation_effect_audit.png)

## Linear associations and basket arithmetic

| Variable | Pairwise-complete n | Pearson r | Nominal 95% Fisher-z CI |
| --- | ---: | ---: | --- |
| Monthly income | 7,985 | -0.010 | [-0.032, +0.012] |
| Age | 8,000 | -0.001 | [-0.023, +0.021] |
| Discount rate | 8,000 | +0.003 | [-0.019, +0.025] |
| Rating | 7,985 | +0.014 | [-0.008, +0.036] |
| Quantity | 8,000 | +0.372 | [+0.353, +0.391] |
| Unit price | 8,000 | +0.762 | [+0.753, +0.771] |

Near-zero estimates constrain plausible **linear** correlations under the sampling
assumptions. Intervals containing zero do not demonstrate absence of association;
nonlinear patterns, confounding and causal effects remain unresolved.

![Correlation forest](figures/02_correlation_forest.png)

Recorded amount tracks `price × quantity × (1 − discount)` with
r = 0.937, R² = 0.878.
The recorded/expected ratio has median 1.000 and upper
quartile 1.100. Fees or dataset construction rules are hypotheses,
not verified mechanisms. Basket arithmetic does not exclude customer behaviour.

![Basket arithmetic](figures/03_basket_identity.png)
![Amount distribution](figures/04_amount_distribution.png)

## Membership association and commercial meaning

Mean amount is ¥1,338.04 for Standard and
¥1,578.78 for Platinum, a descriptive difference of
¥240.74 per transaction.
Membership omnibus p-values are ANOVA 1.04e-06,
Welch 1.33e-05, Kruskal-Wallis 0.000112 and
trimmed Welch-Yuen 0.000355; they address different nulls.
These are neither an adjusted Standard–Platinum pairwise test nor an upgrade effect.

Membership is a candidate for further investigation, not a reason to spend more
on upgrades. Tier eligibility may depend on prior spending, and the assignment
rule is undocumented. Selection, confounding and reverse causality remain possible.
The top two categories contribute 58.5%
of recorded revenue; inspect their margins and inventory exposure before allocating
budget. Revenue concentration alone does not establish customer preference or profit.

![Membership](figures/05_membership_effect.png)
![Category revenue](figures/06_category_revenue.png)

## Monthly reference and its limits

12 of 12 months lie within
pointwise 95% reference bands from 500 reassignments of amounts while holding each
month's order count fixed. This is not a joint seasonality test and cannot exclude
seasonality in order counts, dependence or smaller effects. Exchangeability is an
assumption; a single teaching-data year is insufficient for a general seasonal policy.

![Monthly reference](figures/07_monthly_trend_vs_noise.png)

## Decision and next experiment — proposed, not performed

1. **Current decision:** do not prioritise demographic targeting solely from these
   unadjusted rankings. Keep membership as a hypothesis and first validate user IDs,
   tier assignment timing, missing labels and the amount definition on production data.
2. **Observational follow-up:** construct customer histories, define a fixed
   follow-up window, audit dependence and selection, and use customer-cluster
   inference. Specify a commercially meaningful effect before any equivalence claim.
3. **Proposed experiment:** randomise eligible customers to a defined membership
   offer or existing experience, stratifying on pre-treatment spending/tier where
   appropriate. Do not infer the offer effect by comparing existing tiers.
4. **Primary decision metric:** incremental contribution margin per randomised
   eligible customer over the pre-specified window, including non-purchasers and
   offer costs. Track conversion, repeat purchase and order value as secondary
   metrics; refunds, unsubscribes and discount expense are guardrails.
5. **Decision rule:** agree a minimum worthwhile margin gain, guardrail limits,
   sample size/power, follow-up period and multiplicity plan before launch. Analyse
   by assigned group (intention to treat); expand only if the interval supports the
   agreed economic threshold and guardrails, otherwise revise or gather more evidence.

No A/B test, random assignment or causal identification was performed in this project.
The current data lacks the cost and eligibility fields needed to estimate that payoff.

## Data provenance and reproducibility

The course-supplied source has **8,020 raw rows**, including
**20 exact duplicate rows**. All reported analyses use the
**8,000 deduplicated transactions**; missing values are not
globally imputed. Raw missing counts: `income`: 15, `payment`: 15, `rating`: 15. Dates span
2025-01-01 to 2025-12-31. The generating process and upstream vendor
are undocumented. Results illustrate an analysis workflow, not real-market claims.

From this project directory, in the centrally prepared Python environment:

```bash
python src/analyze.py
python -m unittest discover -s tests -v
```

The build rewrites seven PNG figures, six CSV tables, `outputs/findings.json` and
this README via `render_readme()`. A seed of 20261013 is reset at each full run;
reproducibility also depends on dependency versions. Reports/PNG figures can be
viewed offline. Original coursework is retained in `source_materials/`; source data
is unmodified. AI assistance was used for code structuring and English writing.
