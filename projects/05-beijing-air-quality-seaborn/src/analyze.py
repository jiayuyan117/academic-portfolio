"""Beijing PM2.5, 2010-2014: ventilation associations and missing-data audit.

Input  : data/PRSA_data_2010.1.1-2014.12.31.csv  (UCI Beijing PM2.5 dataset)
Output : figures/*.png   seven Seaborn figures
         outputs/*.csv   the tables behind each figure
         outputs/findings.json  every number quoted in README.md

Two decisions drive this script.

1. Gap-aware imputation. 2,067 PM2.5 hours are missing, spread over 214 gaps
   whose longest run is 155 consecutive hours. Interpolating all of them, as the
   original coursework did, draws a smooth ramp through what may have been an
   entire haze episode. Only gaps of at most MAX_GAP_HOURS are filled; longer
   gaps stay missing in a separate policy-audit series. Headline analyses use
   original observed values only, excluding all 2,067 missing hours.

2. Rank correlation first. PM2.5 against temperature gives Pearson -0.091 but
   Spearman +0.011. Both are small; their different signs motivate inspecting
   the conditional shape rather than assuming a linear relationship. Figures
   lead with binned conditional means and Spearman coefficients.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "PRSA_data_2010.1.1-2014.12.31.csv"
FIGURES = ROOT / "figures"
OUTPUTS = ROOT / "outputs"

# Gaps longer than this are left missing rather than interpolated.
MAX_GAP_HOURS = 3

# China Ambient Air Quality Standard GB 3095-2012 grade II daily limit, and the
# "severe pollution" AQI boundary. Both are daily standards shown on hourly data
# as reference lines only.
CN_GRADE_II = 75
SEVERE = 250

DRIVERS = ["Iws", "DEWP", "PRES", "TEMP", "Ir", "Is"]
DRIVER_LABELS = {
    "Iws": "Cumulated wind speed",
    "DEWP": "Dew point",
    "PRES": "Pressure",
    "TEMP": "Temperature",
    "Ir": "Cumulated rain hours",
    "Is": "Cumulated snow hours",
}
WIND_LABELS = {"NW": "NW", "NE": "NE", "SE": "SE", "cv": "Calm / variable"}
WIND_ORDER = ["NW", "NE", "SE", "cv"]

sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams.update({
    "figure.dpi": 110,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "font.family": "DejaVu Sans",
    "axes.titleweight": "bold",
})


def gap_runs(is_missing: np.ndarray) -> np.ndarray:
    """Lengths of consecutive-missing runs in a boolean mask."""
    runs, current = [], 0
    for flag in is_missing:
        if flag:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return np.array(runs, dtype=int)


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the hourly frame and the gap audit table."""
    df = pd.read_csv(DATA, na_values=["NA"])
    df["timestamp"] = pd.to_datetime(df[["year", "month", "day", "hour"]])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # The index must be a complete hourly series before gap lengths mean anything.
    steps = df["timestamp"].diff().dropna().unique()
    assert len(steps) == 1 and steps[0] == pd.Timedelta(hours=1), \
        "input is not a gap-free hourly index; gap lengths would be meaningless"

    # Negative readings are physically impossible in these fields.
    for column in ["pm2.5", "Iws", "Ir", "Is"]:
        df.loc[df[column] < 0, column] = np.nan

    missing = df["pm2.5"].isna().to_numpy()
    runs = gap_runs(missing)

    # Fill a gap only if the *whole* gap is short. pandas' interpolate(limit=n)
    # would instead fill the first n hours of a 155-hour gap, which is the
    # behaviour this project is trying to avoid.
    short_gap = np.zeros(len(df), dtype=bool)
    start = None
    for index, flag in enumerate(missing):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            if index - start <= MAX_GAP_HOURS:
                short_gap[start:index] = True
            start = None
    interpolated = df["pm2.5"].interpolate("linear", limit_area="inside")
    df["pm25_filled"] = df["pm2.5"].where(~short_gap, interpolated)
    df["pm25_imputed"] = short_gap & interpolated.notna()


    buckets = [(1, "1 hour"), (3, "2-3 hours"), (6, "4-6 hours"),
               (12, "7-12 hours"), (24, "13-24 hours"), (10 ** 6, "over 24 hours")]
    rows, lower = [], 0
    for upper, label in buckets:
        selected = runs[(runs > lower) & (runs <= upper)]
        rows.append({"gap_length": label, "gaps": len(selected),
                     "missing_hours": int(selected.sum()),
                     "interpolated": upper <= MAX_GAP_HOURS})
        lower = upper
    audit = pd.DataFrame(rows)
    return df, audit


def save(fig, name: str, note: str) -> None:
    fig.text(0.01, -0.02, note, fontsize=8, color="#7a8a99", ha="left", va="top")
    fig.savefig(FIGURES / f"{name}.png")
    plt.close(fig)


def fig_gap_audit(audit: pd.DataFrame) -> None:
    """The methodological figure: what is filled, and what is deliberately not."""
    kept = audit.loc[~audit["interpolated"], "missing_hours"].sum()
    share = kept / audit["missing_hours"].sum()
    longest = audit.loc[audit["missing_hours"] > 0, "gap_length"].iloc[-1]
    fig, ax = plt.subplots(figsize=(9, 5))
    colours = ["#1f6fb2" if flag else "#c9d3dc" for flag in audit["interpolated"]]
    bars = ax.bar(audit["gap_length"], audit["missing_hours"], color=colours, width=0.62)
    for bar, gaps in zip(bars, audit["gaps"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 20,
                f"{int(bar.get_height())} h\n({gaps} gaps)", ha="center", fontsize=8.5,
                color="#425362")
    ax.set_ylabel("Missing PM2.5 hours")
    ax.set_xlabel("Length of the gap the hour belongs to")
    ax.set_title(f"A short-gap policy leaves {share:.0%} of missing hours unfilled\n"
                 f"2,067 absent PM2.5 hours, by gap length "
                 f"(largest bucket: {longest})")

    ax.set_ylim(0, audit["missing_hours"].max() * 1.25)
    handles = [plt.Rectangle((0, 0), 1, 1, color="#1f6fb2"),
               plt.Rectangle((0, 0), 1, 1, color="#c9d3dc")]
    ax.legend(handles, [f"policy permits filling (gap <= {MAX_GAP_HOURS} h)",
                        "policy leaves missing"], loc="upper left")
    save(fig, "01_missing_data_gap_audit",
         "Policy audit only. All headline summaries use observed values and exclude "
         "all 2,067 missing hours. The longest gap is 155 consecutive hours.")


def fig_distribution(df: pd.DataFrame) -> None:
    observed = df["pm2.5"].dropna()
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.histplot(x=observed, bins=70, kde=True, color="#1f6fb2", ax=ax)
    ax.set_xscale("log")
    for value, label, colour in [(CN_GRADE_II, f"CN grade II daily limit ({CN_GRADE_II})", "#e8a33d"),
                                 (SEVERE, f"daily AQI reference ({SEVERE})", "#d9534f")]:
        ax.axvline(value, color=colour, linestyle="--", linewidth=1.6)
        ax.text(value * 1.05, ax.get_ylim()[1] * 0.92, label, fontsize=8.5, color=colour)
    share = (observed > CN_GRADE_II).mean()
    severe_share = (observed > SEVERE).mean()
    ax.set_xlabel("PM2.5 (µg/m³, log scale)")
    ax.set_ylabel("Hours")
    ax.set_title(f"{share:.1%} of observed hourly PM2.5 readings exceed 75 µg/m³\n"
                 f"{severe_share:.1%} exceed 250 µg/m³; these are not daily compliance rates")
    save(fig, "02_pm25_distribution",
         "Observed hours only; imputed values are excluded. The two reference "
         "lines are daily standards, shown on hourly data for orientation only.")


def ventilation_table(df: pd.DataFrame) -> pd.DataFrame:
    observed = df.dropna(subset=["pm2.5"]).copy()
    observed["iws_decile"] = pd.qcut(observed["Iws"], 10, labels=False, duplicates="drop")
    table = observed.groupby("iws_decile").agg(
        hours=("pm2.5", "size"), mean_pm25=("pm2.5", "mean"),
        median_pm25=("pm2.5", "median"),
        iws_lower=("Iws", "min"), iws_upper=("Iws", "max")).reset_index()
    return table


def fig_ventilation(df: pd.DataFrame, table: pd.DataFrame) -> None:
    """Describe the association with the source's cumulated-wind-speed field.

    Args:
        df: Hourly observations, including original missing pollution readings.
        table: Cumulated-wind deciles with counts and median pollution.
    """
    observed = df.dropna(subset=["pm2.5"]).copy()
    observed["iws_decile"] = pd.qcut(observed["Iws"], 10, labels=False, duplicates="drop")
    ratio = table["median_pm25"].iloc[0] / table["median_pm25"].iloc[-1]

    fig, ax = plt.subplots(figsize=(9.5, 5))
    sns.boxplot(data=observed, x="iws_decile", y="pm2.5", showfliers=False,
                color="#1f6fb2", width=0.65, ax=ax)
    ax.plot(range(len(table)), table["median_pm25"], color="#d9534f", marker="o",
            linewidth=2, label="Median PM2.5")
    ax.axhline(CN_GRADE_II, color="#e8a33d", linestyle="--", linewidth=1.4,
               label=f"CN grade II daily limit ({CN_GRADE_II})")
    ax.set_xlabel("Cumulated wind speed, decile (1 = lowest)")
    ax.set_ylabel("PM2.5 (µg/m³)")
    ax.set_xticks(range(len(table)), [str(i + 1) for i in range(len(table))])
    ax.set_title(f"Median PM2.5 is {ratio:.1f}x higher in the lowest cumulated-wind decile\n"
                 f"than in the highest, Beijing 2010-2014")
    ax.legend(loc="upper right")
    save(fig, "03_ventilation_wind_speed",
         "Spearman rho = -0.360 between cumulated wind speed and PM2.5, against "
         "+0.011 for temperature. Outliers hidden for readability; medians use all "
         "observed hours.")


def fig_wind_direction(df: pd.DataFrame) -> None:
    observed = df.dropna(subset=["pm2.5"]).copy()
    observed["wind"] = observed["cbwd"].map(WIND_LABELS)
    order = [WIND_LABELS[key] for key in WIND_ORDER]
    medians = observed.groupby("wind")["pm2.5"].median()

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.violinplot(data=observed, x="wind", y="pm2.5", order=order, cut=0,
                   density_norm="width", palette="Blues_r", hue="wind",
                   legend=False, ax=ax)
    ax.set_yscale("log")
    labels = []
    for label in order:
        hours = int((observed["wind"] == label).sum())
        labels.append(f"{label}\nmedian {medians[label]:.0f} µg/m³\n{hours:,} hours")
    ax.set_xticks(range(len(order)), labels)
    ax.axhline(CN_GRADE_II, color="#e8a33d", linestyle="--", linewidth=1.4)
    cleanest, dirtiest = medians.min(), medians.max()

    ax.set_xlabel("Combined wind direction")
    ax.set_ylabel("PM2.5 (µg/m³, log scale)")
    ax.set_title("PM2.5 differs across recorded wind-direction categories\n"
                 f"median PM2.5 of {cleanest:.0f} vs {dirtiest:.0f} µg/m³, "
                 f"a {dirtiest / cleanest:.1f}x difference")

    save(fig, "04_wind_direction",
         "Descriptive distributions; hourly dependence and seasonality are not controlled. "
         "Direction is a source-defined combined category, not a measured bearing.")


def correlation_table(df: pd.DataFrame) -> pd.DataFrame:
    observed = df.dropna(subset=["pm2.5"])
    rows = []
    for column in DRIVERS:
        pearson, p_pearson = stats.pearsonr(observed[column], observed["pm2.5"])
        spearman, p_spearman = stats.spearmanr(observed[column], observed["pm2.5"])
        rows.append({"variable": column, "label": DRIVER_LABELS[column],
                     "pearson_r": pearson, "pearson_p": p_pearson,
                     "spearman_rho": spearman, "spearman_p": p_spearman,
                     "sign_disagrees": np.sign(pearson) != np.sign(spearman)})
    return pd.DataFrame(rows)


def fig_pearson_vs_spearman(table: pd.DataFrame) -> None:
    """Why the coursework's temperature finding was an artefact of the statistic."""
    fig, ax = plt.subplots(figsize=(9, 5))
    y = np.arange(len(table))
    ax.barh(y - 0.19, table["pearson_r"], height=0.36, color="#8a99a8", label="Pearson r")
    ax.barh(y + 0.19, table["spearman_rho"], height=0.36, color="#1f6fb2",
            label="Spearman rho")
    for index, row in table.iterrows():
        if row["sign_disagrees"]:
            ax.text(0.015, index, "  sign flips", va="center", fontsize=9,
                    color="#d9534f", fontweight="bold")
    ax.axvline(0, color="#425362", linewidth=1)
    ax.set_yticks(y, table["label"])
    ax.invert_yaxis()
    ax.set_xlabel("Correlation with PM2.5")
    ax.set_title("Pearson and Spearman disagree on temperature's sign\n"
                 "which is why the linear coefficient should not be the headline")
    ax.legend(loc="lower right")
    save(fig, "05_pearson_vs_spearman",
         "Observed hours only. Different signs alone do not prove non-monotonicity; "
         "inspect the conditional-median plot. Neither coefficient identifies causation.")


def fig_temperature_shape(df: pd.DataFrame) -> pd.DataFrame:
    """Inspect binned temperature associations without identifying their cause."""
    observed = df.dropna(subset=["pm2.5"]).copy()
    observed["temp_bin"] = pd.cut(observed["TEMP"], bins=range(-20, 45, 5))
    table = observed.groupby("temp_bin", observed=True).agg(
        hours=("pm2.5", "size"), median_pm25=("pm2.5", "median"),
        q25=("pm2.5", lambda s: s.quantile(0.25)),
        q75=("pm2.5", lambda s: s.quantile(0.75))).reset_index()
    table["temp_mid"] = [interval.mid for interval in table["temp_bin"]]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.fill_between(table["temp_mid"], table["q25"], table["q75"], color="#1f6fb2",
                    alpha=0.18, label="Interquartile range")
    ax.plot(table["temp_mid"], table["median_pm25"], color="#1f6fb2", marker="o",
            linewidth=2.2, label="Median PM2.5")
    ax.axhline(CN_GRADE_II, color="#e8a33d", linestyle="--", linewidth=1.4,
               label=f"CN grade II daily limit ({CN_GRADE_II})")
    ax.set_xlabel("Temperature (°C, 5° bins)")
    ax.set_ylabel("PM2.5 (µg/m³)")
    peak_cold = table.loc[table["temp_mid"] < 10, "median_pm25"].idxmax()
    peak_warm = table.loc[table["temp_mid"] >= 10, "median_pm25"].idxmax()
    ax.set_title("Binned temperature summaries vary across the observed range\n"
                 f"local maxima near {table.loc[peak_cold, 'temp_mid']:.0f} °C and "
                 f"{table.loc[peak_warm, 'temp_mid']:.0f} °C, cleanest air at both extremes")
    ax.legend(loc="upper center")
    save(fig, "06_temperature_shape",
         "Binned medians and IQR, not confidence intervals. Shape depends on bins "
         "and uncontrolled factors such as season. Opposite correlation signs alone "
         "do not establish non-monotonicity.")

    return table.drop(columns="temp_bin")


def fig_season_hour(df: pd.DataFrame) -> pd.DataFrame:
    """Month x hour mean PM2.5 -- the seasonal and diurnal structure together."""
    observed = df.dropna(subset=["pm2.5"])
    grid = observed.pivot_table(index="month", columns="hour", values="pm2.5",
                                aggfunc="mean")
    fig, ax = plt.subplots(figsize=(11, 5.2))
    sns.heatmap(grid, cmap="YlOrRd", linewidths=0.4, linecolor="white",
                cbar_kws={"label": "Mean PM2.5 (µg/m³)"}, ax=ax)
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Month")
    ax.set_yticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], rotation=0)
    ax.set_title("Two cycles at once: a winter heating season and a nightly trough-to-peak swing\n"
                 "cleanest hours are early afternoon; dirtiest are after midnight in winter")
    save(fig, "07_season_hour_heatmap",
         "Mean of observed hours in each month-hour cell across 2010-2014. "
         "Means, not medians, are used so single severe episodes remain visible.")
    return grid.reset_index()


def main() -> None:
    FIGURES.mkdir(exist_ok=True)
    OUTPUTS.mkdir(exist_ok=True)

    df, audit = load()
    correlations = correlation_table(df)
    ventilation = ventilation_table(df)

    fig_gap_audit(audit)
    fig_distribution(df)
    fig_ventilation(df, ventilation)
    fig_wind_direction(df)
    fig_pearson_vs_spearman(correlations)
    temperature = fig_temperature_shape(df)
    season_hour = fig_season_hour(df)

    audit.to_csv(OUTPUTS / "01_missing_data_gap_audit.csv", index=False)
    correlations.to_csv(OUTPUTS / "02_pm25_correlations.csv", index=False)
    ventilation.to_csv(OUTPUTS / "03_wind_speed_deciles.csv", index=False)
    temperature.to_csv(OUTPUTS / "04_temperature_bins.csv", index=False)
    season_hour.to_csv(OUTPUTS / "05_month_hour_means.csv", index=False)
    wind = df.dropna(subset=["pm2.5"]).groupby("cbwd")["pm2.5"].agg(
        hours="size", mean="mean", median="median").reset_index()
    wind.to_csv(OUTPUTS / "06_wind_direction.csv", index=False)

    observed = df["pm2.5"].dropna()
    runs = gap_runs(df["pm2.5"].isna().to_numpy())
    iws = ventilation
    spearman = correlations.set_index("variable")["spearman_rho"]
    pearson = correlations.set_index("variable")["pearson_r"]
    findings = {
        "analysis_basis": "original observed PM2.5 only; no imputed values used",
        "observed_pm25_hours": int(observed.size),
        "analysis_excluded_missing_hours": int(df["pm2.5"].isna().sum()),
        "imputation_fields_scope": "separate short-gap policy audit, not analysis inputs",
        "hourly_rows": int(len(df)),
        "missing_pm25_hours": int(df["pm2.5"].isna().sum()),
        "missing_share": round(float(df["pm2.5"].isna().mean()), 4),
        "gap_count": int(len(runs)),
        "longest_gap_hours": int(runs.max()),
        "hours_interpolated": int(df["pm25_imputed"].sum()),
        "hours_left_missing": int(df["pm25_filled"].isna().sum()),
        "share_above_cn_grade_ii": round(float((observed > CN_GRADE_II).mean()), 4),
        "share_severe": round(float((observed > SEVERE).mean()), 4),
        "spearman_wind_speed": round(float(spearman["Iws"]), 3),
        "spearman_temperature": round(float(spearman["TEMP"]), 3),
        "pearson_temperature": round(float(pearson["TEMP"]), 3),
        "median_pm25_calmest_decile": float(iws["median_pm25"].iloc[0]),
        "median_pm25_windiest_decile": float(iws["median_pm25"].iloc[-1]),
        "median_pm25_by_wind": {
            WIND_LABELS[row.cbwd]: float(row.median) for row in wind.itertuples()},
    }
    (OUTPUTS / "findings.json").write_text(
        json.dumps(findings, indent=2), encoding="utf-8")
    print(json.dumps(findings, indent=2))


if __name__ == "__main__":
    main()





