# 闫佳玉 — 数据分析作品集

**作者：闫佳玉 / Jiayu Yan**

广东工业大学 **大数据管理与应用** 本科
· 申请方向：商业分析 / 数据科学硕士（美国 · 新加坡 · 香港）

**[→ 浏览作品集网站](https://jiayuyan117.github.io/academic-portfolio/)**

English version: [README.md](README.md)

---

## 研究重点

我关注模型在什么条件下能为决策提供有用的信息。项目将污染预警、市场预测和招聘文本
特征与简单基准比较，并检查支撑这些比较的数据质量。

作品集包含本科课程与自主学习中发展的 8 个项目，涵盖统计与 NLP 研究、交互可视化
及 Java 工程实践。报告链接到方法、来源和已保存的证据，便于读者核查发现及其局限。

所有预测类结论都在未参与拟合和调参的数据上评分。否证结果和方法纠错与正面发现
一起呈现。没有拒绝零假设并不证明完全没有差异；观测数据的相关性也不等于干预效果。

**01–05** 的 CI 已留下数值校验与分析重建记录。两个计量项目检查输入 SHA-256，
并以 `rtol=1e-6` 比对合计 **586 个数值**。**06** 已完成来源重建、分类与抽取实验，
并保留预测供独立重算指标。

## 30 秒导读

**商业分析路线：05 → 03 → 06 → 04。数据科学路线：06 → 07 → 02 → 05。**
可先选一篇简报阅读，再通过预测文件和校验程序深入检查。

| 精选 | 筛选理由 | 证据入口 |
| --- | --- | --- |
| [05 · 次日预警决策](projects/05-beijing-air-quality-seaborn/FIRST_READ.html) | 2013 年按成本选阈值、2014 年一次性测试；每日成本比持续性规则低 0.126，95% CI [0.066, 0.195] | [测试日预测](projects/05-beijing-air-quality-seaborn/outputs/08_alert_test_predictions.csv) |
| [03 · 提前测算市场规模](projects/03-china-nev-industry-analytics/FIRST_READ.html) | 滚动起点回测：所有测算模型平均都低估；S 曲线拟合上限从 6% 到 100% 再到 54% | [回测预测](projects/03-china-nev-industry-analytics/results/backtest_forecasts.csv) |
| [06 · NLP 评估](projects/06-nlp-job-postings/report.html) | 雇主隔离的特征比较，分类与抽取独立评估 | [预测与校验说明](projects/06-nlp-job-postings/README.md#what-is-independently-checkable) |
| [07 · 时序机器学习](projects/07-market-direction/report.html) | 模型选择包含基准，后续测试区间报告不确定性 | [验证程序](projects/07-market-direction/verify.py) |
| [02 · 预测检验与识别假设](projects/02-shanghai-hongkong-market-linkages/FIRST_READ.html) | 500 个起点的 Diebold–Mariano 检验；不依赖变量排序的方差分解 | [稳健性结果](projects/02-shanghai-hongkong-market-linkages/results/robustness_summary.json) |

**补充：** 04 需求数据对账与交互图表；01 预测诊断；08 持久化、版本校验分页与 HTTP 测试。

<details>
<summary>完整项目目录</summary>

| 项目 | 阅读重点 |
| --- | --- |
| [01 · 股票时间序列预测](projects/01-equity-time-series-forecasting/) | 简单基准与残差诊断 |
| [02 · 沪港市场联动](projects/02-shanghai-hongkong-market-linkages/) | 滚动预测检验与识别假设敏感性 |
| [03 · 新能源汽车转型](projects/03-china-nev-industry-analytics/) | 市场测算回测、分母口径与来源追溯 |
| [04 · 共享单车可视化](projects/04-bike-sharing-interactive-visualization/) | 日期对账与交互图表 |
| [05 · 北京 PM2.5](projects/05-beijing-air-quality-seaborn/) | 缺失数据审计与按成本决策的次日预警 |
| [06 · Does the Skill Signal Help?](projects/06-nlp-job-postings/README.md) | NLP 评估、否证结果与可复现性 |
| [07 · When the Baseline Wins](projects/07-market-direction/report.html) | 时序机器学习、包含基准的模型选择与分块置信区间 |
| [08 · 商品目录](projects/08-product-catalog/PROJECT.html) | 文件持久化、旧版本冲突与 HTTP 边界测试 |

</details>

### 商业分析：从问题到决策

| 项目 | 决策问题与方法 | 证据及行动边界 |
| --- | --- | --- |
| [05 · 运营预警](projects/05-beijing-air-quality-seaborn/README.md) | 今晚要不要为明天发预警？2010–2012 拟合，2013 按成本选阈值，2014 一次性测试。 | 模型抓到 181 个预警日中的 174 个，误报 103 次，持续性规则误报 168 次。3:1 的漏报/误报成本比是假设，需与承担成本的团队确认。 |
| [03 · 市场测算](projects/03-china-nev-industry-analytics/README.md) | 新能源渗透率能否提前预测？在 2020–2024 每个起点重新拟合各测算模型。 | 所有模型都低估；拐点之前数据无法确定 S 曲线上限。市场规模应按上限情景呈现，国内口径（50.8%）与含出口口径分开。 |
| [06 · 岗位信息质量](projects/06-nlp-job-postings/README.md) | 在隔离雇主的留出集上比较文本与技能特征，并独立评估抽取。 | 融合 Macro-F1 为 0.7348，文本为 0.7406，未达到研究设定的改善标准；实际运营价值尚未测量。 |
| [04 · 需求数据](projects/04-bike-sharing-interactive-visualization/README.md) | 规划前先对账小时与日需求文件。 | 直接连接 731 天一天都对不上；正确解析后两个文件完全一致。 |

每个项目按 **问题 → 数据与方法 → 结果 → 决策意义 → 限制** 阅读。
建议属于学术分析解释，不是已部署的干预或实测 ROI。

## 补充简报与完整证据

<details>
<summary>展开全部 8 项简报（建议先读上面的精选入口）</summary>

### 01 · [股票时间序列预测](projects/01-equity-time-series-forecasting/)
`statsmodels` · `ARMA/ARIMA` · `固定起点样本外检验` · `每次运行校验 252 个数值`

仅用训练集的 BIC 选出 MA(2)，在完全未被触碰的 20 天留出样本上比"零收益率"预测
的 RMSE 好 **0.29%**——但 Ljung–Box 在滞后 20 阶**拒绝**残差无自相关，ARCH-LM
也拒绝方差恒定（*p* = 4e-09）。单个窗口上的微小优势尚不足以证明实际预测价值。

**决策含义：** 保留简单基准，先补充多个时间窗口和交易成本验证，再考虑部署。

### 02 · [沪港市场联动](projects/02-shanghai-hongkong-market-linkages/)
`VAR / VECM` · `Johansen` · `广义方差分解` · `Diebold–Mariano` · `每次运行校验 334 个数值`

上证冲击看起来能解释恒生指数 10 步预测误差方差的 **32.4%**——把 Cholesky 排序
反过来，同一个量变成 **0.35%**。不依赖排序的广义方差分解给出 **24.6%**；同日残差
相关系数 0.568 的平方（≈32.3%）几乎解释了全部份额，提示该分解主要反映同日共振，
尚不能据此确立因果溢出。在 **500 个滚动一步预测**中，VAR(7) 在两个市场都显著
劣于零收益率预测（Diebold–Mariano *p* = 0.042 和 0.012）。

**决策含义：** 可进一步研究共振对同期风险分析的意义；现有结果尚未验证对冲策略或次日方向信号。

### 03 · [中国新能源汽车转型 2015–2025](projects/03-china-nev-industry-analytics/)
`pandas` · `scipy` · `7 张整理数据表` · `16 张中英文图表` · `滚动起点回测`

2025 年中汽协**含出口、全车型**销量中新能源占 **47.9%**，国内口径为 **50.8%**。
回测在 2020–2024 每个起点只用当时可得的数据，重新拟合朴素、线性趋势和 S 曲线
测算模型：所有模型**平均都低估**（−3.1 至 −20.1 个百分点），S 曲线拟合上限
随数据到来从 **6% 变为 100% 再变为 54%**。[来源审计](docs/NEV_SOURCE_AUDIT.md)
纠正 2021 年插混输入，并披露 **2025 年充电设施统计口径断点**。减碳计算是示意情景，
不是实测减排量。

**决策含义：** 市场规模应按上限情景呈现并每年重估；充电投资还需要位置、利用率和功率数据。

### 04 · [共享单车交互可视化](projects/04-bike-sharing-interactive-visualization/)
`Plotly` · `可离线交互图表` · `17,379 条观测` · [在线图表](https://jiayuyan117.github.io/academic-portfolio/projects/04-bike-sharing-interactive-visualization/charts/01_sunburst.html)

UCI 共享单车数据集的两个文件把日期分别存成 `2011/1/1` 和 `2011-01-01`，所以最自然
的那个连接**在 731 天里一天都没对上**——建立在它上面的任何"小时汇总等于日汇总"
的校验都会通过，因为它在拿空值和空值比较。正确解析后，两个文件确实完全一致。
四张交互图内嵌渲染资源，可离线阅读，并说明每个视觉通道的含义。

**决策含义：** 需求规划前先对账；具体站点调度仍需车辆可用量和服务成本数据。

### 05 · [北京 PM2.5：从缺失数据到次日预警](projects/05-beijing-air-quality-seaborn/)
`Seaborn` · `statsmodels` · `43,824 条小时观测` · `8 张图` · `分块 bootstrap`

先做审计：2,067 个缺失小时里有 1,341 个落在超过一天的缺口里（最长 155 个连续小时），
因此不做插值，所有核心结论只用原始观测。累计风速与 PM2.5 的 Spearman ρ = **−0.360**；
累计风速最低十分位的 PM2.5 中位数是最高十分位的 **6.3 倍**。

这些关联被转化为可检验的决策。日均值超过 75 µg/m³ 且至少有 20 个有效小时记为预警日。
基于当天数据的 logistic 模型在 2010–2012 拟合，在 2013 按成本选阈值（假设漏报一个
预警日的成本等于三次误报），在 2014 一次性测试。模型抓到 **181 个预警日中的 174 个**，
误报 **103 次**；最优持续性规则每天都发预警，误报 168 次。每日成本降低 **0.126，
95% 分块 bootstrap 置信区间 [0.066, 0.195]**，成本比从 1:1 到 10:1 排名都不变。
加入次日实测气象（相当于完美天气预报的上限）还能再减少 55 次误报。

**决策含义：** 以该模型替代持续性规则做试点，确认成本比，部署前接入天气预报数据。

### 06 · [Does the Skill Signal Help?](projects/06-nlp-job-postings/README.md)
`招聘文本 NLP` · `SkillSpan` · `21,663 条招聘记录` · `20 个类别` · `雇主不交叉划分`

加入 SkillSpan Skill + Knowledge 词典特征未达到研究设定的提升标准：
测试集 Macro-F1 分别为纯文本 **0.7406**、仅词典 **0.5003**、
等权融合 **0.7348**。岗位分类与精确跨度抽取回答不同问题，分别评估。

**证据状态：** 21,663 条记录、20 个类别和 employer-disjoint split（雇主不交叉划分）
已对照固定公开来源核验，研究样本可精确重建。全量分类、技能抽取及
TF-IDF/CNN/冻结 MiniLM 对照均已运行，并保留预测供独立重算。
本轮与论文不一致的指标分开列示。`+0.02` 的 Macro-F1 绝对增益
是原研究记录的阈值；未提供可独立核验时间戳的预注册材料。

**决策含义：** 大类岗位路由继续保留纯文本基准；将抽取结果用于技能画像前，
需要直接验证具体技能跨度。
[阅读研究简报](https://jiayuyan117.github.io/academic-portfolio/projects/06-nlp-job-postings/report.html)。

### 07 · [When the Baseline Wins](projects/07-market-direction/report.html)

在课程机器学习实验的基础上深化的研究，采用全新实现和 UCI Istanbul Stock Exchange
公开数据（Akbilgic，2013；CC BY 4.0），没有上传课程原始数据或课程代码。

开发期模型选择包含基准，最终选中历史上涨频率。五段滚动测试共 216 个日期：
基准 Brier 为 **0.245605**，本地特征逻辑回归为 **0.246611**。
配对差值 **+0.001006**，95% 分块置信区间 **[−0.002279, +0.004296]**。
收益率单特征、PCA、滞后海外市场特征及窗口稳健性比较未建立可靠的预测优势。
这是单市场历史研究，不是盈利证明。

七项时序约束测试、六张结果表完整重跑及 24 组区间复算已在本地通过；
项目带独立 CI 工作流。在项目目录使用独立环境安装项目依赖后运行 `python verify.py` 和
`python -m unittest discover -s tests -v`，首次运行自动下载并校验公开数据。

### 08 · [商品目录：可核验的数据修改](projects/08-product-catalog/PROJECT.html)

以教材商品管理章节为选题的 Java 工程项目，代码为本人独立实现，不转载教材代码。提供本地 HTTP
增删改查、整数分金额、原子文件快照和旧版本冲突检查。
新增版本校验分页、SKU／价格确定性排序；写入后旧分页链接返回 409。
本机实际通过 13 组测试，包括真实 HTTP 请求、完整分页遍历、重启恢复、
竞争修改和写入失败。查询仍为扫描，不宣称索引性能提升。
GitHub Pages 只能展示静态简报，Java 后端需本地运行。

不声称存在真实用户、研究成果或已部署的业务系统。
详见[运行说明与测试证据](projects/08-product-catalog/README.md)及
[来源说明](projects/08-product-catalog/PROVENANCE.md)。本项目不使用 workflow。

</details>

## 可复现性

各项目按其研究内容进行验证。NLP 工作流重算已保存预测的指标，并运行真实数据小样本实验；
全量模型训练通过单独的本地命令完成，不将其表述为常规 CI 的覆盖范围。

| 项目 | 已有 CI 成功记录与范围 | 复现命令 |
| --- | --- | --- |
| 01 股票预测 | Windows：11 张表 / 252 个参考数值，`rtol=1e-6` | `python run_analysis.py` |
| 02 市场联动 | Linux 与 Windows：8 张表 / 334 个参考数值，`rtol=1e-6`；滚动起点与广义方差分解扩展 | `python robustness.py`；`python run_analysis.py` |
| 03 新能源汽车 | Linux：图表重建、数据/语义检查及回测防泄漏测试；未核实来源仍保留标注 | `python src/nev_visualization.py`；`python src/build_figures_en.py`；`python src/market_backtest.py` |
| 04 共享单车 | Linux：交互图重建与日期对账检查 | `python src/build_charts.py` |
| 05 北京 PM2.5 | Linux：分析与图表重建、缺口审计及次日目标测试 | `python src/analyze.py`；`python src/alert_model.py` |
| 06 招聘文本 NLP | 来源重建、已保存预测校验及小样本训练检查 | `python run.py verify`；`python run.py smoke` |
| 07 时序机器学习 | 本地完整重跑、7 项时序测试、预测与区间校验；已有独立 CI | `python verify.py`；`python -m unittest discover -s tests -v` |
| 08 商品目录 | Windows / JDK 21，Java 17 编译目标；13 组测试，无 workflow | `powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 test` |

项目 01 和 02 交付的是**校验器**而不只是运行脚本：它会核对每个输入文件的 SHA-256
是否与 `provenance.json` 一致，清空 notebook 所有输出后从零重跑，任何单元格报错
即失败，然后把重新生成的每个数值与存档参考值比对。库版本的静默变化会表现为构建
失败，而不是一个悄悄变了的结论。

表中命令在各项目目录运行。01–05 使用项目依赖声明与根目录 `constraints.txt`，
文档环境为 CPython 3.12.10。06、07 有各自的 workflow 和复现说明。
01 的 Linux 优化器结果超出原有容差，因此未声称它能在 Linux 上通过 Windows
数值基准；参考值和容差均未修改。
已有证据见 [workflow 运行记录](https://github.com/jiayuyan117/academic-portfolio/actions/workflows/build.yml)。
安装、统一重建和容器说明见 [REPRODUCING.md](REPRODUCING.md)。
README 为独立维护的文案，生成的结果文件不会自动更新 README。

```bash
git clone https://github.com/jiayuyan117/academic-portfolio.git
cd academic-portfolio
python -m venv .venv
# 01 使用 Windows；按 REPRODUCING.md 激活虚拟环境。
python -m pip install -c constraints.txt -r requirements.txt
python tools/rebuild.py --project 05
```

## 这些项目体现的能力

**决策分析** — 在验证年按成本选择预警阈值、检验不同成本比假设下的结论、按明确上限
情景测算市场规模，并区分模型能支持什么、还缺什么证据。

**预测评估** — 滚动起点与严格时间切分、每次比较都保留简单基准、Diebold–Mariano 检验、
配对移动分块 bootstrap 置信区间，以及针对目标和特征的防泄漏测试。

**NLP 研究设计** — 纯文本、仅词典与融合特征对照；雇主不交叉评估；
区分类别准确率与精确跨度抽取。

**计量经济学** — ARMA/ARIMA、VAR/VECM、单位根与协整检验、格兰杰因果、
Cholesky 与广义方差分解、残差与 ARCH 诊断。

**数据工程与数据质量** — 输入文件哈希校验、连接完整性检查、插值前的缺口长度审计、
数据完整性规则、日期与单位归一化、来源交叉核对、随机种子固定的确定性流水线。

**可视化与表达** — Matplotlib、Seaborn 与可离线 Plotly 图表，每张图标注来源、分母口径
和已知局限；把"测量到的""估算的""仍是假设的"分开陈述；中英文双语交付。

## 作者声明

**作者：闫佳玉 / Jiayu Yan。** 本仓库全部项目均为作者本人作品，由本科课程作业和
自主学习深化而成。AI 工具用于编程辅助与英文润色；全部代码、结果与结论均经作者本人
审核与验证。课程材料与教材代码均未转载；07 采用全新实现和 CC BY 4.0 公开数据。

决策建议描述证据含义和未来验证步骤，不冒充已做的干预实验。
估算、假设的成本比、情景与公开统计分开标注；尚未完成的来源核验明确披露。

本仓库中没有任何结论被表述得比证据所能支持的更确定。模型失效的地方，失效本身就是
发现。

## 联系方式

GitHub: [@jiayuyan117](https://github.com/jiayuyan117)

代码采用 MIT 许可。第三方数据集仍遵循其原始许可条款，详见各项目的来源说明。
