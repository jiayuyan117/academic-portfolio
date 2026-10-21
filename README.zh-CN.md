# 闫佳玉 — 数据分析作品集

广东工业大学 **大数据管理与应用** 本科
· 申请方向：数据科学 / 商业分析硕士（美国 · 新加坡 · 香港）

**[→ 浏览作品集网站](https://jiayuyan117.github.io/academic-portfolio/)**

English version: [README.md](README.md)

---

## 这个仓库想证明什么

这些项目围绕两个问题：**这个结论经得起检验吗？它能支持什么决策？**

八个项目来自本科课程与团队研究，检验技能特征能否改善岗位类别分类、预测能否优于
简单基准、市场联动估计如何依赖识别假设，以及数据质量是否足以支持业务结论。

否证结果和方法纠错与正面发现一起呈现。没有拒绝零假设并不证明完全没有差异；
观测数据的相关性也不等于干预效果。

**01–07** 的既有 CI 已分别留下数值校验、分析与图表重建或 Java 测试的成功记录。
两个计量项目检查输入 SHA-256，并以 `rtol=1e-6` 比对合计 **586 个数值**。
**08** 已完成来源重建、分类与抽取实验，并保留预测供独立重算指标。

## 30 秒导读

我以大数据管理与应用的本科训练为基础，申请**美国、新加坡、香港的数据科学 /
商业分析硕士**。作品集将模型评估、数据质量与研究表达连接到具体决策，并明确证据边界。

建议首先阅读 **08 · Does the Skill Signal Help?**。数据科学路线为 **08 → 01 → 02**，
关注 NLP 评估、预测检验与识别假设；商业分析路线为 **08 → 06 → 03**，
关注岗位信息、客群划分与行业证据。**04、05、07** 补充交互表达、缺失数据分析和工程能力。

| 项目 | 阅读重点 |
| --- | --- |
| **[08 · Does the Skill Signal Help?](projects/08-nlp-job-postings/README.md)** | 首读：NLP 评估、否证结果与可复现性 |
| [01 · 股票时间序列预测](projects/01-equity-time-series-forecasting/) | 简单基准与残差诊断 |
| [02 · 沪港市场联动](projects/02-shanghai-hongkong-market-linkages/) | 对识别假设的敏感性 |
| [03 · 新能源汽车转型](projects/03-china-nev-industry-analytics/) | 来源追溯与市场分母口径 |
| [04 · 共享单车可视化](projects/04-bike-sharing-interactive-visualization/) | 日期对账与交互图表 |
| [05 · 北京 PM2.5](projects/05-beijing-air-quality-seaborn/) | 缺失机制与观测关联 |
| [06 · 消费交易](projects/06-consumer-behaviour-matplotlib/) | 客群证据与决策限制 |
| [07 · Java 员工系统](projects/07-workforce-system-java/) | 数据结构与不变量测试 |

阅读顺序从 08 开始，原有 01–07 目录编号保留。

## 项目（共 8 个）

### 08 · [Does the Skill Signal Help?](projects/08-nlp-job-postings/README.md)
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

**归属说明：** 原团队作者为 **闫佳玉 / 凌泳婷 / 王安娜**。
作品集版本采用 **AI-assisted integration（AI 辅助整合）**；
团队研究贡献记录于
[项目 README](https://github.com/jiayuyan117/academic-portfolio/blob/main/projects/08-nlp-job-postings/README.md)。
[阅读研究简报](https://jiayuyan117.github.io/academic-portfolio/projects/08-nlp-job-postings/report.html)。

### 01 · [股票时间序列预测](projects/01-equity-time-series-forecasting/)
`statsmodels` · `ARMA/ARIMA` · `固定起点样本外检验` · `每次运行校验 252 个数值`

仅用训练集的 BIC 选出 MA(2)，在完全未被触碰的 20 天留出样本上比"零收益率"预测
的 RMSE 好 **0.29%**——但 Ljung–Box 在滞后 20 阶**拒绝**残差无自相关，ARCH-LM
也拒绝方差恒定（*p* = 4e-09）。项目的设计目的就是让这两个事实同时可见：单个窗口上
0.29% 的优势，并不是一个可以拿去用的模型。

**决策含义：** 保留简单基准，先补充多个时间窗口和交易成本验证，再考虑部署。

### 02 · [沪港市场联动](projects/02-shanghai-hongkong-market-linkages/)
`VAR / VECM` · `Johansen` · `格兰杰检验` · `每次运行校验 334 个数值`

上证冲击看起来能解释恒生指数 10 步预测误差方差的 **32.4%**——直到把 Cholesky
排序反过来，同一个量变成 **0.35%**。数据、模型、样本完全一样，只换了识别假设。
同时 VAR(7) 在两个市场的 MAE 上都输给零收益率基准，两个方向的格兰杰检验都不显著。

**决策含义：** 不据此形成方向性对冲策略，也不把排序敏感的方差分解当成因果归因。

### 03 · [中国新能源汽车转型 2015–2025](projects/03-china-nev-industry-analytics/)
`pandas` · `matplotlib` · `7 张整理数据表` · `16 张中英文图表`

2025 年中汽协**含出口、全车型**汽车销量中，新能源汽车占 **47.9%**；
这与国内销量、注册登记量口径不同。[来源审计](docs/NEV_SOURCE_AUDIT.md)
纠正 2021 年插混输入，披露 **2025 年充电设施统计口径断点**，
区分电池两类小计与全市场总量，并标明舍入和尚未核实的历史记录。
减碳计算是示意情景，不是实测减排量。

**决策含义：** 充电投资需要位置、利用率和功率数据；全国数量及有统计断点的
时间序列不能单独说明哪里服务能力不足。

### 04 · [共享单车交互可视化](projects/04-bike-sharing-interactive-visualization/)
`Plotly` · `可离线交互图表` · `17,379 条观测` · [在线图表](https://jiayuyan117.github.io/academic-portfolio/projects/04-bike-sharing-interactive-visualization/charts/01_sunburst.html)

UCI 共享单车数据集的两个文件把日期分别存成 `2011/1/1` 和 `2011-01-01`，所以最自然
的那个连接**在 731 天里一天都没对上**——建立在它上面的任何"小时汇总等于日汇总"
的校验都会通过，因为它在拿空值和空值比较。正确解析后，两个文件确实完全一致。
四张交互图内嵌渲染资源，可离线阅读，并说明每个视觉通道的含义。

**决策含义：** 需求规划前先对账；具体站点调度仍需车辆可用量和服务成本数据。

### 05 · [北京 PM2.5，2010–2014](projects/05-beijing-air-quality-seaborn/)
`Seaborn` · `43,824 条小时观测` · `7 张图`

**48.5% 的有效小时观测**高于 75 µg/m³；这里借用日标准数值作为参考，不能解释为
小时超标率或日达标率。累计风速的 Spearman ρ = **−0.360**，温度为 **+0.011**；
累计风速最低十分位的 PM2.5 中位数是最高十分位的 **6.3 倍**。
温度的 Pearson *r*（−0.091）和 Spearman ρ（+0.011）符号不同，
需结合条件中位数曲线理解关系，不能仅凭符号断言非单调性。另外，2,067 个
缺失小时里有 1,341 个落在超过一天的缺口里（最长 155 个连续小时）。
短缺口策略审计仍保留 **91% 缺失**。核心图表及统计只使用原始有效观测，
排除全部 2,067 个缺失小时，不使用审计中生成的插值序列。

**决策含义：** 可将通风指标作为户外作业预警的待验证候选变量，结合实时监测和
后续时间段检验；不能由这些相关性推断限产或调度的效果。

### 06 · [消费交易：检验客群划分是否有据](projects/06-consumer-behaviour-matplotlib/)
`Matplotlib` · `8,000 条交易` · `Bootstrap 置信区间 · ANOVA · 置换检验`

任务书问"哪类客户消费更多"。先做检验再回答：**五个候选划分里有四个未检出显著均值差异**
（年龄段 *p* = 0.44、性别 0.52、城市等级 0.77、支付方式 0.90）。收入与消费额的相关
系数是 −0.010，95% 置信区间 [−0.032, +0.012]，约束了样本中的线性关联大小，
并不证明完全独立。只有会员等级有区分度（*p* = 1.0 × 10⁻⁶，对截尾稳健），
而它的因果方向无法识别：等级授予规则未记录，可能取决于历史消费。月度收入在置换零假设
区间内落了**全部 12 个月**，本分析未建立季节性证据。
口径统一为：**原始 8,020 行，删除 20 行完全重复记录，得到 8,000 笔交易**。
检验和区间以交易为单位，尚未校正同一客户重复交易的相关性，
因此属于探索性结果，业务行动前还需客户层面的验证。

**决策含义：** 暂不依据这些人口特征排名重分配营销预算。下一步可设计随机优惠实验，
以增量贡献利润为主指标；这里没有声称已经开展该实验。

### 07 · [Java 员工信息系统](projects/07-workforce-system-java/)
`Java 17` · `部门树` · `平衡员工索引` · `JUnit 5`

部门层级和员工索引必须始终描述同一批员工。系统实现新增、转岗、删除、
薪资区间查询，并在每次操作后检查部门归属、唯一性、排序和总人数是否一致。
使用 `TreeMap` 参考模型，并覆盖有序输入、删除、转岗和结构不变量。

**决策含义：** 部门与员工索引一致性是可靠人数报表的基础；实际生产系统还需要
持久化、访问控制和审计记录。


## 可复现性

本轮整合所依据的 01–07 旧 CI 已有以下成功记录。这些记录只覆盖既有项目，
不代表新 NLP 训练完成，也不代表本次整合已通过验证。

| 项目 | 已有 CI 成功记录与范围 | 复现命令 |
| --- | --- | --- |
| 01 股票预测 | Windows：11 张表 / 252 个参考数值，`rtol=1e-6` | `python run_analysis.py` |
| 02 市场联动 | Linux 与 Windows：8 张表 / 334 个参考数值，`rtol=1e-6` | `python run_analysis.py` |
| 03 新能源汽车 | Linux：图表重建与数据/语义检查；未核实来源仍保留标注 | 依次运行 `python src/nev_visualization.py` 和 `python src/build_figures_en.py` |
| 04 共享单车 | Linux：交互图重建与日期对账检查 | `python src/build_charts.py` |
| 05 北京 PM2.5 | Linux：分析与图表重建、时间索引和缺口审计 | `python src/analyze.py` |
| 06 消费交易 | Linux：分析与图表重建、推断语义检查 | `python src/analyze.py` |
| 07 Java 员工系统 | Linux / Java 17：Maven 验证、JUnit 和参考模型测试 | `mvn verify` |
| 08 招聘文本 NLP | 本轮训练未完成；数据确认与模型验证分别记录 | 见[项目 README](projects/08-nlp-job-postings/README.md) |


项目 01 和 02 交付的是**校验器**而不只是运行脚本：它会核对每个输入文件的 SHA-256
是否与 `provenance.json` 一致，清空 notebook 所有输出后从零重跑，任何单元格报错
即失败，然后把重新生成的每个数值与存档参考值比对。库版本的静默变化会表现为构建
失败，而不是一个悄悄变了的结论。

表中命令在各项目目录运行。01–06 使用项目依赖声明与根目录 `constraints.txt`，
01–07 的文档环境为 CPython 3.12.10 和 JDK 17。CI 按任务分别重跑 notebook、
重建分析与图表或执行 Java 测试。08 使用单独的复现说明，不属于上述成功记录的覆盖范围。
01 的 Linux 优化器结果超出原有容差，因此未声称它能在 Linux 上通过 Windows
数值基准；参考值和容差均未修改。
已有证据见 [workflow 运行记录](https://github.com/jiayuyan117/academic-portfolio/actions/workflows/build.yml)
及 [CI 历史说明](docs/REVIEW_RESOLUTION.md#boundaries-of-this-evidence)。
安装、统一重建和容器说明见 [REPRODUCING.md](REPRODUCING.md)。
README 为独立维护的文案，生成 `findings.json` 不会自动更新 README。


```bash
git clone https://github.com/jiayuyan117/academic-portfolio.git
cd academic-portfolio
python -m venv .venv
# 01 使用 Windows；按 REPRODUCING.md 激活虚拟环境。
python -m pip install -c constraints.txt -r requirements.txt
python tools/rebuild.py --project 01
```

## 这些项目体现的能力

**NLP 研究设计** — 纯文本、仅词典与融合特征对照；雇主不交叉评估；
区分类别准确率与精确跨度抽取；将当前复现状态与原报告结果分开陈述。

**计量经济学与预测** — ARMA/ARIMA、VAR/VECM、单位根与协整检验、格兰杰因果、
脉冲响应与方差分解、残差与 ARCH 诊断、对预先设定基准的固定起点样本外评估。

**推断纪律** — Bootstrap 与 Fisher-z 置信区间、单因素 ANOVA 与 Kruskal-Wallis
（含多重比较的 Bonferroni 校正）、置换零假设区间、截尾均值稳健性检验，以及
如实报告不确定性及可检测差异边界的判断力。

**数据工程与数据质量** — 输入文件哈希校验、连接完整性检查、插值前的缺口长度审计、
日期与单位归一化、独立来源之间的交叉核对、随机种子固定的确定性端到端流水线。

**可视化** — Matplotlib 与 Seaborn 做静态图，Plotly 提供可离线交互；
原始 Pyecharts 课程材料保留供对照；
显式说明每个视觉通道的编码；每张图都标注数据来源、分母口径和已知局限。


**研究表达** — 把"测量到的""估算的""仍然是假设的"三类内容分开陈述；中英文双语交付。

## 学术诚信与 AI 使用说明

01–07 源于我的本科课程作业。这些项目的 `source_materials/` 目录保留了
未经修改的原始课程提交物和数据集，可以直接对照查看从作业到作品集版本的演进过程
——包括项目 04 和 05 中，作品集版本纠正我自己早期作业里方法错误的地方。


08 源于 **闫佳玉 / 凌泳婷 / 王安娜** 的团队研究，团队研究贡献记录于
[项目 README](projects/08-nlp-job-postings/README.md)。
作品集改编采用 **AI-assisted integration（AI 辅助整合）**。

AI 被用于代码结构整理、英文写作、校验工具和评审驱动的修订，包括 08 的作品集整合。
原始课程材料单独保留。决策建议描述证据含义和未来验证步骤，不冒充已做的干预实验。
估算、情景与公开统计分开标注；尚未完成的来源核验明确披露。

本仓库中没有任何结论被表述得比证据所能支持的更确定。模型失效的地方，失效本身就是
发现。

## 联系方式

GitHub: [@jiayuyan117](https://github.com/jiayuyan117)

代码采用 MIT 许可。第三方数据集仍遵循其原始许可条款，详见各项目的来源说明。
