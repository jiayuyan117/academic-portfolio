"""Consumer transactions: evidence and limits for a segmentation decision.

Input  : data/consumer_transactions.csv (8,020 raw rows -> 8,000 after deduplication)
Output : figures/*.png   seven Matplotlib figures
         outputs/*.csv   the tables behind each figure
         outputs/findings.json, README.md  computed findings and report

Mean transaction amount is the primary estimand. Classical ANOVA is accompanied
by Welch, Kruskal-Wallis and a Welch-Yuen trimmed-mean sensitivity check. These
tests do not all estimate the same thing. Non-rejection does not establish equality.
Repeated user IDs also make transaction-level p-values and intervals nominal:
customer dependence is not corrected by any of these sensitivity checks.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "consumer_transactions.csv"
FIGURES = ROOT / "figures"
OUTPUTS = ROOT / "outputs"

SEED = 20261013
RNG = np.random.default_rng(SEED)
BOOTSTRAP = 2000

INK = "#16222e"
BODY = "#425362"
GRID = "#dde4ea"
MUTED = "#8a99a8"
BLUE = "#1f6fb2"
TEAL = "#179a9a"
AMBER = "#e8a33d"
CORAL = "#d9534f"

# Source labels are Chinese; English labels are used in every figure.
MEMBERSHIP = {"普通": "Standard", "银卡": "Silver", "金卡": "Gold", "铂金": "Platinum"}
MEMBERSHIP_ORDER = ["Standard", "Silver", "Gold", "Platinum"]
CITY = {"一线": "Tier 1", "新一线": "New Tier 1", "二线": "Tier 2", "三线及以下": "Tier 3+"}
CITY_ORDER = ["Tier 1", "New Tier 1", "Tier 2", "Tier 3+"]
GENDER = {"男": "Male", "女": "Female"}
PAYMENT = {"微信支付": "WeChat Pay", "支付宝": "Alipay", "银行卡": "Debit card",
           "信用卡": "Credit card"}
CATEGORY = {"食品": "Food", "服装": "Apparel", "家电": "Appliances", "美妆": "Beauty",
            "数码": "Digital", "家居": "Home", "运动": "Sports"}

plt.rcParams.update({
    "figure.dpi": 110,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "font.family": "DejaVu Sans",
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "text.color": BODY,
    "xtick.color": BODY,
    "ytick.color": BODY,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.7,
    "legend.frameon": False,
})


def load() -> tuple[pd.DataFrame, dict]:
    """Load, translate labels, and record the data defects before fixing them."""
    raw = pd.read_csv(DATA)
    numeric = ["age", "income", "price", "quantity", "discount", "rating", "amount"]
    for column in numeric:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    raw["purchase_date"] = pd.to_datetime(raw["purchase_date"], errors="coerce")

    defects = {
        "rows": int(len(raw)),
        "fields": int(raw.shape[1]),
        "unique_users": int(raw["user_id"].nunique()),
        "missing_by_field": {k: int(v) for k, v in raw.isna().sum().items() if v},
        "duplicate_rows": int(raw.duplicated().sum()),
        "date_min": str(raw["purchase_date"].min().date()),
        "date_max": str(raw["purchase_date"].max().date()),
    }

    df = raw.drop_duplicates().copy()
    defects["rows_after_dedup"] = int(len(df))
    defects["unique_users_after_dedup"] = int(df["user_id"].nunique())
    defects["users_with_multiple_transactions"] = int((df["user_id"].value_counts() > 1).sum())
    df["membership"] = df["membership"].map(MEMBERSHIP)
    df["city_level"] = df["city_level"].map(CITY)
    df["gender"] = df["gender"].map(GENDER)
    df["payment"] = df["payment"].map(PAYMENT)
    df["category"] = df["category"].map(CATEGORY)
    df["age_group"] = pd.cut(df["age"], [17, 25, 35, 45, 55, np.inf],
                             labels=["18-25", "26-35", "36-45", "46-55", "56+"])
    df["month"] = df["purchase_date"].dt.to_period("M").astype(str)
    # Rows missing `amount` would silently drop out of every group mean; none do.
    assert df["amount"].notna().all(), "amount has missing values"
    return df, defects


def mean_ci(values: np.ndarray) -> tuple[float, float, float]:
    """IID percentile bootstrap CI; neither tail-proof nor adjusted for user clusters."""
    draws = RNG.choice(values, size=(BOOTSTRAP, len(values)), replace=True).mean(axis=1)
    return values.mean(), float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


GROUPINGS = [("age_group", "Age band"), ("gender", "Gender"),
             ("city_level", "City tier"), ("payment", "Payment method"),
             ("membership", "Membership tier")]


def welch_test(groups: list[np.ndarray], trim: float = 0.0) -> tuple[float, float]:
    """Welch ANOVA; with trimming, the Welch-Yuen test of trimmed means.

    Trim floor(n * trim) observations from EACH tail. Use winsorised sums of
    squares divided by h-1 (h = retained n), not the variance of the trimmed
    observations. With two groups, F equals scipy's Welch/Yuen t statistic squared.
    See Wilcox, Introduction to Robust Estimation and Hypothesis Testing (2017).
    """
    if not 0 <= trim < 0.5 or len(groups) < 2:
        raise ValueError("Need >=2 groups and 0 <= trim < 0.5")
    means, variances, sizes = [], [], []
    for group in groups:
        values = np.sort(np.asarray(group, dtype=float))
        cut = int(len(values) * trim)
        retained = len(values) - 2 * cut
        if retained < 2 or not np.isfinite(values).all():
            raise ValueError("Each group needs >=2 retained, finite observations")
        winsorised = values.copy()
        if cut:
            winsorised[:cut] = values[cut]
            winsorised[-cut:] = values[-cut - 1]
        means.append(values[cut:len(values) - cut].mean())
        variances.append(np.sum((winsorised - winsorised.mean()) ** 2) / (retained - 1))
        sizes.append(retained)
    means, variances, sizes = map(np.asarray, (means, variances, sizes))
    if np.any(variances <= 0):
        raise ValueError("Welch test requires positive within-group variances")
    weights = sizes / variances
    relative_weights = weights / weights.sum()
    centre = np.sum(relative_weights * means)
    k = len(groups)
    correction = np.sum((1 - relative_weights) ** 2 / (sizes - 1))
    f_stat = (np.sum(weights * (means - centre) ** 2) / (k - 1)
              / (1 + 2 * (k - 2) * correction / (k * k - 1)))
    df2 = (k * k - 1) / (3 * correction)
    return float(f_stat), float(stats.f.sf(f_stat, k - 1, df2))


def group_tests(df: pd.DataFrame) -> pd.DataFrame:
    """Five primary mean comparisons plus explicitly separate sensitivity families."""
    rows = []
    for column, label in GROUPINGS:
        groups = [g["amount"].to_numpy() for _, g in df.groupby(column, observed=True)]
        f_stat, p_anova = stats.f_oneway(*groups)
        _, p_kruskal = stats.kruskal(*groups)
        _, p_welch = welch_test(groups)
        _, p_trimmed = welch_test(groups, trim=0.1)
        _, p_levene = stats.levene(*groups, center="median")
        means = df.groupby(column, observed=True)["amount"].mean()
        trimmed = [stats.trim_mean(group, 0.1) for group in groups]
        group_sizes = [len(group) for group in groups]
        group_variances = [np.var(group, ddof=1) for group in groups]
        rows.append({
            "variable": column, "label": label, "groups": len(groups),
            "n_used": sum(group_sizes), "n_missing_group": int(df[column].isna().sum()),
            "min_group_n": min(group_sizes), "max_group_n": max(group_sizes),
            "variance_ratio": max(group_variances) / min(group_variances),
            "brown_forsythe_p": p_levene,
            "anova_f": f_stat, "anova_p": p_anova, "kruskal_p": p_kruskal,
            "welch_p": p_welch, "trimmed_welch_p": p_trimmed,
            "anova_p_bonferroni": min(1.0, p_anova * len(GROUPINGS)),
            "welch_p_bonferroni": min(1.0, p_welch * len(GROUPINGS)),
            "kruskal_p_bonferroni": min(1.0, p_kruskal * len(GROUPINGS)),
            "trimmed_welch_p_bonferroni": min(1.0, p_trimmed * len(GROUPINGS)),
            "trimmed_mean_min": min(trimmed), "trimmed_mean_max": max(trimmed),
            "spread_pct_of_mean": (means.max() - means.min()) / df["amount"].mean() * 100,
            # Five groupings are tested, so the 5% threshold is Bonferroni-corrected.
            "significant_bonferroni": p_anova < 0.05 / len(GROUPINGS),
        })
    return pd.DataFrame(rows)


def save(fig, name: str, note: str) -> None:
    fig.text(0.01, -0.02, note, fontsize=8, color=MUTED, ha="left", va="top")
    fig.savefig(FIGURES / f"{name}.png")
    plt.close(fig)


def fig_effect_audit(df: pd.DataFrame, tests: pd.DataFrame) -> pd.DataFrame:
    """The headline figure: group means with intervals, so overlap is visible."""
    orders = {"age_group": ["18-25", "26-35", "36-45", "46-55", "56+"],
              "gender": ["Female", "Male"], "city_level": CITY_ORDER,
              "payment": ["WeChat Pay", "Alipay", "Debit card", "Credit card"],
              "membership": MEMBERSHIP_ORDER}
    overall = df["amount"].mean()
    fig, axes = plt.subplots(1, 5, figsize=(15, 4.6), sharey=True)
    detail = []
    for ax, (column, label) in zip(axes, GROUPINGS):
        test = tests.set_index("variable").loc[column]
        order = [v for v in orders[column] if v in set(df[column].dropna())]
        colour = BLUE if test["significant_bonferroni"] else MUTED
        for index, level in enumerate(order):
            values = df.loc[df[column] == level, "amount"].to_numpy()
            mean, low, high = mean_ci(values)
            ax.errorbar(index, mean, yerr=[[mean - low], [high - mean]], fmt="o",
                        color=colour, capsize=5, markersize=7, linewidth=1.8)
            detail.append({"variable": column, "level": level, "n": len(values),
                           "mean_amount": mean, "ci_low": low, "ci_high": high})
        ax.axhline(overall, color=AMBER, linestyle=":", linewidth=1.4)
        ax.set_xticks(range(len(order)), order, rotation=35, ha="right", fontsize=9)
        verdict = "mean evidence" if test["significant_bonferroni"] else "not rejected"
        ax.set_title(f"{label}\np = {test['anova_p']:.2g}\n{verdict}",
                     fontsize=11, color=INK if test["significant_bonferroni"] else BODY)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    axes[0].set_ylabel("Mean transaction amount (¥)")
    not_rejected = int((~tests["significant_bonferroni"]).sum())
    fig.suptitle(f"{not_rejected} of {len(tests)} mean-comparison nulls are not rejected",
                 fontsize=14.5, fontweight="bold", color=INK, y=1.03)
    fig.tight_layout()
    save(fig, "01_segmentation_effect_audit",
         "Means with pointwise IID bootstrap 95% intervals (2,000 draws); not pairwise tests. "
         "Nominal ANOVA p-values; Bonferroni threshold 0.05/5.\n"
         "Repeated users are not cluster-adjusted. Non-rejection is not equivalence; "
         "Welch, rank and trimmed-mean checks are exported separately.")
    return pd.DataFrame(detail)


CONTINUOUS = [("income", "Monthly income"), ("age", "Age"),
              ("discount", "Discount rate"), ("rating", "Rating"),
              ("quantity", "Quantity"), ("price", "Unit price")]


def correlation_table(df: pd.DataFrame) -> pd.DataFrame:
    """Pearson r with a Fisher-z 95% interval, so precision is visible."""
    rows = []
    for column, label in CONTINUOUS:
        sub = df[[column, "amount"]].dropna()
        r, p = stats.pearsonr(sub[column], sub["amount"])
        n = len(sub)
        se = 1 / np.sqrt(n - 3)
        low, high = np.tanh(np.arctanh(r) - 1.96 * se), np.tanh(np.arctanh(r) + 1.96 * se)
        rows.append({"variable": column, "label": label, "n": n, "pearson_r": r,
                     "ci_low": low, "ci_high": high, "p_value": p,
                     "excludes_zero": low > 0 or high < 0})
    return pd.DataFrame(rows)


def fig_correlation_forest(table: pd.DataFrame) -> None:
    """Show the precision of a linear association estimate, with its assumptions."""
    fig, ax = plt.subplots(figsize=(9, 5))
    y = np.arange(len(table))[::-1]
    for position, row in zip(y, table.itertuples()):
        colour = BLUE if row.excludes_zero else MUTED
        ax.plot([row.ci_low, row.ci_high], [position, position], color=colour, linewidth=2.6)
        ax.plot(row.pearson_r, position, "o", color=colour, markersize=8)
        ax.text(1.02, position, f"r = {row.pearson_r:+.3f}", va="center", fontsize=9,
                color=colour, transform=ax.get_yaxis_transform())
    ax.axvline(0, color=CORAL, linewidth=1.4, linestyle="--")
    ax.set_yticks(y, table["label"])
    ax.set_xlim(-0.2, 1.0)
    ax.set_xlabel("Pearson correlation with transaction amount (95% CI)")
    ax.set_title("Linear associations with transaction amount\n"
                 "Intervals containing zero do not establish absence of a relationship")
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    income = table.set_index("variable").loc["income"]
    save(fig, "02_correlation_forest",
         f"Income n = {int(income['n']):,}, nominal Fisher-z 95% CI "
         f"[{income['ci_low']:+.3f}, {income['ci_high']:+.3f}]. Intervals are pointwise, "
         "not multiplicity- or user-cluster-adjusted.\n"
         "They describe linear correlation under sampling assumptions; nonlinear "
         "relationships, confounding and causal effects remain unresolved.")



def fig_mechanical_identity(df: pd.DataFrame) -> dict:
    """Describe basket arithmetic without interpreting association as a mechanism."""
    expected = df["price"] * df["quantity"] * (1 - df["discount"])
    r = float(df["amount"].corr(expected))
    design = np.column_stack([np.ones(len(df)), expected])
    beta, *_ = np.linalg.lstsq(design, df["amount"].to_numpy(), rcond=None)
    residual = df["amount"].to_numpy() - design @ beta
    r2 = 1 - residual.var() / df["amount"].var()

    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.scatter(expected, df["amount"], s=7, alpha=0.18, color=BLUE,
               edgecolors="none", label="Transactions")
    limit = max(expected.max(), df["amount"].max()) * 1.02
    ax.plot([0, limit], [0, limit], color=CORAL, linewidth=1.6, linestyle="--",
            label="amount = price × quantity × (1 − discount)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("price × quantity × (1 − discount)  (¥, log scale)")
    ax.set_ylabel("Recorded amount (¥, log scale)")
    ax.set_title("Transaction value closely tracks basket arithmetic\n"
                 f"r = {r:.3f} against the arithmetic expectation, R² = {r2:.3f}")
    ax.legend(loc="upper left")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ratio = (df["amount"] / expected).describe()
    save(fig, "03_basket_identity",
         f"Recorded/expected ratio: median {ratio['50%']:.3f}, upper quartile "
         f"{ratio['75%']:.3f}. Fees, rounding or construction rules are possible "
         "explanations, not verified mechanisms.\n"
         "This accounting association does not rule out customer behaviour.")
    return {"r_vs_expected": round(r, 4), "r2_vs_expected": round(float(r2), 4),
            "ratio_median": round(float(ratio["50%"]), 4),
            "ratio_q75": round(float(ratio["75%"]), 4)}


def fig_amount_distribution(df: pd.DataFrame) -> None:
    amount = df["amount"]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(amount, bins=np.logspace(np.log10(amount.min()), np.log10(amount.max()), 50),
            color=BLUE, edgecolor="white", linewidth=0.5)
    ax.set_xscale("log")
    for value, label, colour in [(amount.median(), "median", TEAL),
                                 (amount.mean(), "mean", CORAL)]:
        ax.axvline(value, color=colour, linestyle="--", linewidth=1.6)
        ax.text(value * 1.04, ax.get_ylim()[1] * 0.9, f"{label} ¥{value:,.0f}",
                fontsize=9, color=colour)
    share = (amount > amount.mean()).mean()
    ax.set_xlabel("Transaction amount (¥, log scale)")
    ax.set_ylabel("Transactions")
    ax.set_title("The mean sits above two thirds of all transactions\n"
                 f"{share:.0%} of baskets exceed the mean — report both mean and median")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    save(fig, "04_amount_distribution",
         "Log-spaced bins. A right-skewed basket distribution is expected; the "
         "median describes a typical basket; the arithmetic mean remains relevant "
         "to revenue per transaction. Neither measures profit or customer lifetime value.")


def fig_membership(df: pd.DataFrame, tests: pd.DataFrame) -> pd.DataFrame:
    """Descriptive tier differences, with computed sensitivity results and caveats."""
    table = df.groupby("membership", observed=True).agg(
        transactions=("amount", "size"), mean_amount=("amount", "mean"),
        median_amount=("amount", "median"),
        trimmed_mean_amount=("amount", lambda s: stats.trim_mean(s, 0.1)),
        median_price=("price", "median"), mean_quantity=("quantity", "mean"),
        share_over_3000=("amount", lambda s: (s > 3000).mean()),
    ).reindex(MEMBERSHIP_ORDER).reset_index()

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.5, 5))
    data = [df.loc[df["membership"] == level, "amount"].to_numpy()
            for level in MEMBERSHIP_ORDER]
    box = ax.boxplot(data, tick_labels=MEMBERSHIP_ORDER, patch_artist=True,
                     showfliers=False, medianprops=dict(color=CORAL, linewidth=2))
    for patch in box["boxes"]:
        patch.set_facecolor("#d6e4f0")
        patch.set_edgecolor(BLUE)
    ax.plot(range(1, len(table) + 1), table["trimmed_mean_amount"], color=TEAL,
            marker="D", linewidth=1.8, markersize=6, label="10% trimmed mean")
    ax.set_ylabel("Transaction amount (¥)")
    ax.set_title("Transaction amounts by membership tier")
    ax.legend(loc="upper left")

    # Small descriptive differences are unreadable as absolute bars, so show them as
    # percentage change against the Standard tier.
    metrics = [("median_amount", "Median amount", BLUE),
               ("median_price", "Median unit price", TEAL),
               ("mean_quantity", "Mean quantity", AMBER),
               ("share_over_3000", "Share of orders > ¥3,000", CORAL)]
    width = 0.2
    x = np.arange(len(table))
    for offset, (column, label, colour) in enumerate(metrics):
        base = table[column].iloc[0]
        change = (table[column] / base - 1) * 100
        ax2.bar(x + (offset - 1.5) * width, change, width, color=colour, label=label)
    ax2.axhline(0, color=BODY, linewidth=1)
    ax2.set_xticks(x, MEMBERSHIP_ORDER)
    ax2.set_ylabel("Change vs Standard tier (%)")
    ax2.set_title("Basket composition relative to Standard")
    ax2.legend(loc="upper left", fontsize=9)
    for axis in (ax, ax2):
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)
    fig.tight_layout()
    test = tests.set_index("variable").loc["membership"]
    save(fig, "05_membership_effect",
         f"Nominal omnibus p: ANOVA {test['anova_p']:.2g}; Welch {test['welch_p']:.2g}; "
         f"Kruskal-Wallis {test['kruskal_p']:.2g}; 10%-per-tail Welch-Yuen "
         f"{test['trimmed_welch_p']:.2g}.\n"
         "Different estimands; no pairwise tier claims or uniform-distribution-shift claim. "
         "Tier assignment and causal direction are unverified; repeated users are not adjusted.")
    return table



def fig_category(df: pd.DataFrame) -> pd.DataFrame:
    """A legitimately descriptive chart: composition, with no inference attached."""
    table = df.groupby("category", observed=True).agg(
        revenue=("amount", "sum"), transactions=("amount", "size"),
        median_amount=("amount", "median"), mean_price=("price", "mean")
    ).sort_values("revenue", ascending=False).reset_index()
    table["revenue_share"] = table["revenue"] / table["revenue"].sum()

    fig, ax = plt.subplots(figsize=(9.5, 5))
    bars = ax.barh(table["category"][::-1], table["revenue"][::-1] / 1000, color=BLUE)
    for bar, share, count in zip(bars, table["revenue_share"][::-1],
                                 table["transactions"][::-1]):
        ax.text(bar.get_width() * 1.01, bar.get_y() + bar.get_height() / 2,
                f"{share:.1%} · {count:,} orders", va="center", fontsize=9, color=BODY)
    ax.set_xlabel("Revenue (¥ thousands)")
    ax.set_xlim(0, table["revenue"].max() / 1000 * 1.3)
    ax.set_title("Revenue concentration by category\n"
                 f"the top two categories account for "
                 f"{table['revenue_share'].head(2).sum():.0%} of revenue")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    save(fig, "06_category_revenue",
         "Composition only. Category revenue differences are driven by unit price "
         "and order count, both recorded fields, so no customer-preference claim "
         "is made here.")
    return table


def fig_monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly totals against the variation reshuffling alone would produce."""
    monthly = df.groupby("month").agg(
        revenue=("amount", "sum"), transactions=("amount", "size"),
        customers=("user_id", "nunique")).reset_index()

    # Null band: keep each month's order count, reshuffle which amounts land in
    # which month. A permutation preserves the exact set of amounts, so the band
    # shows only the variation that calendar assignment alone can create.
    amounts = df["amount"].to_numpy()
    edges = np.cumsum(monthly["transactions"].to_numpy())[:-1]
    simulated = np.array([
        [chunk.sum() for chunk in np.split(RNG.permutation(amounts), edges)]
        for _ in range(500)])
    low = np.percentile(simulated, 2.5, axis=0) / 1000
    high = np.percentile(simulated, 97.5, axis=0) / 1000
    inside = ((monthly["revenue"] / 1000 >= low) & (monthly["revenue"] / 1000 <= high)).sum()

    fig, ax = plt.subplots(figsize=(10.5, 5))
    ax.fill_between(monthly["month"], low, high, color=MUTED, alpha=0.25,
                    label="95% range under random reassignment of months")
    ax.plot(monthly["month"], monthly["revenue"] / 1000, color=BLUE, marker="o",
            linewidth=2.2, label="Observed revenue")
    ax.set_ylabel("Revenue (¥ thousands)")
    ax.tick_params(axis="x", rotation=45)
    ax.set_title("Monthly revenue against a fixed-order-count reference\n"
                 f"{inside} of {len(monthly)} months fall inside the range produced by "
                 f"reshuffling alone")
    ax.legend(loc="upper left", fontsize=9)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    save(fig, "07_monthly_trend_vs_noise",
         "The band holds each month's order count fixed and permutes which amounts "
         "fall in which month, 500 times. Pointwise reference bands assume exchangeable "
         "amounts, not a joint seasonality test.\n"
         "This cannot exclude order-count seasonality, dependence or smaller effects.")

    monthly["null_low"] = low * 1000
    monthly["null_high"] = high * 1000
    return monthly


def render_readme(findings: dict, tests: pd.DataFrame, correlations: pd.DataFrame,
                  membership: pd.DataFrame) -> str:
    """Render the full report from this run, including assumptions and decisions."""
    data = findings["data"]
    test_rows = "\n".join(
        f"| {r.label} | {r.n_used:,} | {r.anova_p:.3g} | {r.anova_p_bonferroni:.3g} "
        f"| {r.welch_p:.3g} | {r.kruskal_p:.3g} | {r.trimmed_welch_p:.3g} | "
        f"{'reject equal means (nominal)' if r.significant_bonferroni else 'not rejected'} |"
        for r in tests.itertuples())
    correlation_rows = "\n".join(
        f"| {r.label} | {r.n:,} | {r.pearson_r:+.3f} | [{r.ci_low:+.3f}, {r.ci_high:+.3f}] |"
        for r in correlations.itertuples())
    tiers = membership.set_index("membership")
    standard, platinum = tiers.loc["Standard"], tiers.loc["Platinum"]
    mem_test = tests.set_index("variable").loc["membership"]
    identity = findings["basket_identity"]
    missing = ", ".join(f"`{name}`: {count}" for name, count in data["missing_by_field"].items())
    return f"""# Consumer Transactions: Evidence for a Segmentation Decision

**{data['rows']:,} raw rows → remove {data['duplicate_rows']:,} exact duplicates →
{findings['rows_after_dedup']:,} analysed transactions. Non-significance does not prove equality.**

`Python` · `Matplotlib` · `ANOVA / Welch / Kruskal-Wallis / trimmed means`

## Business question and metric

Should a marketing team prioritise a demographic segment or a membership offer?
The primary metric here is **mean recorded amount per transaction** (sum of amount
divided by included transactions), relevant to revenue per order. Median amount
describes a typical order; a 10%-per-tail trimmed mean describes the central 80%.
These are different estimands. None measures margin, conversion, purchase frequency
or lifetime value. The unit is a transaction, not a customer.

## Evidence and statistical scope

The table uses the {findings['rows_after_dedup']:,} deduplicated transactions, dropping
missing labels separately for each grouping; `n` is the included count.
{findings['not_rejected_segmentations']} of {len(tests)} primary ANOVA hypotheses are
not rejected at Bonferroni 0.05/5 = 0.01. This does not prove no difference or
establish that any segment is commercially equivalent.

| Grouping | n | ANOVA p | ANOVA adjusted p | Welch p | Kruskal-Wallis p | Trimmed Welch-Yuen p | Primary decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{test_rows}

**These are nominal, exploratory transaction-level tests.** There are
{data['unique_users_after_dedup']:,} unique user IDs and
{data['users_with_multiple_transactions']:,} IDs with repeated transactions.
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
{correlation_rows}

Near-zero estimates constrain plausible **linear** correlations under the sampling
assumptions. Intervals containing zero do not demonstrate absence of association;
nonlinear patterns, confounding and causal effects remain unresolved.

![Correlation forest](figures/02_correlation_forest.png)

Recorded amount tracks `price × quantity × (1 − discount)` with
r = {identity['r_vs_expected']:.3f}, R² = {identity['r2_vs_expected']:.3f}.
The recorded/expected ratio has median {identity['ratio_median']:.3f} and upper
quartile {identity['ratio_q75']:.3f}. Fees or dataset construction rules are hypotheses,
not verified mechanisms. Basket arithmetic does not exclude customer behaviour.

![Basket arithmetic](figures/03_basket_identity.png)
![Amount distribution](figures/04_amount_distribution.png)

## Membership association and commercial meaning

Mean amount is ¥{standard['mean_amount']:,.2f} for Standard and
¥{platinum['mean_amount']:,.2f} for Platinum, a descriptive difference of
¥{platinum['mean_amount'] - standard['mean_amount']:,.2f} per transaction.
Membership omnibus p-values are ANOVA {mem_test['anova_p']:.3g},
Welch {mem_test['welch_p']:.3g}, Kruskal-Wallis {mem_test['kruskal_p']:.3g} and
trimmed Welch-Yuen {mem_test['trimmed_welch_p']:.3g}; they address different nulls.
These are neither an adjusted Standard–Platinum pairwise test nor an upgrade effect.

Membership is a candidate for further investigation, not a reason to spend more
on upgrades. Tier eligibility may depend on prior spending, and the assignment
rule is undocumented. Selection, confounding and reverse causality remain possible.
The top two categories contribute {findings['top_two_category_revenue_share']:.1%}
of recorded revenue; inspect their margins and inventory exposure before allocating
budget. Revenue concentration alone does not establish customer preference or profit.

![Membership](figures/05_membership_effect.png)
![Category revenue](figures/06_category_revenue.png)

## Monthly reference and its limits

{findings['months_inside_null_band']} of {findings['months_total']} months lie within
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

The course-supplied source has **{data['rows']:,} raw rows**, including
**{data['duplicate_rows']:,} exact duplicate rows**. All reported analyses use the
**{findings['rows_after_dedup']:,} deduplicated transactions**; missing values are not
globally imputed. Raw missing counts: {missing}. Dates span
{data['date_min']} to {data['date_max']}. The generating process and upstream vendor
are undocumented. Results illustrate an analysis workflow, not real-market claims.

From this project directory, in the centrally prepared Python environment:

```bash
python src/analyze.py
python -m unittest discover -s tests -v
```

The build rewrites seven PNG figures, six CSV tables, `outputs/findings.json` and
this README via `render_readme()`. A seed of {SEED} is reset at each full run;
reproducibility also depends on dependency versions. Reports/PNG figures can be
viewed offline. Original coursework is retained in `source_materials/`; source data
is unmodified. AI assistance was used for code structuring and English writing.
"""


def main() -> None:
    global RNG
    RNG = np.random.default_rng(SEED)
    FIGURES.mkdir(exist_ok=True)
    OUTPUTS.mkdir(exist_ok=True)

    df, defects = load()
    tests = group_tests(df)
    correlations = correlation_table(df)

    group_detail = fig_effect_audit(df, tests)
    fig_correlation_forest(correlations)
    identity = fig_mechanical_identity(df)
    fig_amount_distribution(df)
    membership = fig_membership(df, tests)
    category = fig_category(df)
    monthly = fig_monthly_trend(df)

    tests.to_csv(OUTPUTS / "01_segmentation_tests.csv", index=False)
    group_detail.to_csv(OUTPUTS / "02_group_means_ci.csv", index=False)
    correlations.to_csv(OUTPUTS / "03_correlations_ci.csv", index=False)
    membership.to_csv(OUTPUTS / "04_membership_detail.csv", index=False)
    category.to_csv(OUTPUTS / "05_category_revenue.csv", index=False)
    monthly.to_csv(OUTPUTS / "06_monthly_revenue_vs_null.csv", index=False)

    indexed = tests.set_index("variable")
    income = correlations.set_index("variable").loc["income"]
    findings = {
        "data": defects,
        "rows_after_dedup": int(len(df)),
        "segmentation": {
            row.variable: {"anova_p": float(row.anova_p),
                           "anova_p_bonferroni": float(row.anova_p_bonferroni),
                           "welch_p": float(row.welch_p),
                           "kruskal_p": float(row.kruskal_p),
                           "trimmed_welch_p": float(row.trimmed_welch_p),
                           "reject_equal_means_nominal": bool(row.significant_bonferroni),
                           "spread_pct_of_mean": round(float(row.spread_pct_of_mean), 1)}
            for row in tests.itertuples()},
        "not_rejected_segmentations": int((~tests["significant_bonferroni"]).sum()),
        "inference_scope": {
            "unit": "transaction", "primary_estimand": "arithmetic mean amount",
            "primary_family": "five ANOVA tests; Bonferroni alpha=0.05/5",
            "sensitivity": "Welch means; Kruskal-Wallis ranks; 10%-per-tail Welch-Yuen means",
            "user_cluster_adjusted": False, "causal_identification": False,
            "non_rejection_is_equivalence": False},
        "income_amount": {"r": round(float(income["pearson_r"]), 4),
                          "ci": [round(float(income["ci_low"]), 4),
                                 round(float(income["ci_high"]), 4)],
                          "p": round(float(income["p_value"]), 3)},
        "basket_identity": identity,
        "membership_mean_amount": {row.membership: round(float(row.mean_amount), 2)
                                   for row in membership.itertuples()},
        "membership_anova_p": float(indexed.loc["membership", "anova_p"]),
        "top_two_category_revenue_share": round(
            float(category["revenue_share"].head(2).sum()), 4),
        "months_inside_null_band": int(
            ((monthly["revenue"] >= monthly["null_low"]) &
             (monthly["revenue"] <= monthly["null_high"])).sum()),
        "months_total": int(len(monthly)),
    }
    (OUTPUTS / "findings.json").write_text(
        json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")
    (ROOT / "README.md").write_text(
        render_readme(findings, tests, correlations, membership), encoding="utf-8")
    print(json.dumps(findings, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()







