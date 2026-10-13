"""Render the English figure set for the China NEV analysis.

Reads the seven tables in ``data/`` and writes English-labelled PNGs to
``charts_en/``. The Chinese figure set is produced by ``nev_visualization.py``,
which also writes those tables; this script is a presentation layer only and
performs no new estimation.

Run from anywhere:  python src/build_figures_en.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

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

TABLES = {
    "sales": "01_汽车与新能源汽车产销_2015-2025.csv",
    "fleet": "02_新能源汽车保有量_2015-2025.csv",
    "charging": "03_充电基础设施_2020-2025.csv",
    "battery": "04_动力电池装车量_2018-2025.csv",
    "powertrain": "05_新能源乘用车技术路线_2021-2025.csv",
    "exports": "06_新能源汽车出口_2020-2025.csv",
    "carbon": "07_绿色低碳成效情景估算_2015-2025.csv",
}

# Chinese column name -> English column name, applied across all seven tables.
COLUMNS = {
    "年份": "year",
    "汽车总销量_万辆": "total_vehicle_sales_10k",
    "新能源汽车产量_万辆": "nev_output_10k",
    "新能源汽车销量_万辆": "nev_sales_10k",
    "新能源汽车新车渗透率_百分比": "nev_share_of_new_sales_pct",
    "新能源汽车保有量_万辆": "nev_fleet_10k",
    "其中纯电动汽车保有量_万辆": "bev_fleet_10k",
    "纯电动占比_百分比": "bev_share_pct",
    "充电设施总量_万个": "chargers_total_10k",
    "公共充电设施_万个": "chargers_public_10k",
    "私人充电设施_万个": "chargers_private_10k",
    "公共占比_百分比": "public_share_pct",
    "车桩比_辆每桩": "vehicles_per_charger",
    "磷酸铁锂装车量_GWh": "lfp_gwh",
    "三元锂电池装车量_GWh": "nmc_gwh",
    "合计装车量_GWh": "total_gwh",
    "磷酸铁锂占比_百分比": "lfp_share_pct",
    "纯电动汽车销量_万辆": "bev_sales_10k",
    "插电式混动汽车销量_万辆": "phev_sales_10k",
    "合计_万辆": "total_10k",
    "插混占比_百分比": "phev_share_pct",
    "新能源汽车出口_万辆": "nev_exports_10k",
    "汽车出口总量_万辆": "total_exports_10k",
    "传统燃料汽车出口_万辆": "ice_exports_10k",
    "新能源出口占比_百分比": "nev_share_of_exports_pct",
    "年度减碳量估算_亿吨": "annual_co2_avoided_100mt",
    "累计减碳量估算_亿吨": "cumulative_co2_avoided_100mt",
}


def load() -> dict[str, pd.DataFrame]:
    frames = {}
    for key, filename in TABLES.items():
        df = pd.read_csv(DATA / filename, encoding="utf-8-sig")
        frames[key] = df.rename(columns=COLUMNS)
    return frames


def millions(value, _pos=None) -> str:
    """Format a 10k-unit value as millions of vehicles."""
    return f"{value / 100:.0f}"


def finish(fig, ax, name: str, source: str) -> None:
    """Apply shared cosmetics, stamp the data note, and save."""
    for spine in ("top", "right"):
        if spine in ax.spines:
            ax.spines[spine].set_visible(False)
    fig.text(0.01, -0.03, source, fontsize=8, color=GREY, ha="left", va="top")
    fig.savefig(CHARTS / name)
    plt.close(fig)


def fig_sales(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df.year, df.nev_sales_10k / 100, color=BLUE, width=0.62, label="NEV sales")
    ax.set_ylabel("NEV sales (million units)")
    ax.set_xlabel("Year")
    ax.set_title("From niche to mainstream: NEV sales and share of new vehicle sales,\n"
                 "China 2015-2025")
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
           "Source: CAAM / MIIT annual statistics, compiled by the author. "
           "Share uses the domestic new-vehicle denominator.")


def fig_charging(fleet: pd.DataFrame, charging: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(charging.year, charging.nev_fleet_10k / 100, color=BLUE, marker="o",
            linewidth=2.2, label="NEV fleet")
    ax.plot(charging.year, charging.chargers_total_10k / 100, color=TEAL, marker="s",
            linewidth=2.2, label="Charging points")
    ax.set_ylabel("Million units")
    ax.set_xlabel("Year")
    ax.set_title("Charging supply has outgrown the fleet:\n"
                 "vehicles per charging point fell from 2.93 to 2.19, 2020-2025")
    twin = ax.twinx()
    twin.bar(charging.year, charging.vehicles_per_charger, color=AMBER, alpha=0.30,
             width=0.55, label="Vehicles per charging point")
    twin.set_ylabel("Vehicles per charging point", color=AMBER)
    twin.set_ylim(0, 4)
    twin.grid(False)
    handles = ax.get_legend_handles_labels()[0] + twin.get_legend_handles_labels()[0]
    labels = ax.get_legend_handles_labels()[1] + twin.get_legend_handles_labels()[1]
    ax.legend(handles, labels, loc="upper left")
    ax.set_xticks(charging.year)
    finish(fig, ax, "02_fleet_vs_charging.png",
           "Source: EVCIPA / MIIT. The 2020-2025 window is used because earlier "
           "public/private charger definitions are not comparable.")


def fig_charger_mix(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.stackplot(df.year, df.chargers_public_10k / 100, df.chargers_private_10k / 100,
                 labels=["Public", "Private"], colors=[BLUE, TEAL], alpha=0.85)
    ax.set_ylabel("Charging points (millions)")
    ax.set_xlabel("Year")
    ax.set_title("Private chargers drove the build-out:\n"
                 "the public share fell from 48% to 23%, 2020-2025")
    twin = ax.twinx()
    twin.plot(df.year, df.public_share_pct, color=CORAL, marker="o", linewidth=2.2,
              label="Public share")
    twin.set_ylabel("Public share (%)", color=CORAL)
    twin.set_ylim(0, 60)
    twin.grid(False)
    handles = ax.get_legend_handles_labels()[0] + twin.get_legend_handles_labels()[0]
    labels = ax.get_legend_handles_labels()[1] + twin.get_legend_handles_labels()[1]
    ax.legend(handles, labels, loc="upper left")
    ax.set_xticks(df.year)
    finish(fig, ax, "03_charger_mix.png", "Source: EVCIPA monthly releases, annual year-end values.")


def fig_battery(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df.year, df.lfp_gwh, color=BLUE, width=0.62, label="LFP")
    ax.bar(df.year, df.nmc_gwh, bottom=df.lfp_gwh, color=AMBER, width=0.62,
           label="NMC / ternary")
    ax.set_ylabel("Battery installed in new vehicles (GWh)")
    ax.set_xlabel("Year")
    ax.set_title("Chemistry reversed: LFP went from 40% to 81% of installed capacity,\n"
                 "China 2018-2025")
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
           "Source: CABIA. LFP + NMC sums to 769.4 GWh in 2025 against an official "
           "total of 769.7 GWh; the 0.3 GWh gap is other chemistries, documented in "
           "docs/DATA_SOURCES.zh-CN.md.")


def fig_powertrain(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df.year, df.bev_sales_10k / 100, color=BLUE, width=0.6, label="Battery electric")
    ax.bar(df.year, df.phev_sales_10k / 100, bottom=df.bev_sales_10k / 100, color=TEAL,
           width=0.6, label="Plug-in hybrid")
    ax.set_ylabel("Sales (million units)")
    ax.set_xlabel("Year")
    ax.set_title("Plug-in hybrids took share back:\n"
                 "PHEV rose from 17% to 36% of NEV sales, 2021-2025")
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
    finish(fig, ax, "05_powertrain_mix.png", "Source: CPCA / CAAM passenger-vehicle statistics.")


def fig_exports(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df.year, df.nev_exports_10k / 100, color=BLUE, width=0.6, label="NEV exports")
    ax.bar(df.year, df.ice_exports_10k / 100, bottom=df.nev_exports_10k / 100, color=GREY,
           width=0.6, label="Conventional-fuel exports")
    ax.set_ylabel("Vehicle exports (million units)")
    ax.set_xlabel("Year")
    ax.set_title("Exports followed the domestic ramp:\n"
                 "NEVs grew from 7% to 37% of China's vehicle exports, 2020-2025")
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
           "Source: CAAM complete-vehicle export basis; excludes knock-down kits.")


def fig_carbon(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df.year, df.annual_co2_avoided_100mt, color=TEAL, width=0.62,
           label="Annual avoided CO2 (scenario)")
    ax.set_ylabel("Avoided CO2 (hundred million tonnes/year)")
    ax.set_xlabel("Year")
    ax.set_title("Scenario estimate, not an official statistic:\n"
                 "cumulative avoided CO2 reaches 0.197 Gt by 2025")
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
           "Author's scenario using a mid-point factor of 1.5 t CO2 per vehicle-year "
           "applied to the year-end fleet. Not a life-cycle assessment and not an "
           "official figure.")


def fig_dashboard(f: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5))
    fig.suptitle("China's NEV transition in four indicators, 2015-2025",
                 fontsize=15, fontweight="bold", color=INK)

    ax = axes[0][0]
    ax.bar(f["sales"].year, f["sales"].nev_sales_10k / 100, color=BLUE, width=0.62)
    ax.set_title("NEV sales (million units)")
    ax.set_xticks(f["sales"].year[::2])

    ax = axes[0][1]
    ax.plot(f["sales"].year, f["sales"].nev_share_of_new_sales_pct, color=CORAL,
            marker="o", linewidth=2.2)
    ax.axhline(50, color=GREY, linestyle=":", linewidth=1.2)
    ax.set_title("Share of new vehicle sales (%)")
    ax.set_xticks(f["sales"].year[::2])

    ax = axes[1][0]
    ax.bar(f["battery"].year, f["battery"].lfp_gwh, color=BLUE, width=0.62, label="LFP")
    ax.bar(f["battery"].year, f["battery"].nmc_gwh, bottom=f["battery"].lfp_gwh,
           color=AMBER, width=0.62, label="NMC")
    ax.set_title("Battery installed by chemistry (GWh)")
    ax.legend(loc="upper left")
    ax.set_xticks(f["battery"].year)

    ax = axes[1][1]
    ax.plot(f["charging"].year, f["charging"].vehicles_per_charger, color=TEAL,
            marker="s", linewidth=2.2)
    ax.set_title("Vehicles per charging point")
    ax.set_ylim(0, 4)
    ax.set_xticks(f["charging"].year)

    for row in axes:
        for ax in row:
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    fig.text(0.01, 0.005, "Sources: CAAM, MIIT, EVCIPA, CABIA, CPCA. Compiled by the author; "
                          "see docs/DATA_SOURCES.zh-CN.md for definitions and caveats.",
             fontsize=8, color=GREY)
    fig.savefig(CHARTS / "08_dashboard.png")
    plt.close(fig)


def main() -> None:
    CHARTS.mkdir(exist_ok=True)
    f = load()
    fig_sales(f["sales"])
    fig_charging(f["fleet"], f["charging"])
    fig_charger_mix(f["charging"])
    fig_battery(f["battery"])
    fig_powertrain(f["powertrain"])
    fig_exports(f["exports"])
    fig_carbon(f["carbon"])
    fig_dashboard(f)
    written = sorted(p.name for p in CHARTS.glob("*.png"))
    print(f"Wrote {len(written)} figures to {CHARTS}:")
    for name in written:
        print(" -", name)


if __name__ == "__main__":
    main()






