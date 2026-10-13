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
import pandas as pd
import matplotlib

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
# Project root: code/nev_visualization.py -> project root.
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

FOOTER = "数据来源：中国汽车工业协会（CAAM）、公安部、中国充电联盟（EVCIPA）、中国汽车动力电池产业创新联盟、海关总署等官方统计"
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
    fig.text(0.5, y, text, ha="center", va="bottom", fontsize=8, color="#94A3B8")


def _thousands(x, pos=None):
    return f"{x:,.0f}"


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
# 1. 数据区（★全部为可溯源的官方真实数据★）
# ==================================================================

# ---- 数据 1：汽车与新能源汽车产销量、新车渗透率 --------------------
# 来源：中国汽车工业协会（CAAM）历年统计；渗透率为新能源汽车新车销量
#       占汽车新车总销量的比重（国内口径），2025 年为 47.9%
YEARS = np.array([2015, 2016, 2017, 2018, 2019, 2020,
                  2021, 2022, 2023, 2024, 2025])
AUTO_SALES = np.array([2459.8, 2802.8, 2887.9, 2808.1, 2576.9, 2531.1,
                       2627.5, 2686.4, 3009.4, 3143.6, 3440.0])   # 汽车总销量（万辆）
NEV_OUTPUT = np.array([34.0, 51.7, 79.4, 127.0, 124.2, 136.6,
                       354.5, 705.8, 958.7, 1288.8, 1662.6])       # 新能源汽车产量（万辆）
NEV_SALES = np.array([33.1, 50.7, 77.7, 125.6, 120.6, 136.7,
                      352.1, 688.7, 949.5, 1286.6, 1649.0])       # 新能源汽车销量（万辆）
NEV_PENETRATION = np.array([1.3, 1.8, 2.7, 4.5, 4.7, 5.4,
                            13.4, 25.6, 31.6, 40.9, 47.9])         # 新车渗透率（%）

# ---- 数据 2：新能源汽车保有量 -------------------------------------
# 来源：公安部交通管理局历年“全国机动车保有量”统计
NEV_STOCK = np.array([58.3, 109.0, 153.0, 261.0, 381.0, 492.0,
                      784.0, 1310.0, 2041.0, 3140.0, 4397.0])     # 新能源汽车保有量（万辆）
BEV_STOCK = np.array([33.2, 74.1, 125.0, 211.0, 310.0, 400.0,
                      640.0, 1045.0, 1552.0, 2209.0, 3022.0])     # 其中纯电动汽车（万辆）

# ---- 数据 3：充电基础设施 ----------------------------------------
# 来源：中国充电联盟（EVCIPA）/ 国家能源局《全国电动汽车充换电基础设施运行情况》
CHG_YEARS = np.array([2020, 2021, 2022, 2023, 2024, 2025])
CHG_TOTAL = np.array([168.1, 261.7, 521.0, 859.6, 1281.8, 2009.2])   # 充电设施总量（万个）
CHG_PUBLIC = np.array([80.7, 114.7, 179.7, 272.6, 357.9, 471.7])     # 公共充电设施（万个）
CHG_PRIVATE = CHG_TOTAL - CHG_PUBLIC                                  # 私人充电设施（万个）

# ---- 数据 4：动力电池装车量 ---------------------------------------
# 来源：中国汽车动力电池产业创新联盟历年“动力电池装车量”统计
BAT_YEARS = np.array([2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025])
BAT_LFP = np.array([22.2, 20.2, 24.4, 79.8, 183.8, 261.0, 409.0, 625.3])  # 磷酸铁锂（GWh）
BAT_NCM = np.array([33.1, 40.5, 38.9, 74.3, 110.4, 126.2, 139.0, 144.1])  # 三元锂（GWh）

# ---- 数据 5：新能源乘用车技术路线结构 -----------------------------
# 来源：中国汽车工业协会（CAAM）分动力类型产销统计
TECH_YEARS = np.array([2021, 2022, 2023, 2024, 2025])
TECH_BEV = np.array([291.6, 536.5, 668.5, 771.9, 1062.2])   # 纯电动（万辆）
TECH_PHEV = np.array([60.6, 151.8, 280.4, 514.1, 586.1])    # 插电式混动（含增程，万辆）

# ---- 数据 6：新能源汽车出口 ---------------------------------------
# 来源：中国汽车工业协会（CAAM）/ 海关总署
EXP_YEARS = np.array([2020, 2021, 2022, 2023, 2024, 2025])
EXP_NEV = np.array([7.0, 31.0, 67.9, 120.3, 128.4, 261.5])      # 新能源汽车出口（万辆）
EXP_AUTO = np.array([99.5, 201.5, 311.1, 491.0, 585.9, 709.8])  # 汽车出口总量（万辆）

# ---- 数据 7：绿色低碳成效（情景估算） -----------------------------
# 保有量口径同数据 2（公安部）；单车年均减碳 1.5 吨 CO2/年 取 ICCT
# 《Life-cycle GHG emissions of passenger cars》(2025 更新版) 所给区间
# （1.0~2.0 吨/年）的中值。该指标为“情景估算”，用于说明趋势。
CARBON_FACTOR = 1.5  # 吨 CO2 /（辆·年）
CARBON_CUT = NEV_STOCK * CARBON_FACTOR / 10000.0   # 年度减碳量（亿吨 CO2）
CARBON_CUM = np.cumsum(CARBON_CUT)                 # 累计减碳量（亿吨 CO2）


# ==================================================================
# 2. 导出 CSV（实验报告附表）
# ==================================================================
def export_csv():
    pd.DataFrame({
        "年份": YEARS,
        "汽车总销量_万辆": AUTO_SALES,
        "新能源汽车产量_万辆": NEV_OUTPUT,
        "新能源汽车销量_万辆": NEV_SALES,
        "新能源汽车新车渗透率_百分比": NEV_PENETRATION,
    }).to_csv(DATA_DIR / "01_汽车与新能源汽车产销_2015-2025.csv",
              index=False, encoding="utf-8-sig")

    pd.DataFrame({
        "年份": YEARS,
        "新能源汽车保有量_万辆": NEV_STOCK,
        "其中纯电动汽车保有量_万辆": BEV_STOCK,
        "纯电动占比_百分比": np.round(BEV_STOCK / NEV_STOCK * 100, 2),
    }).to_csv(DATA_DIR / "02_新能源汽车保有量_2015-2025.csv",
              index=False, encoding="utf-8-sig")

    pd.DataFrame({
        "年份": CHG_YEARS,
        "充电设施总量_万个": CHG_TOTAL,
        "公共充电设施_万个": CHG_PUBLIC,
        "私人充电设施_万个": CHG_PRIVATE,
        "公共占比_百分比": np.round(CHG_PUBLIC / CHG_TOTAL * 100, 2),
        "新能源汽车保有量_万辆": NEV_STOCK[-6:],
        "车桩比_辆每桩": np.round(NEV_STOCK[-6:] / CHG_TOTAL, 2),
    }).to_csv(DATA_DIR / "03_充电基础设施_2020-2025.csv",
              index=False, encoding="utf-8-sig")

    pd.DataFrame({
        "年份": BAT_YEARS,
        "磷酸铁锂装车量_GWh": BAT_LFP,
        "三元锂电池装车量_GWh": BAT_NCM,
        "合计装车量_GWh": BAT_LFP + BAT_NCM,
        "磷酸铁锂占比_百分比": np.round(BAT_LFP / (BAT_LFP + BAT_NCM) * 100, 2),
    }).to_csv(DATA_DIR / "04_动力电池装车量_2018-2025.csv",
              index=False, encoding="utf-8-sig")

    pd.DataFrame({
        "年份": TECH_YEARS,
        "纯电动汽车销量_万辆": TECH_BEV,
        "插电式混动汽车销量_万辆": TECH_PHEV,
        "合计_万辆": TECH_BEV + TECH_PHEV,
        "纯电动占比_百分比": np.round(TECH_BEV / (TECH_BEV + TECH_PHEV) * 100, 2),
        "插混占比_百分比": np.round(TECH_PHEV / (TECH_BEV + TECH_PHEV) * 100, 2),
    }).to_csv(DATA_DIR / "05_新能源乘用车技术路线_2021-2025.csv",
              index=False, encoding="utf-8-sig")

    pd.DataFrame({
        "年份": EXP_YEARS,
        "新能源汽车出口_万辆": EXP_NEV,
        "汽车出口总量_万辆": EXP_AUTO,
        "传统燃料汽车出口_万辆": EXP_AUTO - EXP_NEV,
        "新能源出口占比_百分比": np.round(EXP_NEV / EXP_AUTO * 100, 2),
    }).to_csv(DATA_DIR / "06_新能源汽车出口_2020-2025.csv",
              index=False, encoding="utf-8-sig")

    pd.DataFrame({
        "年份": YEARS,
        "新能源汽车保有量_万辆": NEV_STOCK,
        "年度减碳量估算_亿吨": np.round(CARBON_CUT, 3),
        "累计减碳量估算_亿吨": np.round(CARBON_CUM, 3),
    }).to_csv(DATA_DIR / "07_绿色低碳成效情景估算_2015-2025.csv",
              index=False, encoding="utf-8-sig")

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
    ax1.set_title("中国新能源汽车销量与新车渗透率（2015—2025）",
                  fontsize=15, fontweight="bold", pad=14)
    ax1.annotate("2021 年渗透率突破 10%，\n产业由政策驱动转向市场驱动",
                 xy=(2021, 352.1), xytext=(2021.4, 1430),
                 fontsize=9.5, color="#475569",
                 arrowprops=dict(arrowstyle="->", color=C_GRAY, lw=1.1))
    ax1.text(0.018, 0.97,
             "2015—2025 年新能源汽车销量增长约 50 倍\n连续 11 年位居全球第一",
             transform=ax1.transAxes, ha="left", va="top",
             fontsize=9.5, color=C_GREEN_D, bbox=BOX)

    ax2.plot(YEARS, NEV_PENETRATION, color=C_BLUE, marker="o",
             markersize=6, linewidth=2.4, zorder=4)
    ax2.fill_between(YEARS, NEV_PENETRATION, color=C_BLUE, alpha=0.10)
    for x, y in zip(YEARS, NEV_PENETRATION):
        ax2.text(x, y + 2.2, f"{y}%", ha="center", fontsize=9, color=C_BLUE)
    ax2.set_ylabel("新车渗透率（%）", color=C_BLUE)
    ax2.set_ylim(0, 58)
    ax2.set_xticks(YEARS)
    ax2.set_xlabel("年份")
    ax2.axhline(50, color=C_RED, linewidth=1.0, linestyle="--", alpha=0.75)
    ax2.text(2015.05, 51.4, "50% 分界线（2025 年 12 月单月渗透率已达 52.3%）",
             fontsize=9, color=C_RED, va="bottom")

    _add_footer(fig, "数据来源：中国汽车工业协会（CAAM）；渗透率 = 新能源汽车新车销量 / 汽车新车总销量", y=0.02)
    fig.subplots_adjust(bottom=0.12)
    fig.savefig(CHART_DIR / "01_新能源汽车销量与渗透率.png")
    plt.close(fig)


def fig2_stock_vs_charging():
    """图2：保有量与充电设施协同增长"""
    fig, ax = plt.subplots(figsize=(10, 6))
    _style_ax(ax)

    ax.plot(YEARS, NEV_STOCK, color=C_GREEN, marker="o", markersize=6,
            linewidth=2.6, label="新能源汽车保有量（万辆）", zorder=4)
    ax.fill_between(YEARS, NEV_STOCK, color=C_GREEN, alpha=0.12, zorder=2)
    for x, y in zip(YEARS, NEV_STOCK):
        ax.text(x, y + 110, f"{y:,.0f}", ha="center", fontsize=9, color=C_GREEN_D)
    ax.set_ylabel("新能源汽车保有量（万辆）", color=C_GREEN_D)
    ax.set_ylim(0, 5100)
    ax.set_xlim(2014.5, 2026.1)
    ax.yaxis.set_major_formatter(FuncFormatter(_thousands))
    ax.set_xticks(YEARS)
    ax.set_xlabel("年份")

    ax2 = ax.twinx()
    ax2.plot(CHG_YEARS, CHG_TOTAL, color=C_BLUE, marker="s", markersize=6,
             linewidth=2.4, label="充电基础设施（万个）", zorder=5)
    for x, y in zip(CHG_YEARS[:-1], CHG_TOTAL[:-1]):
        ax2.text(x, y - 135, f"{y:,.1f}", ha="center", fontsize=9, color=C_BLUE)
    ax2.text(2025.16, CHG_TOTAL[-1], f"{CHG_TOTAL[-1]:,.1f}", ha="left",
             va="center", fontsize=9, color=C_BLUE)
    ax2.set_ylabel("充电基础设施保有量（万个）", color=C_BLUE)
    ax2.set_ylim(0, 2450)
    ax2.spines["top"].set_visible(False)

    ax.text(2016.4, 3450,
            "保有量与充电设施同步高增长\n车桩比由 2020 年 2.93 : 1\n降至 2025 年 2.19 : 1",
            fontsize=9.5, color="#475569", ha="left", va="top", bbox=BOX)

    ax.set_title("新能源汽车保有量与充电基础设施协同增长（2015—2025）",
                 fontsize=15, fontweight="bold", pad=14)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=10)
    _add_footer(fig, "数据来源：公安部（保有量）；中国充电联盟（EVCIPA）/ 国家能源局（充电设施，统计口径自 2020 年起）")
    fig.savefig(CHART_DIR / "02_保有量与充电设施协同增长.png")
    plt.close(fig)


def fig3_charging_structure():
    """图3：充电设施结构（公共 vs 私人）"""
    fig, ax1, ax2 = _two_panel(figsize=(10, 7.4))

    w = 0.55
    ax1.bar(CHG_YEARS, CHG_PRIVATE, width=w, color=C_GREEN_L,
            label="私人充电设施（万个）", zorder=3)
    ax1.bar(CHG_YEARS, CHG_PUBLIC, width=w, bottom=CHG_PRIVATE,
            color=C_BLUE, label="公共充电设施（万个）", zorder=3)
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
    ax1.set_title("中国充电基础设施结构演变：私人桩高速补位（2020—2025）",
                  fontsize=15, fontweight="bold", pad=14)
    ax1.legend(frameon=False, fontsize=10, loc="upper left")

    share = CHG_PUBLIC / CHG_TOTAL * 100
    ax2.plot(CHG_YEARS, share, color=C_ORANGE, marker="D", markersize=6,
             linewidth=2.2)
    for x, y in zip(CHG_YEARS, share):
        ax2.text(x, y + 1.8, f"{y:.1f}%", ha="center", fontsize=9, color=C_ORANGE)
    ax2.set_ylabel("公共设施占比（%）", color=C_ORANGE)
    ax2.set_ylim(0, 60)
    ax2.set_xticks(CHG_YEARS)
    ax2.set_xlabel("年份")
    ax2.annotate("私人桩占比由 52.0% 升至 76.5%，\n充电网络由“公共为主”转向“公私并重”",
                 xy=(2025, 23.5), xytext=(2020.1, 8),
                 fontsize=9.5, color="#475569",
                 arrowprops=dict(arrowstyle="->", color=C_GRAY, lw=1.1))

    _add_footer(fig, "数据来源：中国充电联盟（EVCIPA）/ 国家能源局；2025 年底充电基础设施总量突破 2000 万个，建成全球最大充电网络", y=0.02)
    fig.subplots_adjust(bottom=0.12)
    fig.savefig(CHART_DIR / "03_充电设施结构演变.png")
    plt.close(fig)


def fig4_battery():
    """图4：动力电池装车量结构"""
    fig, ax1, ax2 = _two_panel(figsize=(10, 7.4))

    tot = BAT_LFP + BAT_NCM
    bars = ax1.bar(BAT_YEARS, tot, width=0.5, color=C_GREEN, zorder=3,
                   label="动力电池装车量合计（GWh）")
    for i, b in enumerate(bars):
        if BAT_YEARS[i] >= 2023:
            b.set_color(C_GREEN_D)
    for x, t in zip(BAT_YEARS, tot):
        ax1.text(x, t + 16, f"{t:,.1f}", ha="center", fontsize=9,
                 color="#334155", fontweight="bold")
    ax1.set_ylabel("动力电池装车量（GWh）")
    ax1.set_ylim(0, 900)
    ax1.set_xlim(2017.6, 2025.4)
    ax1.set_title("动力电池装车量快速扩张与磷酸铁锂路线主导（2018—2025）",
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
    ax2.text(2025.0, 91, "三元锂 18.7%", fontsize=9, color="#7C2D12",
             ha="right", va="center")
    ax2.text(2025.0, 40.7, "磷酸铁锂 81.3%", fontsize=9, color="#FFFFFF",
             ha="right", va="center", fontweight="bold")
    ax2.set_ylabel("装车量结构占比（%）")
    ax2.set_ylim(0, 100)
    ax2.set_xticks(BAT_YEARS)
    ax2.set_xlabel("年份")
    ax2.annotate("2021 年磷酸铁锂装车量首次反超三元锂",
                 xy=(2021, 51.8), xytext=(2021.15, 12),
                 fontsize=9.5, color="#475569",
                 arrowprops=dict(arrowstyle="->", color="#FFFFFF", lw=1.3))

    _add_footer(fig, "数据来源：中国汽车动力电池产业创新联盟；2025 年动力电池装车量 769.7GWh，同比增长 40.4%，其中磷酸铁锂 625.3GWh", y=0.02)
    fig.subplots_adjust(bottom=0.12)
    fig.savefig(CHART_DIR / "04_动力电池装车量结构.png")
    plt.close(fig)


def fig5_tech_route():
    """图5：新能源乘用车技术路线结构（纯电 vs 插混）"""
    fig, ax1, ax2 = _two_panel(figsize=(10, 7.4))

    w = 0.5
    ax1.bar(TECH_YEARS, TECH_BEV, width=w, color=C_GREEN_D,
            label="纯电动汽车（万辆）", zorder=3)
    ax1.bar(TECH_YEARS, TECH_PHEV, width=w, bottom=TECH_BEV, color=C_ORANGE,
            label="插电式混动（含增程，万辆）", zorder=3)
    for x, b, p in zip(TECH_YEARS, TECH_BEV, TECH_PHEV):
        _seg_label(ax1, x, 0, b, 1950, f"{b:,.1f}", "#FFFFFF", "#166534", side="left", min_frac=0.058)
        _seg_label(ax1, x, b, p, 1950, f"{p:,.1f}", "#FFFFFF", "#B45309", side="right", min_frac=0.058)
        ax1.text(x, b + p + 30, f"合计 {b + p:,.1f}", ha="center", fontsize=9,
                 color="#334155", fontweight="bold")
    ax1.set_ylabel("新能源乘用车销量（万辆）")
    ax1.set_ylim(0, 1950)
    ax1.set_xlim(2020.0, 2025.95)
    ax1.yaxis.set_major_formatter(FuncFormatter(_thousands))
    ax1.set_title("新能源乘用车技术路线结构：纯电为主、插混快速补位（2021—2025）",
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
    ax2.annotate("插混占比由 17.2% 升至 35.6%，\n成为拉动增长的重要动能",
                 xy=(2025, 35.6), xytext=(2021.05, 8),
                 fontsize=9.5, color="#475569",
                 arrowprops=dict(arrowstyle="->", color=C_GRAY, lw=1.1))

    _add_footer(fig, "数据来源：中国汽车工业协会（CAAM）分动力类型统计；插混含增程式，2025 年纯电动占比 64.4%", y=0.02)
    fig.subplots_adjust(bottom=0.12)
    fig.savefig(CHART_DIR / "05_技术路线结构.png")
    plt.close(fig)


def fig6_export():
    """图6：新能源汽车出口规模与占比"""
    fig, ax = plt.subplots(figsize=(10, 6.2))
    _style_ax(ax)

    x = np.arange(len(EXP_YEARS))
    ax.bar(x, EXP_NEV, width=0.5, color=C_BLUE,
           label="新能源汽车出口（万辆）", zorder=3)
    ax.bar(x, EXP_AUTO - EXP_NEV, width=0.5, bottom=EXP_NEV,
           color="#E2E8F0", label="传统燃料汽车出口（万辆）", zorder=3)
    for xi, n, t in zip(x, EXP_NEV, EXP_AUTO):
        ax.text(xi, n / 2, f"{n:,.1f}", ha="center", va="center",
                fontsize=9, color="#FFFFFF")
        ax.text(xi, n + (t - n) / 2, f"{t - n:,.1f}", ha="center", va="center",
                fontsize=9, color="#475569")
        ax.text(xi, t + 22, f"{t:,.1f}", ha="center", fontsize=9,
                color="#334155", fontweight="bold")

    ax.set_ylabel("汽车出口量（万辆）")
    ax.set_ylim(0, 900)
    ax.yaxis.set_major_formatter(FuncFormatter(_thousands))
    ax.set_xticks(x)
    ax.set_xticklabels(EXP_YEARS)
    ax.set_xlabel("年份")
    ax.set_xlim(-0.75, 5.75)

    ax2 = ax.twinx()
    share = EXP_NEV / EXP_AUTO * 100
    ax2.plot(x, share, color=C_RED, marker="o", markersize=6.5,
             linewidth=2.4, label="新能源占出口比重（%，右轴）")
    for xi, y in zip(x, share):
        ax2.text(xi, y + 2.4, f"{y:.1f}%", ha="center", fontsize=9.5, color=C_RED)
    ax2.set_ylabel("新能源汽车出口占比（%）", color=C_RED)
    ax2.set_ylim(0, 55)
    ax2.spines["top"].set_visible(False)

    ax.text(4.35, 878,
            "2025 年新能源汽车出口 261.5 万辆，\n同比翻番，占汽车出口 36.8%",
            fontsize=9.5, color=C_RED, ha="center", va="top", bbox=BOX)

    ax.set_title("中国汽车出口结构与新能源汽车出口占比（2020—2025）",
                 fontsize=15, fontweight="bold", pad=14)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=10)
    _add_footer(fig, "数据来源：中国汽车工业协会（CAAM）、海关总署")
    fig.savefig(CHART_DIR / "06_新能源汽车出口.png")
    plt.close(fig)


def fig7_carbon():
    """图7：新能源汽车年度减碳量情景估算"""
    fig, ax1, ax2 = _two_panel(figsize=(10, 7.4))

    bars = ax1.bar(YEARS, CARBON_CUT, width=0.6, color=C_GREEN, zorder=3)
    for i, b in enumerate(bars):
        if YEARS[i] >= 2023:
            b.set_color(C_GREEN_D)
    for x, y in zip(YEARS, CARBON_CUT):
        ax1.text(x, y + 0.013, f"{y:.2f}", ha="center", va="bottom",
                 fontsize=9, color="#334155")
    ax1.set_ylabel("年度减碳量（亿吨 CO2）")
    ax1.set_ylim(0, 0.88)
    ax1.set_title("新能源汽车推动绿色低碳转型：年度与累计减碳量情景估算（2015—2025）",
                  fontsize=15, fontweight="bold", pad=14)
    ax1.text(0.015, 0.97,
             "情景假设：单车年均减碳 1.5 t CO2\n（ICCT 2025 全生命周期研究区间\n1.0~2.0 t/年，取中值）\n"
             "官方口径：2024 年中国新能源汽车\n助力全球减碳超 5000 万吨（白皮书）",
             transform=ax1.transAxes, ha="left", va="top", fontsize=9,
             color="#475569", bbox=BOX)

    ax2.plot(YEARS, CARBON_CUM, color=C_ORANGE, marker="D", markersize=5.5,
             linewidth=2.2)
    ax2.fill_between(YEARS, CARBON_CUM, color=C_ORANGE, alpha=0.12)
    for x, y in zip(YEARS, CARBON_CUM):
        if x in (2015, 2018, 2021, 2023, 2025):
            ax2.text(x, y + 0.14, f"{y:.2f}", ha="center", fontsize=9, color=C_ORANGE)
    ax2.set_ylabel("累计减碳量（亿吨 CO2）", color=C_ORANGE)
    ax2.set_ylim(0, 2.45)
    ax2.set_xticks(YEARS)
    ax2.set_xlabel("年份")

    _add_footer(fig, "保有量来源：公安部；减碳系数参考：ICCT《Life-cycle GHG emissions of passenger cars》(2025)｜本图为情景估算，非官方统计值", y=0.02)
    fig.subplots_adjust(bottom=0.12)
    fig.savefig(CHART_DIR / "07_减碳量情景估算.png")
    plt.close(fig)


def fig8_dashboard():
    """图8：综合看板（2×2）"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10.5))
    fig.suptitle("中国新能源汽车产业发展与绿色低碳转型 · 综合看板（2015—2025）",
                 fontsize=18, fontweight="bold", y=0.985, color="#0F172A")

    # (a) 销量 + 渗透率
    ax = axes[0, 0]
    _style_ax(ax)
    ax.bar(YEARS, NEV_SALES, width=0.6, color=C_GREEN, zorder=3)
    ax.set_title("(a) 新能源汽车销量与渗透率", fontsize=12, fontweight="bold")
    ax.set_ylabel("销量（万辆）")
    ax.set_xticks(YEARS[::2])
    axb = ax.twinx()
    axb.plot(YEARS, NEV_PENETRATION, color=C_BLUE, marker="o", lw=2, markersize=4)
    axb.set_ylabel("渗透率（%）", color=C_BLUE)
    axb.set_ylim(0, 62)
    axb.spines["top"].set_visible(False)

    # (b) 保有量 + 充电设施
    ax = axes[0, 1]
    _style_ax(ax)
    ax.plot(YEARS, NEV_STOCK, color=C_GREEN_D, marker="o", lw=2.2, markersize=4,
            label="新能源汽车保有量")
    ax.fill_between(YEARS, NEV_STOCK, color=C_GREEN, alpha=0.12)
    ax.set_title("(b) 保有量与充电基础设施", fontsize=12, fontweight="bold")
    ax.set_ylabel("保有量（万辆）")
    ax.set_xticks(YEARS[::2])
    ax.set_ylim(0, 5100)
    axb = ax.twinx()
    axb.plot(CHG_YEARS, CHG_TOTAL, color=C_BLUE, marker="s", lw=2.2, markersize=4,
             label="充电设施（万个）")
    axb.set_ylabel("充电设施（万个）", color=C_BLUE)
    axb.spines["top"].set_visible(False)

    # (c) 电池结构
    ax = axes[1, 0]
    _style_ax(ax)
    ax.bar(BAT_YEARS, BAT_LFP, width=0.55, color=C_GREEN, label="磷酸铁锂", zorder=3)
    ax.bar(BAT_YEARS, BAT_NCM, width=0.55, bottom=BAT_LFP, color=C_ORANGE,
           label="三元锂", zorder=3)
    ax.set_title("(c) 动力电池装车量结构（GWh）", fontsize=12, fontweight="bold")
    ax.set_ylabel("装车量（GWh）")
    ax.set_xticks(BAT_YEARS[::2])
    ax.legend(frameon=False, fontsize=9, loc="upper left")

    # (d) 出口
    ax = axes[1, 1]
    _style_ax(ax)
    ax.bar(EXP_YEARS, EXP_NEV, width=0.5, color=C_BLUE, label="新能源汽车出口", zorder=3)
    ax.bar(EXP_YEARS, EXP_AUTO - EXP_NEV, width=0.5, bottom=EXP_NEV,
           color="#E2E8F0", label="传统燃料汽车出口", zorder=3)
    ax.set_title("(d) 汽车出口结构（万辆）", fontsize=12, fontweight="bold")
    ax.set_ylabel("出口量（万辆）")
    ax.set_xticks(EXP_YEARS)
    ax.legend(frameon=False, fontsize=9, loc="upper left")

    _add_footer(fig, FOOTER, y=0.012)
    fig.tight_layout(rect=[0, 0.025, 1, 0.965])
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

    print("\n---- 关键结论摘要 ----")
    print(f"1) 新能源汽车销量：{NEV_SALES[0]:.1f} 万辆（2015）→ {NEV_SALES[-1]:,.1f} 万辆（2025），"
          f"增长约 {NEV_SALES[-1] / NEV_SALES[0]:.0f} 倍")
    print(f"2) 新车渗透率：{NEV_PENETRATION[0]}% → {NEV_PENETRATION[-1]}%，"
          f"2025 年 12 月单月已达 52.3%")
    print(f"3) 保有量：{NEV_STOCK[0]:.1f} 万辆 → {NEV_STOCK[-1]:,.0f} 万辆，"
          f"纯电动占比 {BEV_STOCK[-1] / NEV_STOCK[-1] * 100:.1f}%")
    print(f"4) 充电设施：{CHG_TOTAL[0]:.1f} 万个（2020）→ {CHG_TOTAL[-1]:,.1f} 万个（2025），"
          f"车桩比 {NEV_STOCK[-6] / CHG_TOTAL[0]:.2f}:1 → {NEV_STOCK[-1] / CHG_TOTAL[-1]:.2f}:1")
    print(f"5) 动力电池装车量：{BAT_LFP[-1] + BAT_NCM[-1]:,.1f} GWh（2025），"
          f"磷酸铁锂占比 {BAT_LFP[-1] / (BAT_LFP[-1] + BAT_NCM[-1]) * 100:.1f}%")
    print(f"6) 技术路线：2025 年纯电 {TECH_BEV[-1]:,.1f} 万辆、插混 {TECH_PHEV[-1]:,.1f} 万辆，"
          f"插混占比 {TECH_PHEV[-1] / (TECH_BEV[-1] + TECH_PHEV[-1]) * 100:.1f}%")
    print(f"7) 出口：{EXP_NEV[0]:.1f} 万辆（2020）→ {EXP_NEV[-1]:,.1f} 万辆（2025），"
          f"占汽车出口 {EXP_NEV[-1] / EXP_AUTO[-1] * 100:.1f}%")
    print(f"8) 累计减碳（情景估算）：{CARBON_CUM[-1]:.2f} 亿吨 CO2；"
          f"官方口径 2024 年助力全球减碳超 5000 万吨")
    print("\n全部完成")


if __name__ == "__main__":
    main()
