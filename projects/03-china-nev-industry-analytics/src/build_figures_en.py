"""Render the English figure set for the China NEV analysis.

Validates independent inputs and provenance in ``data/source/``, regenerates
the seven derived tables using the shared pipeline and writes English PNGs.
Selected observations are source-checked; 2025 charging has a reporting break.

Run from anywhere:  python src/build_figures_en.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from data_pipeline import (build_tables, NOTE_EN, CHARGING_BREAK_YEAR, CHARGING_NOTE_EN,
                           charging_segments, plot_charging_segments)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHARTS = ROOT / "charts_en"

INK = "#1b2a3a"
GRID = "#d7dee6"
BLUE = "#1f6fb2"
TEAL = "#179a9a"
AMBER = "#e8a33d"
CORAL = "#d9534f"
GREY = "#8a99a8"

plt.rcParams.update({
    "figure.dpi": 110,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "font.family": "DejaVu Sans",
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.7,
    "legend.frameon": False,
})

def load() -> tuple[dict[str, pd.DataFrame], float]:
    return build_tables(write=True)


def millions(value, _pos=None) -> str:
    """Format a 10k-unit value as millions of vehicles."""
    return f"{value / 100:.0f}"


def finish(fig, ax, name: str, source: str) -> None:
    """Apply shared cosmetics, stamp the data note, and save."""
    for spine in ("top", "right"):
        if spine in ax.spines:
            ax.spines[spine].set_visible(False)
    fig.text(0.01, -0.03, f"{NOTE_EN}\n{source}", fontsize=8, color=GREY, ha="left", va="top")
    fig.savefig(CHARTS / name)
    plt.close(fig)


def charging_break(ax):
    ax.axvline(CHARGING_BREAK_YEAR - 0.5, color=CORAL, linestyle="--", linewidth=1.2)
    ax.text(CHARGING_BREAK_YEAR - 0.55, 0.97, "2025 scope break",
            transform=ax.get_xaxis_transform(), ha="right", va="top", fontsize=8, color=CORAL)


def fig_sales(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df.year, df.nev_sales_10k / 100, color=BLUE, width=0.62, label="NEV sales")
    ax.set_ylabel("NEV sales (million units)")
    ax.set_xlabel("Year")
    ax.set_title(f"Compiled NEV sales: {df.nev_sales_10k.iloc[-1] / df.nev_sales_10k.iloc[0]:.2f}x "
                 f"the starting level, {df.year.iloc[0]}-{df.year.iloc[-1]}\n"
                 "All vehicle types including exports; selected observations verified")
    twin = ax.twinx()
    twin.plot(df.year, df.nev_share_of_new_sales_pct, color=CORAL, marker="o",
              linewidth=2.2, label="Share of new vehicle sales")
    twin.axhline(50, color=GREY, linestyle=":", linewidth=1.2)
    twin.text(df.year.max(), 51, "50% of new sales", fontsize=8, color=GREY, ha="right")

    twin.set_ylabel("Share of new vehicle sales (%)", color=CORAL)
    twin.set_ylim(0, 60)
    twin.grid(False)
    handles = ax.get_legend_handles_labels()[0] + twin.get_legend_handles_labels()[0]
    labels = ax.get_legend_handles_labels()[1] + twin.get_legend_handles_labels()[1]
    ax.legend(handles, labels, loc="upper left")
    ax.set_xticks(df.year)
    finish(fig, ax, "01_sales_and_penetration.png",
           "2025: CAAM via MIIT/MOFCOM (2026-01-15), government republication; denominator includes exports.\n"
           f"Published share {df.reported_share_pct.iloc[-1]:.1f}%; calculated from rounded counts "
           f"{df.nev_share_of_new_sales_pct.iloc[-1]:.2f}%.")


def fig_charging(charging: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(charging.year, charging.nev_fleet_10k / 100, color=BLUE, marker="o",
            linewidth=2.2, label="NEV fleet")
    plot_charging_segments(ax, charging, "chargers_total_10k", scale=100, color=TEAL, marker="s",
                           linewidth=2.2, label="Charging counts (scope break)")
    charging_break(ax)
    ax.set_ylabel("Million units")
    ax.set_xlabel("Year")
    ax.set_title("Fleet and charging counts: 2025 NEA reporting break\n"
                 f"2025 snapshot: {charging.vehicles_per_charger.iloc[-1]:.2f} vehicles per connector")
    twin = ax.twinx()
    for i, segment in enumerate(charging_segments(charging)):
        twin.bar(segment.year, segment.vehicles_per_charger, color=AMBER, alpha=0.30,
                 width=0.55, hatch="//" if i else None,
                 label="Vehicles per point/connector" if i == 0 else "2025 NEA revised scope")
    twin.set_ylabel("Vehicles per charging point", color=AMBER)
    twin.set_ylim(0, 4)
    twin.grid(False)
    handles = ax.get_legend_handles_labels()[0] + twin.get_legend_handles_labels()[0]
    labels = ax.get_legend_handles_labels()[1] + twin.get_legend_handles_labels()[1]
    ax.legend(handles, labels, loc="upper left")
    ax.set_xticks(charging.year)
    finish(fig, ax, "02_fleet_vs_charging.png",
           CHARGING_NOTE_EN + "\nNEA: 2025-07-31 scope notice; 2026-01-21 year-end release. Counts do not measure power or public access.")


def fig_charger_mix(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, segment in enumerate(charging_segments(df)):
        ax.bar(segment.year, segment.chargers_public_10k / 100, color=BLUE, width=0.55,
               label="Public" if i == 0 else "_nolegend_", hatch="//" if i else None)
        ax.bar(segment.year, segment.chargers_private_10k / 100,
               bottom=segment.chargers_public_10k / 100, color=TEAL, width=0.55,
               label="Private" if i == 0 else "2025 revised scope (hatched)", hatch="//" if i else None)
    charging_break(ax)
    ax.set_ylabel("Charging points (millions)")
    ax.set_xlabel("Year")
    ax.set_title("Charging composition: EVCIPA series / 2025 NEA snapshot\n"
                 f"2025 public connector share: {df.public_share_pct.iloc[-1]:.2f}% (new scope)")
    twin = ax.twinx()
    plot_charging_segments(twin, df, "public_share_pct", color=CORAL, marker="o",
                           linewidth=2.2, label="Public share")
    twin.set_ylabel("Public share (%)", color=CORAL)
    twin.set_ylim(0, 60)
    twin.grid(False)
    handles = ax.get_legend_handles_labels()[0] + twin.get_legend_handles_labels()[0]
    labels = ax.get_legend_handles_labels()[1] + twin.get_legend_handles_labels()[1]
    ax.legend(handles, labels, loc="upper left")
    ax.set_xticks(df.year)
    finish(fig, ax, "03_charger_mix.png",
           CHARGING_NOTE_EN + "\nPrivate = total minus public; 2025 matches NEA's reported private count. Hatched bars use the new scope.")


def fig_battery(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df.year, df.lfp_gwh, color=BLUE, width=0.62, label="LFP")
    ax.bar(df.year, df.nmc_gwh, bottom=df.lfp_gwh, color=AMBER, width=0.62,
           label="NMC / ternary")
    ax.set_ylabel("Battery installed in new vehicles (GWh)")
    ax.set_xlabel("Year")
    ax.set_title(f"LFP share within the two-chemistry subtotal: {df.lfp_share_pct.iloc[0]:.1f}% "
                 f"to {df.lfp_share_pct.iloc[-1]:.1f}%\n"
                 f"{df.year.iloc[0]}-{df.year.iloc[-1]} (selected observations verified)")
    twin = ax.twinx()
    twin.plot(df.year, df.lfp_share_pct, color=CORAL, marker="o", linewidth=2.2,
              label="LFP share")
    twin.set_ylabel("LFP share (%)", color=CORAL)
    twin.set_ylim(0, 100)
    twin.grid(False)
    handles = ax.get_legend_handles_labels()[0] + twin.get_legend_handles_labels()[0]
    labels = ax.get_legend_handles_labels()[1] + twin.get_legend_handles_labels()[1]
    ax.legend(handles, labels, loc="upper left")
    ax.set_xticks(df.year)
    finish(fig, ax, "04_battery_chemistry.png",
           f"LFP + ternary = {df.total_gwh.iloc[-1]:.1f} GWh in {df.year.iloc[-1]}. "
           "Denominator is LFP + ternary only; 2025 counts supported by Securities Times (2026-01-16), secondary evidence.")


def fig_powertrain(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df.year, df.bev_sales_10k / 100, color=BLUE, width=0.6, label="Battery electric")
    ax.bar(df.year, df.phev_sales_10k / 100, bottom=df.bev_sales_10k / 100, color=TEAL,
           width=0.6, label="Plug-in hybrid")
    ax.set_ylabel("Sales (million units)")
    ax.set_xlabel("Year")
    ax.set_title(f"PHEV / (BEV + PHEV): {df.phev_share_pct.iloc[0]:.1f}% to {df.phev_share_pct.iloc[-1]:.1f}%\n"
                 f"Latest change: {df.phev_share_pct.iloc[-1]-df.phev_share_pct.iloc[-2]:+.2f} pp "
                 "(all vehicle types)")
    twin = ax.twinx()
    twin.plot(df.year, df.phev_share_pct, color=CORAL, marker="o", linewidth=2.2,
              label="PHEV share")
    twin.set_ylabel("PHEV share (%)", color=CORAL)
    twin.set_ylim(0, 50)
    twin.grid(False)
    handles = ax.get_legend_handles_labels()[0] + twin.get_legend_handles_labels()[0]
    labels = ax.get_legend_handles_labels()[1] + twin.get_legend_handles_labels()[1]
    ax.legend(handles, labels, loc="upper left")
    ax.set_xticks(df.year)
    finish(fig, ax, "05_powertrain_mix.png",
           "All vehicle types; BEV + PHEV subtotal excludes fuel-cell vehicles. 2021: MIIT/SCIO (2022-01-12).\n"
           "2025: Economic Observer reporting CAAM (2026-01-15); 2022-2024 values remain unverified.")


def fig_exports(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df.year, df.nev_exports_10k / 100, color=BLUE, width=0.6, label="NEV exports")
    ax.bar(df.year, df.ice_exports_10k / 100, bottom=df.nev_exports_10k / 100, color=GREY,
           width=0.6, label="Other exports (residual)")
    ax.set_ylabel("Vehicle exports (million units)")
    ax.set_xlabel("Year")
    ax.set_title(f"NEV share of compiled exports: about {df.nev_share_of_exports_pct.iloc[0]:.1f}% "
                 f"to {df.nev_share_of_exports_pct.iloc[-1]:.1f}%\n"
                 f"{df.year.iloc[0]}-{df.year.iloc[-1]} (2020 volume is approximate)")
    twin = ax.twinx()
    twin.plot(df.year, df.nev_share_of_exports_pct, color=CORAL, marker="o", linewidth=2.2,
              label="NEV share of exports")
    twin.set_ylabel("NEV share of exports (%)", color=CORAL)
    twin.set_ylim(0, 50)
    twin.grid(False)
    handles = ax.get_legend_handles_labels()[0] + twin.get_legend_handles_labels()[0]
    labels = ax.get_legend_handles_labels()[1] + twin.get_legend_handles_labels()[1]
    ax.legend(handles, labels, loc="upper left")
    ax.set_xticks(df.year)
    finish(fig, ax, "06_exports.png",
           "2025: CAAM via MIIT/MOFCOM (2026-01-15), government republication. 2020 NEV volume: about 70,000.\n"
           "2020 share is approximate; earlier annual values and kit coverage are not fully verified.")


def fig_carbon(df: pd.DataFrame, factor: float) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df.year, df.annual_co2_avoided_100mt, color=TEAL, width=0.62,
           label="Annual avoided CO2 (scenario)")
    ax.set_ylabel("Avoided CO2 (hundred million tonnes/year)")
    ax.set_xlabel("Year")
    ax.set_title("Illustrative scenario; author-selected assumption:\n"
                 f"cumulative {df.cumulative_co2_avoided_100mt.iloc[-1] / 10:.3f} Gt "
                 f"through {df.year.iloc[-1]}")
    twin = ax.twinx()
    twin.plot(df.year, df.cumulative_co2_avoided_100mt, color=CORAL, marker="o",
              linewidth=2.2, label="Cumulative avoided CO2 (scenario)")
    twin.set_ylabel("Cumulative avoided CO2 (hundred million tonnes)", color=CORAL)
    twin.grid(False)
    handles = ax.get_legend_handles_labels()[0] + twin.get_legend_handles_labels()[0]
    labels = ax.get_legend_handles_labels()[1] + twin.get_legend_handles_labels()[1]
    ax.legend(handles, labels, loc="upper left")
    ax.set_xticks(df.year)
    finish(fig, ax, "07_carbon_scenario.png",
           f"Author-selected assumption: {factor:g} t CO2/vehicle-year x year-end fleet; not an external statistic.\n"
           "Year-end stocks are not annual vehicle-years. Excludes grid, mileage and manufacturing variation; not an LCA.")


def fig_dashboard(f: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5))
    fig.suptitle("China NEV dashboard, 2015-2025\nSelected observations verified; charging scope changes in 2025",
                 fontsize=15, fontweight="bold", color=INK)

    ax = axes[0][0]
    ax.bar(f["sales"].year, f["sales"].nev_sales_10k / 100, color=BLUE, width=0.62)
    ax.set_title("NEV sales (million units)")
    ax.set_xticks(f["sales"].year[::2])

    ax = axes[0][1]
    ax.plot(f["sales"].year, f["sales"].nev_share_of_new_sales_pct, color=CORAL,
            marker="o", linewidth=2.2)
    ax.axhline(50, color=GREY, linestyle=":", linewidth=1.2)
    ax.set_title("All-vehicle sales share incl. exports (%)")
    ax.set_xticks(f["sales"].year[::2])

    ax = axes[1][0]
    ax.bar(f["battery"].year, f["battery"].lfp_gwh, color=BLUE, width=0.62, label="LFP")
    ax.bar(f["battery"].year, f["battery"].nmc_gwh, bottom=f["battery"].lfp_gwh,
           color=AMBER, width=0.62, label="NMC")
    ax.set_title("Two-chemistry installations (GWh)")
    ax.legend(loc="upper left")
    ax.set_xticks(f["battery"].year)

    ax = axes[1][1]
    plot_charging_segments(ax, f["charging"], "vehicles_per_charger", color=TEAL,
                           marker="s", linewidth=2.2)
    charging_break(ax)
    ax.set_title("Fleet / charging counts: 2025 scope break")
    ax.set_ylim(0, 4)
    ax.set_xticks(f["charging"].year)

    for row in axes:
        for ax in row:
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    fig.text(0.01, 0.005, NOTE_EN + "\n2025 sales denominator includes exports. " + CHARGING_NOTE_EN,
             fontsize=8, color=GREY)
    fig.savefig(CHARTS / "08_dashboard.png")
    plt.close(fig)


def main() -> None:
    CHARTS.mkdir(exist_ok=True)
    f, factor = load()
    fig_sales(f["sales"])
    fig_charging(f["charging"])
    fig_charger_mix(f["charging"])
    fig_battery(f["battery"])
    fig_powertrain(f["powertrain"])
    fig_exports(f["exports"])
    fig_carbon(f["carbon"], factor)
    fig_dashboard(f)
    written = sorted(p.name for p in CHARTS.glob("*.png"))
    print(f"Wrote {len(written)} figures to {CHARTS}:")
    for name in written:
        print(" -", name)


if __name__ == "__main__":
    main()






