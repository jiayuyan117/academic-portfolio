from pathlib import Path
import warnings, numpy as np, pandas as pd, seaborn as sns, matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
warnings.filterwarnings("ignore")
ROOT=Path(__file__).resolve().parent; DATA=ROOT/"data"/"PRSA_data_2010.1.1-2014.12.31.csv"; FIG=ROOT/"figures"; OUT=ROOT/"outputs"; FIG.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
sns.set_theme(style="whitegrid", context="notebook"); plt.rcParams["font.sans-serif"]=["Microsoft YaHei","SimHei","Arial Unicode MS","DejaVu Sans"]; plt.rcParams["axes.unicode_minus"]=False
raw=pd.read_csv(DATA, na_values=["NA"]); raw_rows=len(raw); df=raw.copy(); df["timestamp"]=pd.to_datetime(df[["year","month","day","hour"]]); df=df.sort_values("timestamp").reset_index(drop=True)
continuous=["pm2.5","TEMP","PRES","Ir"]; quality=pd.DataFrame({"field":continuous,"missing_before":df[continuous].isna().sum().values,"missing_ratio":df[continuous].isna().mean().values})
quality.to_csv(OUT/"01_data_quality.csv",index=False,encoding="utf-8-sig")
invalid_negative={}; for_report=[]
for c in continuous:
    invalid_negative[c]=int((df[c]<0).sum()); df.loc[df[c]<0,c]=np.nan
    before=int(df[c].isna().sum()); df[c]=df[c].interpolate("linear").bfill().ffill(); for_report.append((c,before,int(df[c].isna().sum())))
df["rain_level"]=pd.cut(df["Ir"],[-.001,0,2,np.inf],labels=["No rain","Light rain","Heavy rain"],include_lowest=True)
df.to_csv(OUT/"02_cleaned_derived_data.csv",index=False,encoding="utf-8-sig")
def save(fig,name): fig.tight_layout(); fig.savefig(FIG/f"{name}.png",dpi=180); plt.close(fig)
fig,ax=plt.subplots(figsize=(10,6)); sns.histplot(data=df,x="pm2.5",bins=60,kde=True,color="#4472C4",ax=ax); ax.set(title="PM2.5 distribution with KDE",xlabel="PM2.5",ylabel="Frequency"); save(fig,"01_pm25_hist_kde")
fig,ax=plt.subplots(figsize=(9,6)); sns.boxplot(data=df,x="rain_level",y="TEMP",order=["No rain","Light rain","Heavy rain"],palette="Blues",ax=ax); ax.set(title="Temperature by rain level",xlabel="Rain level",ylabel="TEMP"); save(fig,"02_rain_temperature_boxplot")
corr=df[["pm2.5","TEMP","PRES","Ir"]].corr(); corr.to_csv(OUT/"03_correlation_matrix.csv",encoding="utf-8-sig"); fig,ax=plt.subplots(figsize=(8,6)); sns.heatmap(corr,annot=True,fmt=".2f",cmap="RdBu_r",center=0,square=True,ax=ax); ax.set_title("Four-field correlation heatmap"); save(fig,"03_correlation_heatmap")
sample=df.sample(min(8000,len(df)),random_state=42); fig,ax=plt.subplots(figsize=(9,6)); sns.regplot(data=sample,x="TEMP",y="pm2.5",scatter_kws={"s":8,"alpha":.2},line_kws={"color":"red"},ci=95,ax=ax); ax.set(title=f"TEMP vs PM2.5 regression (r={df.TEMP.corr(df['pm2.5']):.3f})",xlabel="TEMP",ylabel="PM2.5"); save(fig,"04_temp_pm25_regplot")
weekly=df.set_index("timestamp").groupby("rain_level")["pm2.5"].resample("W").mean().reset_index(); weekly["rain_level"]=pd.Categorical(weekly["rain_level"],["No rain","Light rain","Heavy rain"],ordered=True)
g=sns.relplot(data=weekly,x="timestamp",y="pm2.5",col="rain_level",col_order=["No rain","Light rain","Heavy rain"],kind="line",height=4,aspect=1.2,facet_kws={"sharey":True}); g.set_axis_labels("Time","Weekly mean PM2.5"); g.set_titles("{col_name}"); g.fig.suptitle("Rain-level faceted PM2.5 time series",y=1.04); g.fig.savefig(FIG/"05_rain_faceted_timeseries.png",dpi=180,bbox_inches="tight"); plt.close(g.fig)
stats=df.groupby("rain_level",observed=False).agg(temp_median=("TEMP","median"),temp_iqr=("TEMP",lambda x:x.quantile(.75)-x.quantile(.25)),pm25_mean=("pm2.5","mean"),pm25_std=("pm2.5","std")).reset_index(); stats.to_csv(OUT/"04_rain_level_statistics.csv",index=False,encoding="utf-8-sig")
with PdfPages(OUT/"seaborn_figures.pdf") as pdf:
    for p in sorted(FIG.glob("*.png")):
        im=plt.imread(p); fig,ax=plt.subplots(figsize=(11,7)); ax.imshow(im); ax.axis("off"); ax.set_title(p.stem); pdf.savefig(fig); plt.close(fig)
report=f"""# Seaborn Beijing Air Quality Analysis

The source contains **{raw_rows} hourly records**. Timestamps were assembled and sorted. `Ir` is the source-defined **cumulative rainfall hours**, not millimetres; therefore the teaching labels are documented as operational thresholds: 0 = No rain, 0<Ir<=2 = Light rain, Ir>2 = Heavy rain. These labels are not precipitation intensity measurements.

Negative values were marked invalid and excluded before linear interpolation. Internal gaps were interpolated in time order and endpoint gaps were forward/back filled; the quality outputs record the affected counts. PM2.5 extreme values are retained as observations unless negative, so the histogram and regression do not silently remove high pollution events.

TEMP vs PM2.5 Pearson r is **{df.TEMP.corr(df['pm2.5']):.3f}**. The regplot band is a descriptive 95% fit interval, not a rigorous time-series confidence interval. All five required plots are made with Seaborn; correlation does not establish causality.
"""
(ROOT/"analysis_report.md").write_text(report,encoding="utf-8"); print("Seaborn complete:",ROOT)
