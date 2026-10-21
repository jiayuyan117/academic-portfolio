# -*- coding: utf-8 -*-
"""
中国新能源汽车产业发展与绿色低碳转型 —— 数据可视化分析
================================================================
课程：《大数据可视化原理与实践》课程设计
主题：中国新能源汽车产业发展与绿色低碳转型——基于数据可视化的分析


"""

import os
import platform
from pathlib import Path

import numpy as np
import matplotlib
from data_pipeline import (build_tables, NOTE_ZH, CHARGING_BREAK_YEAR, CHARGING_NOTE_ZH,
                           charging_segments, plot_charging_segments)

# 默认使用 Agg 后端：无界面、只把图存成文件，适合命令行 / 双击 bat 运行；
# 若设置了环境变量 NEV_GUI=1（《分步骤运行版.py》会自动设置），
# 则改用系统默认 GUI 后端，运行时可弹窗逐张看图。
if os.environ.get("NEV_GUI") != "1":
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# ------------------------------------------------------------------
# 0. 全局绘图风格（浅色主题，适合打印与插入 Word 报告）
# ------------------------------------------------------------------
# Project root: src/nev_visualization.py -> project root.
# Generated assets stay beside README.md so the portfolio remains self-contained.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHART_DIR = BASE_DIR / "charts"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)

# 中文字体：Windows 用微软雅黑，Mac 用苹方，Linux 用文泉驿
_sys = platform.system()
if _sys == "Windows":
    _fonts = ["Microsoft YaHei", "SimHei", "SimSun"]
elif _sys == "Darwin":
    _fonts = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]
else:
    _fonts = ["WenQuanYi Zen Hei", "Noto Sans CJK SC", "DejaVu Sans"]

plt.rcParams["font.sans-serif"] = _fonts
plt.rcParams["axes.unicode_minus"] = False          # 负号正常显示
plt.rcParams["figure.dpi"] = 110
plt.rcParams["savefig.dpi"] = 300                   # 出图分辨率
plt.rcParams["savefig.bbox"] = "tight"
plt.rcParams["font.size"] = 11
plt.rcParams["axes.edgecolor"] = "#CBD5E1"
plt.rcParams["axes.linewidth"] = 0.9
plt.rcParams["axes.labelcolor"] = "#1F2937"
plt.rcParams["text.color"] = "#1F2937"
plt.rcParams["xtick.color"] = "#475569"
plt.rcParams["ytick.color"] = "#475569"

# 主题色板：绿色低碳 + 科技蓝
C_GREEN = "#16A34A"      # 主色：绿色 / 低碳
C_GREEN_D = "#14532D"    # 深绿
C_GREEN_L = "#86EFAC"    # 浅绿
C_BLUE = "#2563EB"       # 科技蓝
C_BLUE_L = "#93C5FD"     # 浅蓝
C_ORANGE = "#F59E0B"     # 橙（插混 / 三元）
C_RED = "#DC2626"        # 强调红
C_GRAY = "#94A3B8"
BG = "#FFFFFF"
GRID = "#E5E7EB"

FOOTER = NOTE_ZH
BOX = dict(boxstyle="round,pad=0.45", facecolor="#F8FAFC",
           edgecolor="#CBD5E1", linewidth=0.8)


def _style_ax(ax):
    """统一坐标轴风格"""
    ax.set_facecolor(BG)
    ax.grid(axis="y", color=GRID, linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#CBD5E1")
    ax.spines["bottom"].set_color("#CBD5E1")


def _add_footer(fig, text=FOOTER, y=0.005):
    if text != FOOTER:
        text = f"{text}\n{FOOTER}"
    fig.subplots_adjust(bottom=max(fig.subplotpars.bottom, 0.17))
    fig.text(0.5, y, text, ha="center", va="bottom", fontsize=8, color="#64748B")


def _thousands(x, pos=None):
    return f"{x:,.0f}"


def _charging_break(ax):
    ax.axvline(CHARGING_BREAK_YEAR - 0.5, color=C_RED, linestyle="--", linewidth=1.2)
    ax.text(CHARGING_BREAK_YEAR - 0.55, 0.97, "2025 口径断点",
            transform=ax.get_xaxis_transform(), ha="right", va="top", fontsize=8, color=C_RED)


def _seg_label(ax, x, bottom, height, ylim, text, inside_color,
               outside_color, side="right", min_frac=0.13):
    """堆叠柱分段数值标注：段足够高写在段内，否则移到柱体两侧，避免文字溢出柱体"""
    if height / ylim >= min_frac:
        ax.text(x, bottom + height / 2, text, ha="center", va="center",
                fontsize=9, color=inside_color, zorder=6)
    else:
        dx, ha = (0.28, "left") if side == "right" else (-0.28, "right")
        ax.text(x + dx, bottom + height / 2, text, ha=ha, va="center",
                fontsize=9, color=outside_color, zorder=6)


# ==================================================================
# 1. 读取独立输入并验证；外部来源状态见 provenance.json
# ==================================================================

FRAMES, CARBON_FACTOR = build_tables()


def _values(table, field):
    return FRAMES[table][field].to_numpy()


YEARS = _values("sales", "year")
AUTO_SALES = _values("sales", "auto_sales_10k")
NEV_OUTPUT = _values("sales", "nev_output_10k")
NEV_SALES = _values("sales", "nev_sales_10k")
NEV_PENETRATION = _values("sales", "nev_share_of_new_sales_pct")
FLEET_YEARS = _values("fleet", "year")
NEV_STOCK = _values("fleet", "nev_fleet_10k")
BEV_STOCK = _values("fleet", "bev_fleet_10k")
CHG_YEARS = _values("charging", "year")
CHG_TOTAL = _values("charging", "chargers_total_10k")
CHG_PUBLIC = _values("charging", "chargers_public_10k")
CHG_PRIVATE = _values("charging", "chargers_private_10k")
# The pipeline merges fleet and charging by year, with one-to-one validation.
CHG_FLEET = _values("charging", "nev_fleet_10k")
CHG_RATIO = _values("charging", "vehicles_per_charger")
BAT_YEARS = _values("battery", "year")
BAT_LFP = _values("battery", "lfp_gwh")
BAT_NCM = _values("battery", "nmc_gwh")
TECH_YEARS = _values("powertrain", "year")
TECH_BEV = _values("powertrain", "bev_sales_10k")
TECH_PHEV = _values("powertrain", "phev_sales_10k")
EXP_YEARS = _values("exports", "year")
EXP_NEV = _values("exports", "nev_exports_10k")
EXP_AUTO = _values("exports", "total_exports_10k")
CARBON_YEARS = _values("carbon", "year")
CARBON_CUT = _values("carbon", "annual_co2_avoided_100mt")
CARBON_CUM = _values("carbon", "cumulative_co2_avoided_100mt")


# ==================================================================
# 2. 导出 CSV（实验报告附表）
# ==================================================================
def export_csv():
    build_tables(write=True)
    print(f"[OK] 已导出 7 个 CSV 数据文件 -> {DATA_DIR}")


def _two_panel(figsize=(10, 7.4)):
    """上下双面板（上：规模柱状 / 下：比率曲线），避免双轴标注互相压盖"""
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=figsize, sharex=True,
        gridspec_kw={"height_ratios": [2.15, 1.15], "hspace": 0.10})
    _style_ax(ax1)
    _style_ax(ax2)
    ax1.spines["bottom"].set_visible(False)
    return fig, ax1, ax2


# ==================================================================
# 3. 绘图函数
# ==================================================================
def fig1_sales_penetration():
    """图1：新能源汽车销量与新车渗透率"""
    fig, ax1, ax2 = _two_panel(figsize=(10, 7.6))

    bars = ax1.bar(YEARS, NEV_SALES, width=0.6, color=C_GREEN, zorder=3)
    for i, b in enumerate(bars):
        if YEARS[i] >= 2023:
            b.set_color(C_GREEN_D)
    for x, y in zip(YEARS, NEV_SALES):
        ax1.text(x, y + 30, f"{y:,.1f}", ha="center", va="bottom",
                 fontsize=9, color="#334155")
    ax1.set_ylabel("新能源汽车销量（万辆）")
    ax1.set_ylim(0, 1980)
    ax1.yaxis.set_major_formatter(FuncFormatter(_thousands))
    ax1.set_title("新能源汽车销量与占比（2015—2025，全车型含出口）",
                  fontsize=15, fontweight="bold", pad=14)
    crossings = np.flatnonzero(NEV_PENETRATION > 10)
    if len(crossings):
        i = crossings[0]
        ax1.annotate(f"样本内首次销量占比超过 10%：{YEARS[i]} 年\n年度总量不能识别政策或市场驱动效应",
                     xy=(YEARS[i], NEV_SALES[i]), xytext=(2017.5, 1200),
                     fontsize=9, color="#475569",
                     arrowprops=dict(arrowstyle="->", color=C_GRAY, lw=1.1))
    ax1.text(0.018, 0.97,
             f"{YEARS[0]}—{YEARS[-1]} 年样本销量\n期末为期初的 {NEV_SALES[-1] / NEV_SALES[0]:.2f} 倍",
             transform=ax1.transAxes, ha="left", va="top",
             fontsize=9.5, color=C_GREEN_D, bbox=BOX)

    ax2.plot(YEARS, NEV_PENETRATION, color=C_BLUE, marker="o",
             markersize=6, linewidth=2.4, zorder=4)
    ax2.fill_between(YEARS, NEV_PENETRATION, color=C_BLUE, alpha=0.10)
    for x, y in zip(YEARS, NEV_PENETRATION):
        ax2.text(x, y + 2.2, f"{y:.2f}%", ha="center", fontsize=9, color=C_BLUE)
    ax2.set_ylabel("样本销量占比（%）", color=C_BLUE)
    ax2.set_ylim(0, 58)
    ax2.set_xticks(YEARS)
    ax2.set_xlabel("年份")
    ax2.axhline(50, color=C_RED, linewidth=1.0, linestyle="--", alpha=0.75)
    ax2.text(2015.05, 51.4, "50% 参考线（本项目仅有年度输入）",
             fontsize=9, color=C_RED, va="bottom")

    _add_footer(fig, "2025 分母为全车型销量（含出口）；公布占比 47.9%，图中由舍入销量重算；商务部转载工信部/中汽协，2026-01-15", y=0.02)
    fig.subplots_adjust(bottom=0.12)
    fig.savefig(CHART_DIR / "01_新能源汽车销量与渗透率.png")
    plt.close(fig)


def fig2_stock_vs_charging():
    """图2：保有量与充电设施；2025 年 NEA 口径断点。"""
    fig, ax = plt.subplots(figsize=(10, 6))
    _style_ax(ax)

    ax.plot(FLEET_YEARS, NEV_STOCK, color=C_GREEN, marker="o", markersize=6,
            linewidth=2.6, label="新能源汽车保有量（万辆）", zorder=4)
    ax.fill_between(FLEET_YEARS, NEV_STOCK, color=C_GREEN, alpha=0.12, zorder=2)
    for x, y in zip(FLEET_YEARS, NEV_STOCK):
        ax.text(x, y + 110, f"{y:,.0f}", ha="center", fontsize=9, color=C_GREEN_D)
    ax.set_ylabel("新能源汽车保有量（万辆）", color=C_GREEN_D)
    ax.set_ylim(0, 5100)
    ax.set_xlim(2014.5, 2026.1)
    ax.yaxis.set_major_formatter(FuncFormatter(_thousands))
    ax.set_xticks(YEARS)
    ax.set_xlabel("年份")

    ax2 = ax.twinx()
    plot_charging_segments(ax2, FRAMES["charging"], "chargers_total_10k",
                           color=C_BLUE, marker="s", markersize=6,
                           linewidth=2.4, label="充电数量（2025 改计枪口）", zorder=5)
    _charging_break(ax2)
    for x, y in zip(CHG_YEARS[:-1], CHG_TOTAL[:-1]):
        ax2.text(x, y - 135, f"{y:,.1f}", ha="center", fontsize=9, color=C_BLUE)
    ax2.text(2025.16, CHG_TOTAL[-1], f"{CHG_TOTAL[-1]:,.1f}", ha="left",
             va="center", fontsize=9, color=C_BLUE)
    ax2.set_ylabel("充电基础设施保有量（万个）", color=C_BLUE)
    ax2.set_ylim(0, 2450)
    ax2.spines["top"].set_visible(False)

    ax.text(2016.4, 3450,
            f"2025 年 NEA 新口径截面\n车/枪口比 {CHG_RATIO[-1]:.2f} : 1\n"
            "与此前 EVCIPA 不作连续增长比较",
            fontsize=9.5, color="#475569", ha="left", va="top", bbox=BOX)

    ax.set_title("保有量与充电数量（2025 年 NEA 统计口径断点）",
                 fontsize=15, fontweight="bold", pad=14)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=10)
    _add_footer(fig, CHARGING_NOTE_ZH + "\nNEA 2025-07-31 口径说明、2026-01-21 年末发布；数量不反映功率、可达性或利用率")
    fig.savefig(CHART_DIR / "02_保有量与充电设施协同增长.png")
    plt.close(fig)


def fig3_charging_structure():
    """图3：充电设施结构（公共 vs 私人）"""
    fig, ax1, ax2 = _two_panel(figsize=(10, 7.4))

    w = 0.55
    for i, segment in enumerate(charging_segments(FRAMES["charging"])):
        ax1.bar(segment.year, segment.chargers_private_10k, width=w, color=C_GREEN_L,
                label="私人" if i == 0 else "2025 NEA 新口径（斜线）",
                hatch="//" if i else None, zorder=3)
        ax1.bar(segment.year, segment.chargers_public_10k, width=w,
                bottom=segment.chargers_private_10k, color=C_BLUE,
                label="公共" if i == 0 else "_nolegend_", hatch="//" if i else None, zorder=3)
    _charging_break(ax1)
    for x, p, q in zip(CHG_YEARS, CHG_PRIVATE, CHG_PUBLIC):
        _seg_label(ax1, x, 0, p, 2450, f"{p:,.1f}", "#14532D", "#166534", side="left", min_frac=0.058)
        _seg_label(ax1, x, p, q, 2450, f"{q:,.1f}", "#FFFFFF", "#1D4ED8", side="right", min_frac=0.058)
    for x, t in zip(CHG_YEARS, CHG_TOTAL):
        ax1.text(x, t + 45, f"合计 {t:,.1f}", ha="center", fontsize=9,
                 color="#334155", fontweight="bold")
    ax1.set_ylabel("充电基础设施（万个）")
    ax1.set_ylim(0, 2450)
    ax1.set_xlim(2019.0, 2025.95)
    ax1.yaxis.set_major_formatter(FuncFormatter(_thousands))
    ax1.set_title("充电数量结构：EVCIPA 历史序列与 2025 NEA 新口径",
                  fontsize=15, fontweight="bold", pad=14)
    ax1.legend(frameon=False, fontsize=10, loc="upper left")

    share = CHG_PUBLIC / CHG_TOTAL * 100
    plot_charging_segments(ax2, FRAMES["charging"], "public_share_pct",
                           color=C_ORANGE, marker="D", markersize=6, linewidth=2.2)
    _charging_break(ax2)
    for x, y in zip(CHG_YEARS, share):
        ax2.text(x, y + 1.8, f"{y:.1f}%", ha="center", fontsize=9, color=C_ORANGE)
    ax2.set_ylabel("公共设施占比（%）", color=C_ORANGE)
    ax2.set_ylim(0, 60)
    ax2.set_xticks(CHG_YEARS)
    ax2.set_xlabel("年份")
    ax2.annotate(f"2025 新口径公共占比 {share[-1]:.2f}%\n跨口径差额不能解释为实际新增量",
                 xy=(CHG_YEARS[-1], share[-1]), xytext=(2020.1, 8),
                 fontsize=9.5, color="#475569",
                 arrowprops=dict(arrowstyle="->", color=C_GRAY, lw=1.1))

    _add_footer(fig, CHARGING_NOTE_ZH + "\n私人数量按总量减公共量计算，与 NEA 公布的 2025 私人数量一致", y=0.005)
    fig.subplots_adjust(bottom=0.12)
    fig.savefig(CHART_DIR / "03_充电设施结构演变.png")
    plt.close(fig)


def fig4_battery():
    """图4：动力电池装车量结构"""
    fig, ax1, ax2 = _two_panel(figsize=(10, 7.4))

    tot = BAT_LFP + BAT_NCM
    bars = ax1.bar(BAT_YEARS, tot, width=0.5, color=C_GREEN, zorder=3,
                   label="磷酸铁锂 + 三元锂小计（GWh）")
    for i, b in enumerate(bars):
        if BAT_YEARS[i] >= 2023:
            b.set_color(C_GREEN_D)
    for x, t in zip(BAT_YEARS, tot):
        ax1.text(x, t + 16, f"{t:,.1f}", ha="center", fontsize=9,
                 color="#334155", fontweight="bold")
    ax1.set_ylabel("动力电池装车量（GWh）")
    ax1.set_ylim(0, 900)
    ax1.set_xlim(2017.6, 2025.4)
    ax1.set_title("两类动力电池装车结构（2018—2025，部分历史值待核实）",
                  fontsize=15, fontweight="bold", pad=14)
    ax1.legend(frameon=False, fontsize=10, loc="upper left")

    share_lfp = BAT_LFP / tot * 100
    share_ncm = 100 - share_lfp
    ax2.fill_between(BAT_YEARS, 0, share_lfp, color=C_GREEN, alpha=0.85, lw=0)
    ax2.fill_between(BAT_YEARS, share_lfp, 100, color=C_ORANGE, alpha=0.85, lw=0)
    ax2.plot(BAT_YEARS, share_lfp, color="#FFFFFF", linewidth=1.6)
    ax2.axhline(50, color=C_RED, linewidth=1.0, linestyle="--", alpha=0.8)
    ax2.text(2022.55, 52.5, "50% 结构分界线", fontsize=8.5, color=C_RED)
    ax2.text(2018.0, 20, "磷酸铁锂\n占比", fontsize=9, color="#FFFFFF",
             ha="left", va="center", fontweight="bold")
    ax2.text(BAT_YEARS[-1], 91, f"三元锂 {share_ncm[-1]:.1f}%", fontsize=9, color="#7C2D12",
             ha="right", va="center")
    ax2.text(BAT_YEARS[-1], 40.7, f"磷酸铁锂 {share_lfp[-1]:.1f}%", fontsize=9, color="#FFFFFF",
             ha="right", va="center", fontweight="bold")
    ax2.set_ylabel("两类小计内占比（%）")
    ax2.set_ylim(0, 100)
    ax2.set_xticks(BAT_YEARS)
    ax2.set_xlabel("年份")
    crossings = np.flatnonzero(BAT_LFP > BAT_NCM)
    if len(crossings):
        i = crossings[0]
        ax2.annotate(f"样本内首次磷酸铁锂高于三元锂：{BAT_YEARS[i]} 年",
                     xy=(BAT_YEARS[i], share_lfp[i]), xytext=(2021.15, 12),
                     fontsize=9.5, color="#475569",
                     arrowprops=dict(arrowstyle="->", color="#FFFFFF", lw=1.3))

    _add_footer(fig, f"{BAT_YEARS[-1]} 年两类小计 {tot[-1]:.1f} GWh；占比分母不包含未列出的化学体系", y=0.02)
    fig.subplots_adjust(bottom=0.12)
    fig.savefig(CHART_DIR / "04_动力电池装车量结构.png")
    plt.close(fig)


def fig5_tech_route():
    """图5：全车型 BEV/PHEV 小计，不含燃料电池汽车。"""
    fig, ax1, ax2 = _two_panel(figsize=(10, 7.4))

    w = 0.5
    ax1.bar(TECH_YEARS, TECH_BEV, width=w, color=C_GREEN_D,
            label="纯电动汽车（万辆）", zorder=3)
    ax1.bar(TECH_YEARS, TECH_PHEV, width=w, bottom=TECH_BEV, color=C_ORANGE,
            label="插电式混动（万辆）", zorder=3)
    for x, b, p in zip(TECH_YEARS, TECH_BEV, TECH_PHEV):
        _seg_label(ax1, x, 0, b, 1950, f"{b:,.1f}", "#FFFFFF", "#166534", side="left", min_frac=0.058)
        _seg_label(ax1, x, b, p, 1950, f"{p:,.1f}", "#FFFFFF", "#B45309", side="right", min_frac=0.058)
        ax1.text(x, b + p + 30, f"合计 {b + p:,.1f}", ha="center", fontsize=9,
                 color="#334155", fontweight="bold")
    ax1.set_ylabel("样本两类汽车销量（万辆）")
    ax1.set_ylim(0, 1950)
    ax1.set_xlim(2020.0, 2025.95)
    ax1.yaxis.set_major_formatter(FuncFormatter(_thousands))
    ax1.set_title("全车型纯电与插混销量结构（2021—2025，非仅乘用车）",
                  fontsize=15, fontweight="bold", pad=14)
    ax1.legend(frameon=False, fontsize=10, loc="upper left")

    phev_share = TECH_PHEV / (TECH_BEV + TECH_PHEV) * 100
    ax2.plot(TECH_YEARS, phev_share, color=C_BLUE, marker="s", markersize=6,
             linewidth=2.2)
    for x, y in zip(TECH_YEARS, phev_share):
        ax2.text(x, y + 2.0, f"{y:.1f}%", ha="center", fontsize=9, color=C_BLUE)
    ax2.set_ylabel("插电式混动占比（%）", color=C_BLUE)
    ax2.set_ylim(0, 50)
    ax2.set_xticks(TECH_YEARS)
    ax2.set_xlabel("年份")
    ax2.annotate(f"两类小计内插混占比：{phev_share[0]:.1f}% → {phev_share[-1]:.1f}%\n"
                 f"末年较上年变动 {phev_share[-1]-phev_share[-2]:+.2f} 个百分点",
                 xy=(TECH_YEARS[-1], phev_share[-1]), xytext=(2021.05, 8),
                 fontsize=9.5, color="#475569",
                 arrowprops=dict(arrowstyle="->", color=C_GRAY, lw=1.1))

    _add_footer(fig, "全车型 BEV + PHEV 小计（不含燃料电池）；2021 工信部发布会，2022-01-12；2025 经济观察报，2026-01-15", y=0.02)
    fig.subplots_adjust(bottom=0.12)
    fig.savefig(CHART_DIR / "05_技术路线结构.png")
    plt.close(fig)


def fig6_export():
    """图6：新能源汽车出口规模与占比"""
    fig, ax, ax2 = _two_panel(figsize=(10, 7.6))

    x = np.arange(len(EXP_YEARS))
    ax.bar(x, EXP_NEV, width=0.5, color=C_BLUE,
           label="新能源汽车出口（万辆）", zorder=3)
    ax.bar(x, EXP_AUTO - EXP_NEV, width=0.5, bottom=EXP_NEV,
           color="#E2E8F0", label="其余汽车出口（差额，万辆）", zorder=3)
    for xi, n, t in zip(x, EXP_NEV, EXP_AUTO):
        _seg_label(ax, xi, 0, n, 900, f"{'约 ' if EXP_YEARS[xi] == 2020 else ''}{n:,.1f}", "#FFFFFF", C_BLUE,
                   side="left", min_frac=0.058)
        ax.text(xi, n + (t - n) / 2, f"{t - n:,.1f}", ha="center", va="center",
                fontsize=9, color="#475569")
        ax.text(xi, t + 22, f"{t:,.1f}", ha="center", fontsize=9,
                color="#334155", fontweight="bold")

    ax.set_ylabel("汽车出口量（万辆）")
    ax.set_ylim(0, 900)
    ax.yaxis.set_major_formatter(FuncFormatter(_thousands))
    ax.set_xticks(x)
    ax.set_xticklabels(EXP_YEARS)
    ax.set_xlim(-0.75, 5.75)

    share = EXP_NEV / EXP_AUTO * 100
    ax2.plot(x, share, color=C_RED, marker="o", markersize=6.5,
             linewidth=2.4, label="新能源占出口比重（%）")
    for xi, y in zip(x, share):
        ax2.text(xi, y + 2.4, f"{'约 ' if EXP_YEARS[xi] == 2020 else ''}{y:.1f}%",
                 ha="center", fontsize=9.5, color=C_RED)
    ax2.set_ylabel("新能源汽车出口占比（%）", color=C_RED)
    ax2.set_ylim(0, 55)
    ax2.set_xlabel("年份")
    ax2.spines["top"].set_visible(False)

    ax.text(4.35, 878,
            f"{EXP_YEARS[-1]} 年样本新能源出口 {EXP_NEV[-1]:.1f} 万辆\n"
            f"同比 {(EXP_NEV[-1]/EXP_NEV[-2]-1)*100:.1f}%，占样本出口 {share[-1]:.1f}%",
            fontsize=9.5, color=C_RED, ha="center", va="top", bbox=BOX)

    ax.set_title("汽车出口结构与新能源占比（2020—2025，2020 为约数）",
                 fontsize=15, fontweight="bold", pad=14)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=10)
    _add_footer(fig, "2025 中汽协数据经工信部/商务部转载，2026-01-15；2020 新能源出口仅获约 7 万辆支持，计算占比亦为约数", y=0.02)
    fig.subplots_adjust(bottom=0.12)
    fig.savefig(CHART_DIR / "06_新能源汽车出口.png")
    plt.close(fig)


def fig7_carbon():
    """图7：新能源汽车年度减碳量情景估算"""
    fig, ax1, ax2 = _two_panel(figsize=(10, 7.4))

    bars = ax1.bar(CARBON_YEARS, CARBON_CUT, width=0.6, color=C_GREEN, zorder=3)
    for i, b in enumerate(bars):
        if CARBON_YEARS[i] >= 2023:
            b.set_color(C_GREEN_D)
    for x, y in zip(CARBON_YEARS, CARBON_CUT):
        ax1.text(x, y + 0.013, f"{y:.2f}", ha="center", va="bottom",
                 fontsize=9, color="#334155")
    ax1.set_ylabel("年度减碳量（亿吨 CO2）")
    ax1.set_ylim(0, 0.88)
    ax1.set_title("年度与累计减碳情景（2015—2025，作者自定假设）",
                  fontsize=15, fontweight="bold", pad=14)
    ax1.text(0.015, 0.97,
             f"作者演示假设：{CARBON_FACTOR:g} t CO2 /（辆·年）\n"
             "参数类别：assumption（非统计观测）\n年末保有量替代全年车年暴露量\n"
             "未计电网、行驶里程与制造排放\n不是实测减排或生命周期评估",
             transform=ax1.transAxes, ha="left", va="top", fontsize=9,
             color="#475569", bbox=BOX)

    ax2.plot(CARBON_YEARS, CARBON_CUM, color=C_ORANGE, marker="D", markersize=5.5,
             linewidth=2.2)
    ax2.fill_between(CARBON_YEARS, CARBON_CUM, color=C_ORANGE, alpha=0.12)
    for x, y in zip(CARBON_YEARS, CARBON_CUM):
        if x in (2015, 2018, 2021, 2023, 2025):
            ax2.text(x, y + 0.14, f"{y:.2f}", ha="center", fontsize=9, color=C_ORANGE)
    ax2.set_ylabel("累计减碳量（亿吨 CO2）", color=C_ORANGE)
    ax2.set_ylim(0, 2.45)
    ax2.set_xticks(YEARS)
    ax2.set_xlabel("年份")

    _add_footer(fig, "累计值为年度情景值之和；不得与其他地区、年度或生命周期口径的减排量直接比较", y=0.02)
    fig.subplots_adjust(bottom=0.12)
    fig.savefig(CHART_DIR / "07_减碳量情景估算.png")
    plt.close(fig)


def fig8_dashboard():
    """图8：综合看板（2×2）"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10.5))
    fig.suptitle("新能源汽车产业看板（部分数值已核实，2025 充电口径断点）",
                 fontsize=18, fontweight="bold", y=0.985, color="#0F172A")

    # (a) 销量 + 渗透率
    ax = axes[0, 0]
    _style_ax(ax)
    ax.bar(YEARS, NEV_SALES, width=0.6, color=C_GREEN, zorder=3)
    ax.set_title("(a) 全车型新能源汽车销量与占比（含出口）", fontsize=12, fontweight="bold")
    ax.set_ylabel("销量（万辆）")
    ax.set_xticks(YEARS[::2])
    axb = ax.twinx()
    axb.plot(YEARS, NEV_PENETRATION, color=C_BLUE, marker="o", lw=2, markersize=4)
    axb.set_ylabel("样本销量占比（%）", color=C_BLUE)
    axb.set_ylim(0, 62)
    axb.spines["top"].set_visible(False)

    # (b) 保有量 + 充电设施
    ax = axes[0, 1]
    _style_ax(ax)
    ax.plot(FLEET_YEARS, NEV_STOCK, color=C_GREEN_D, marker="o", lw=2.2, markersize=4,
            label="新能源汽车保有量")
    ax.fill_between(FLEET_YEARS, NEV_STOCK, color=C_GREEN, alpha=0.12)
    ax.set_title("(b) 保有量与充电数量（2025 口径断点）", fontsize=12, fontweight="bold")
    ax.set_ylabel("保有量（万辆）")
    ax.set_xticks(YEARS[::2])
    ax.set_ylim(0, 5100)
    axb = ax.twinx()
    plot_charging_segments(axb, FRAMES["charging"], "chargers_total_10k",
                           color=C_BLUE, marker="s", lw=2.2, markersize=4, label="充电数量（万个）")
    _charging_break(axb)
    axb.set_ylabel("充电设施（万个）", color=C_BLUE)
    axb.spines["top"].set_visible(False)

    # (c) 电池结构
    ax = axes[1, 0]
    _style_ax(ax)
    ax.bar(BAT_YEARS, BAT_LFP, width=0.55, color=C_GREEN, label="磷酸铁锂", zorder=3)
    ax.bar(BAT_YEARS, BAT_NCM, width=0.55, bottom=BAT_LFP, color=C_ORANGE,
           label="三元锂", zorder=3)
    ax.set_title("(c) 两类动力电池装车量（GWh）", fontsize=12, fontweight="bold")
    ax.set_ylabel("装车量（GWh）")
    ax.set_xticks(BAT_YEARS[::2])
    ax.legend(frameon=False, fontsize=9, loc="upper left")

    # (d) 出口
    ax = axes[1, 1]
    _style_ax(ax)
    ax.bar(EXP_YEARS, EXP_NEV, width=0.5, color=C_BLUE, label="新能源汽车出口", zorder=3)
    ax.bar(EXP_YEARS, EXP_AUTO - EXP_NEV, width=0.5, bottom=EXP_NEV,
           color="#E2E8F0", label="其余汽车出口（差额）", zorder=3)
    ax.set_title("(d) 汽车出口结构（万辆，2020 NEV 为约数）", fontsize=12, fontweight="bold")
    ax.set_ylabel("出口量（万辆）")
    ax.set_xticks(EXP_YEARS)
    ax.legend(frameon=False, fontsize=9, loc="upper left")

    _add_footer(fig, CHARGING_NOTE_ZH, y=0.008)
    fig.tight_layout(rect=[0, 0.045, 1, 0.965])
    fig.savefig(CHART_DIR / "08_综合看板.png")
    plt.close(fig)


# ==================================================================
# 4. 主流程
# ==================================================================
def main():
    print("=" * 66)
    print("  中国新能源汽车产业发展与绿色低碳转型 · 数据可视化")
    print("=" * 66)

    export_csv()

    print("[..] 正在生成图表 …")
    fig1_sales_penetration()
    fig2_stock_vs_charging()
    fig3_charging_structure()
    fig4_battery()
    fig5_tech_route()
    fig6_export()
    fig7_carbon()
    fig8_dashboard()
    print(f"[OK] 已生成 8 张图表 -> {CHART_DIR}")

    print("\n---- 计算摘要（部分数值已按来源审计核对） ----")
    print(NOTE_ZH)
    print(f"1) 新能源汽车销量：{NEV_SALES[0]:.1f} 万辆（{YEARS[0]}）→ "
          f"{NEV_SALES[-1]:,.1f} 万辆（{YEARS[-1]}），期末为期初 {NEV_SALES[-1] / NEV_SALES[0]:.2f} 倍")
    print(f"2) 样本年度销量占比：{NEV_PENETRATION[0]:.2f}% → {NEV_PENETRATION[-1]:.2f}%；"
          "分母为全车型销量（含出口）；2025 公布值 47.9%，计算值单列")
    print(f"3) 保有量：{NEV_STOCK[0]:.1f} 万辆 → {NEV_STOCK[-1]:,.0f} 万辆，"
          f"纯电动占比 {BEV_STOCK[-1] / NEV_STOCK[-1] * 100:.1f}%")
    print(f"4) 2025 NEA 新口径：{CHG_TOTAL[-1]:,.1f} 万枪口，车/枪口比 {CHG_RATIO[-1]:.2f}:1；"
          "跨口径不解释为连续增长或实际新增量")
    print(f"5) 两类电池装车量小计：{BAT_LFP[-1] + BAT_NCM[-1]:,.1f} GWh（{BAT_YEARS[-1]}），"
          f"小计内磷酸铁锂占比 {BAT_LFP[-1] / (BAT_LFP[-1] + BAT_NCM[-1]) * 100:.1f}%")
    print(f"6) 技术路线：{TECH_YEARS[-1]} 年纯电 {TECH_BEV[-1]:,.1f} 万辆、插混 {TECH_PHEV[-1]:,.1f} 万辆，"
          f"插混占比 {TECH_PHEV[-1] / (TECH_BEV[-1] + TECH_PHEV[-1]) * 100:.1f}%")
    print(f"7) 出口：约 {EXP_NEV[0]:.1f} 万辆（{EXP_YEARS[0]}）→ {EXP_NEV[-1]:,.1f} 万辆（{EXP_YEARS[-1]}），"
          f"占汽车出口 {EXP_NEV[-1] / EXP_AUTO[-1] * 100:.1f}%")
    print(f"8) 累计减碳情景：{CARBON_CUM[-1]:.6f} 亿吨 CO2；"
          f"作者假设系数 {CARBON_FACTOR:g} 吨/辆年，独立 assumption 分类，非实测减排")
    print("\n全部完成")


if __name__ == "__main__":
    main()
