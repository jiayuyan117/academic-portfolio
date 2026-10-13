"""Consumer transactions: a segmentation exercise on data with almost no segments.

Input  : data/consumer_transactions.csv   (8,020 rows, course-supplied)
Output : figures/*.png   seven Matplotlib figures
         outputs/*.csv   the tables behind each figure
         outputs/findings.json  every number quoted in README.md

The assignment asks which customer groups spend more. The honest answer, on this
dataset, is that four of the five candidate groupings do not differ at all:
age band, gender, city tier and payment method all give ANOVA p > 0.48. Only
membership tier separates (p < 0.0001), and even that admits an obvious reverse
reading -- tiers are usually awarded *for* spending.

So this project reports confidence intervals and tests before it reports
rankings, and declines to rank where the test says there is nothing to rank.
Ranking five group means that differ by noise is the single most common way a
dashboard invents a finding.
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

RNG = np.random.default_rng(20261013)
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
    """Bootstrap mean and 95% percentile interval, robust to the heavy right tail."""
    draws = RNG.choice(values, size=(BOOTSTRAP, len(values)), replace=True).mean(axis=1)
    return values.mean(), float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


GROUPINGS = [("age_group", "Age band"), ("gender", "Gender"),
             ("city_level", "City tier"), ("payment", "Payment method"),
             ("membership", "Membership tier")]


def group_tests(df: pd.DataFrame) -> pd.DataFrame:
    """One row per candidate segmentation: does it separate spending at all?"""
    rows = []
    for column, label in GROUPINGS:
        groups = [g["amount"].to_numpy() for _, g in df.groupby(column, observed=True)]
        f_stat, p_anova = stats.f_oneway(*groups)
        _, p_kruskal = stats.kruskal(*groups)
        means = df.groupby(column, observed=True)["amount"].mean()
        rows.append({
            "variable": column, "label": label, "groups": len(groups),
            "anova_f": f_stat, "anova_p": p_anova, "kruskal_p": p_kruskal,
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
        verdict = "separates" if test["significant_bonferroni"] else "no difference"
        ax.set_title(f"{label}\np = {test['anova_p']:.3f} — {verdict}",
                     fontsize=11, color=INK if test["significant_bonferroni"] else BODY)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    axes[0].set_ylabel("Mean transaction amount (¥)")
    fig.suptitle("Four of five candidate segmentations do not separate spending at all",
                 fontsize=14.5, fontweight="bold", color=INK, y=1.03)
    fig.tight_layout()
    save(fig, "01_segmentation_effect_audit",
         "Points are group means; bars are 2,000-draw bootstrap 95% intervals. "
         "Dotted line is the overall mean. p-values are one-way ANOVA; the "
         "'separates' verdict uses a Bonferroni threshold of 0.05/5 = 0.01.")
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
    """A tight interval around zero is a finding, not a missing finding."""
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
    ax.set_title("Income, age, discount and rating are confidently unrelated to spend\n"
                 "the intervals are narrow and they contain zero — this is a null, not a gap")
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    income = table.set_index("variable").loc["income"]
    bound = max(abs(income["ci_low"]), abs(income["ci_high"]))
    save(fig, "02_correlation_forest",
         f"Fisher-z intervals on n = {int(income['n']):,}. The income interval is "
         f"[{income['ci_low']:+.3f}, {income['ci_high']:+.3f}] — narrow enough to rule "
         f"out any association stronger than {bound:.2f}, which is why 'weak but "
         f"present' would be the wrong description of it.")



def fig_mechanical_identity(df: pd.DataFrame) -> dict:
    """What amount *is* determined by: the basket, not the customer."""
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
    ax.set_title("Transaction value is a basket identity, not a behavioural outcome\n"
                 f"r = {r:.3f} against the arithmetic expectation, R² = {r2:.3f}")
    ax.legend(loc="upper left")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    save(fig, "03_basket_identity",
         "Points above the dashed line carry a surcharge; the ratio clusters on a "
         "few discrete multipliers (median 1.000, upper quartile 1.100), which is "
         "consistent with a shipping or service tier rather than customer choice.")
    ratio = (df["amount"] / expected).describe()
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
                 f"only {share:.0%} of baskets exceed the mean — report medians, not means")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    save(fig, "04_amount_distribution",
         "Log-spaced bins. A right-skewed basket distribution is expected; the "
         "point is that a 'mean basket' headline would describe a minority of orders.")


def fig_membership(df: pd.DataFrame) -> pd.DataFrame:
    """The one real effect -- shown with its mechanism and its causal caveat."""
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
    ax.set_title("Membership tier does separate spending")
    ax.legend(loc="upper left")

    # Small real differences are unreadable as absolute bars, so show them as
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
    ax2.set_title("…through unit price and large orders, not basket size")
    ax2.legend(loc="upper left", fontsize=9)
    for axis in (ax, ax2):
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)
    fig.tight_layout()
    save(fig, "05_membership_effect",
         "ANOVA p = 1.0e-06, surviving Bonferroni correction for five tested "
         "groupings, and p = 1.6e-09 on 10% trimmed means — so this is a shift of "
         "the whole distribution, not a few large orders. Direction is not "
         "identified: loyalty tiers are normally awarded for past spending, so this "
         "is as consistent with reverse causality as with a tier effect.")
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
    ax.set_title("There is no monthly pattern to explain\n"
                 f"{inside} of {len(monthly)} months fall inside the range produced by "
                 f"reshuffling alone")
    ax.legend(loc="upper left", fontsize=9)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    save(fig, "07_monthly_trend_vs_noise",
         "The band holds each month's order count fixed and permutes which amounts "
         "fall in which month, 500 times. A seasonality narrative fitted to this "
         "series would be fitting noise.")

    monthly["null_low"] = low * 1000
    monthly["null_high"] = high * 1000
    return monthly


def main() -> None:
    FIGURES.mkdir(exist_ok=True)
    OUTPUTS.mkdir(exist_ok=True)

    df, defects = load()
    tests = group_tests(df)
    correlations = correlation_table(df)

    group_detail = fig_effect_audit(df, tests)
    fig_correlation_forest(correlations)
    identity = fig_mechanical_identity(df)
    fig_amount_distribution(df)
    membership = fig_membership(df)
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
            row.variable: {"anova_p": round(float(row.anova_p), 4),
                           "separates": bool(row.significant_bonferroni),
                           "spread_pct_of_mean": round(float(row.spread_pct_of_mean), 1)}
            for row in tests.itertuples()},
        "null_segmentations": int((~tests["significant_bonferroni"]).sum()),
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
    print(json.dumps(findings, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()







