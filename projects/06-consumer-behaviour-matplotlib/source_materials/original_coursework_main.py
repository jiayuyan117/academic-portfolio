from pathlib import Path
import json, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "数据可视化综合实验_消费行为分析数据.csv"
FIG, OUT = ROOT / "figures", ROOT / "outputs"
FIG.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

df_raw = pd.read_csv(DATA)
raw_rows, raw_cols = df_raw.shape
df = df_raw.copy()
numeric = ["age", "income", "price", "quantity", "discount", "rating", "amount"]
for c in numeric: df[c] = pd.to_numeric(df[c], errors="coerce")
df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce")
quality = pd.DataFrame({"field": df.columns, "missing_count": df.isna().sum().values,
                        "missing_ratio": df.isna().mean().values,
                        "dtype": df.dtypes.astype(str).values})
quality.to_csv(OUT / "01_data_quality.csv", index=False, encoding="utf-8-sig")
dup_count = int(df.duplicated().sum())
missing_before = df.isna().sum()
for c in numeric: df[c] = df[c].fillna(df[c].median())
df["purchase_date"] = df["purchase_date"].ffill().bfill()
df = df.drop_duplicates().copy()
for c in numeric:
    q1, q3 = df[c].quantile([.25, .75]); iqr = q3 - q1
    df[f"{c}_outlier_flag"] = (df[c] < q1 - 1.5 * iqr) | (df[c] > q3 + 1.5 * iqr)
df["age_group"] = pd.cut(df["age"], [17,25,35,45,55,np.inf],
                         labels=["18-25","26-35","36-45","46-55","56+"])
df.to_csv(OUT / "02_cleaned_analysis_data.csv", index=False, encoding="utf-8-sig")

age = df.groupby("age_group", observed=False).agg(total_amount=("amount","sum"),
    mean_amount=("amount","mean"), people=("user_id","nunique"), records=("amount","size")).reset_index()
age.to_csv(OUT / "03_age_group_statistics.csv", index=False, encoding="utf-8-sig")
cat = df.groupby("category").agg(sales_amount=("amount","sum"), sales_quantity=("quantity","sum"),
    mean_price=("price","mean"), records=("amount","size")).sort_values("sales_amount", ascending=False).reset_index()
cat.to_csv(OUT / "04_category_statistics.csv", index=False, encoding="utf-8-sig")
member_cat = pd.pivot_table(df, index="category", columns="membership", values="amount", aggfunc="sum", fill_value=0)
member_cat.to_csv(OUT / "05_category_membership_structure.csv", encoding="utf-8-sig")
corr_cols = ["age","income","price","quantity","discount","rating","amount"]
corr = df[corr_cols].corr(); corr.to_csv(OUT / "06_correlation_matrix.csv", encoding="utf-8-sig")
r = float(df["income"].corr(df["amount"]))
monthly = df.groupby(df["purchase_date"].dt.to_period("M")).agg(amount=("amount","sum"),
    people=("user_id","nunique"), records=("amount","size"))
monthly["rolling_3_month_amount"] = monthly["amount"].rolling(3).mean()
monthly.index = monthly.index.astype(str); monthly.to_csv(OUT / "07_monthly_trend.csv", encoding="utf-8-sig")

def save(fig, name):
    fig.tight_layout(); fig.savefig(FIG / f"{name}.png", dpi=180); plt.close(fig)

fig, ax = plt.subplots(figsize=(10,6)); x=np.arange(len(age)); w=.28
ax.bar(x-w, age.total_amount, w, label="Total amount"); ax.bar(x, age.mean_amount, w, label="Mean amount")
ax2=ax.twinx(); ax2.bar(x+w, age.people, w, color="#54A24B", label="People")
ax.set_xticks(x, age.age_group); ax.set_ylabel("Amount"); ax2.set_ylabel("People"); ax.set_title("Age-group total, mean and people (separate scales)")
ax.legend(loc="upper left"); ax2.legend(loc="upper right"); save(fig,"01_age_group_scales")

fig, ax=plt.subplots(figsize=(10,6)); ax.hist(df.amount, bins=40, color="#4C78A8", edgecolor="white"); ax.set(title="Overall amount distribution", xlabel="Amount", ylabel="Frequency"); save(fig,"02_amount_histogram")
fig, ax=plt.subplots(figsize=(10,6)); order=["普通","银卡","金卡","铂金"]; ax.boxplot([df.loc[df.membership==m,"amount"] for m in order], tick_labels=order, patch_artist=True); ax.set(title="Amount by membership", ylabel="Amount"); save(fig,"03_membership_boxplot")
fig, ax=plt.subplots(figsize=(10,6)); ax.bar(cat.category, cat.sales_amount, color="#F58518"); ax.tick_params(axis="x", rotation=25); ax.set(title="Sales amount by category", ylabel="Sales amount"); save(fig,"04_category_sales")
fig, ax=plt.subplots(figsize=(10,6)); ax.scatter(df.income, df.amount, s=10, alpha=.25, color="#54A24B"); z=np.polyfit(df.income,df.amount,1); xs=np.linspace(df.income.min(),df.income.max(),100); ax.plot(xs,z[0]*xs+z[1],color="red"); ax.set(title=f"Income vs amount (Pearson r={r:.3f})",xlabel="Monthly income",ylabel="Amount"); save(fig,"05_income_amount_scatter")
fig, ax=plt.subplots(figsize=(12,5)); ax.plot(monthly.index,monthly.amount,marker="o",ms=3,label="Monthly amount"); ax.plot(monthly.index,monthly.rolling_3_month_amount,linewidth=2,label="3-month moving average"); ax.tick_params(axis="x",rotation=60); ax.set(title="Monthly amount trend",ylabel="Amount"); ax.legend(); save(fig,"06_monthly_trend")
fig, ax=plt.subplots(figsize=(9,7)); im=ax.imshow(corr,cmap="coolwarm",vmin=-1,vmax=1); ax.set_xticks(range(len(corr_cols)),corr_cols,rotation=35,ha="right"); ax.set_yticks(range(len(corr_cols)),corr_cols)
for i in range(len(corr_cols)):
    for j in range(len(corr_cols)): ax.text(j,i,f"{corr.iloc[i,j]:.2f}",ha="center",va="center",fontsize=8)
fig.colorbar(im,ax=ax,label="Pearson correlation"); ax.set_title("Seven-variable correlation heatmap"); save(fig,"07_correlation_heatmap")

with PdfPages(OUT / "matplotlib_figures.pdf") as pdf:
    for p in sorted(FIG.glob("*.png")):
        im=plt.imread(p); fig, ax=plt.subplots(figsize=(11,7)); ax.imshow(im); ax.axis("off"); ax.set_title(p.stem); pdf.savefig(fig); plt.close(fig)
top = cat.iloc[0]; best = corr.where(~np.eye(len(corr),dtype=bool)).abs().stack().sort_values(ascending=False).index[0]
report = f"""# Matplotlib Consumer Behaviour Analysis

## Data and quality
The original dataset has **{raw_rows} rows and {raw_cols} fields**. The quality table preserves missing counts before imputation; {int(missing_before.sum())} missing cells were filled with numeric medians or date endpoint filling, and {dup_count} duplicate rows were removed. IQR flags are retained rather than deleting every extreme value. `discount` is treated only as a source-labelled discount-rate field; its encoding is not reverse-engineered into a price formula.

## Findings
- Highest total amount age group: **{age.loc[age.total_amount.idxmax(),'age_group']}**; highest mean amount group: **{age.loc[age.mean_amount.idxmax(),'age_group']}**. These are intentionally shown on separate scales from people counts.
- Highest sales category: **{top.category}**. Category output includes amount, quantity, mean price, record count and a membership-by-category amount table.
- Income/amount Pearson correlation: **{r:.3f}**. Correlation is descriptive, not causal.
- Monthly output includes the original amount series and a 3-month moving average. Strongest absolute off-diagonal correlation pair: **{best[0]} / {best[1]}**.

## Limitations
The source is observational transaction data. Median imputation and duplicate removal can affect estimates; IQR flags identify candidates but do not prove invalidity. Currency, discount semantics and business identity rules remain those of the original assignment.
"""
(ROOT / "analysis_report.md").write_text(report, encoding="utf-8")
print("Matplotlib complete:", ROOT)
