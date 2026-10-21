# NEV source audit — 2026-10-21

This audit distinguishes publisher pages, government republications, media
reports and calculations from rounded published inputs. A located URL is not
evidence that an unread original statistical table was verified.

## Sales: the denominator includes exports

The [CAAM release](http://www.caam.org.cn/chn/1/cate_38/con_5237000.html),
2026-01-14, contains image tables. The original page was located; the tables
were not independently transcribed in this audit.
The [Ministry of Commerce republication of MIIT's report](https://cif.mofcom.gov.cn/cif/html/mobile_data/market/sell/qcxsqk/2026/1/1768439584405.html),
2026-01-15, explicitly attributes its figures to CAAM:

| Period | NEV sales, 10,000 vehicles | All-vehicle sales, 10,000 vehicles | Published share |
| --- | ---: | ---: | ---: |
| 2025 annual | 1649.0 | 3440.0 | 47.9% |
| December 2025 | 171.0 | 327.2 | 52.3% |

Both ratios use all-vehicle sales **including exports**. They are not domestic
sales shares, registration shares or passenger-car retail shares.
The annual NEV production value is 1662.6; all-vehicle production is 3453.1.
Annual exports are 709.8 for all vehicles and 261.5 for NEVs, in the same units.

[CCTV, 2026-01-16](https://auto.cctv.cn/2026/01/16/ARTIHiGCxfhjlDHdinYWaaz6260116.shtml)
reports domestic NEV sales of 1387.5 and a domestic share of 50.8%.
These are different measures and must not replace the 47.9% series silently.

## Technology: all vehicle types; BEV/PHEV subtotal

The [MIIT briefing transcript hosted by the State Council Information Office](http://www.scio.gov.cn/xwfb/bwxwfb/gbwfbh/gyhxxhb/202307/t20230703_720565.html)
is dated 2022-01-12 (the migrated URL contains 2023). It reports 2021 NEV
sales of 352.1, BEV sales of 291.6 and PHEV sales of **60.3**, not 60.6,
in 10,000 vehicles. BEV+PHEV is 351.9; the subtotal excludes fuel-cell vehicles.

[Economic Observer, 2026-01-15](http://www.eeo.com.cn/2026/0115/779531.shtml),
reporting CAAM's briefing, gives 2025 BEV sales of 1062.2 and PHEV sales
of 586.1. These are all-vehicle figures, not passenger-car figures.
The 35.56% computed PHEV share uses the BEV+PHEV subtotal, 1648.3.
It is below the compiled 2024 share; do not imply uninterrupted growth.

## Charging: a 2025 statistical break

[National Energy Administration, 2026-01-21](https://www.nea.gov.cn/20260121/33ceb49dc4eb472aa48c62ab3b2ddbbb/c.html)
reports 2009.2 total charging facilities/connectors, 471.7 public and 1537.5
private, in units of 10,000. The public share calculated from these counts
is 23.48%; this measures counts, not power, accessibility or capacity.

The [NEA briefing dated 2025-07-31](https://www.nea.gov.cn/20250731/9c2d1f4c046c4b25ac6f8882a7ffb01e/c.html)
explicitly states that the statistical scope was adjusted and a new reporting
system introduced, with local authorities reporting and NEA reviewing totals.
It describes the measurement unit as charging connectors.
Therefore the pre-2025 EVCIPA series and the 2025 NEA observation must be
visually separated or prominently marked as a break. Their difference is not
a defensible estimate of physical additions under a fixed scope.

The 2024 [EVCIPA original release](https://www.evcipa.org.cn/newsinfo/8137834.html)
was located but its body could not be retrieved. A
[2025-01-23 media republication](https://finance.sina.com.cn/stock/hkstock/ggscyd/2025-01-23/doc-inefxxva4710922.shtml)
reports 1281.8 total and 357.9 public. Do not claim direct original-table verification.

## Battery chemistry: two-chemistry subtotal, not total market

The existing LFP+NCM series is a subtotal. Either label it consistently as such
or introduce independently sourced total-market denominators. Do not silently
switch denominators within the time series.

| Year | LFP+NCM subtotal, GWh | Reported total, GWh | Published LFP market share | Evidence |
| --- | ---: | ---: | ---: | --- |
| 2018 | 55.3 | 56.9 | 39.0% | [2019-01-14, China Securities Journal republication](https://wap.eastmoney.com/a/201901141026324874.html) |
| 2019 | 60.7 | 62.2 | 32.5% | [2020-02-24, China Securities Journal](https://www.cs.com.cn/ssgs/gsxw/202002/t20200224_6028706.html) |
| 2020 | 63.3 | 63.6 | 38.3% | [2021-01-21, Economic Information Daily](http://dz.jjckb.cn/www/pages/webpage2009/html/2021-01/21/content_70968.htm) |
| 2021 | 154.1 | 154.5 | 51.7% | [2022-01-14, China Economic Net republication](http://auto.cyol.com/gb/articles/2022/01/14/content_QG67lsRKX.html) |
| 2022 | 294.2 | 294.6 | 62.4% | [2023-01-18, CCTV republication](https://auto.cctv.com/2023/01/18/ARTIQBfyUbVO2uPPhU5JJre6230118.shtml) |
| 2023 | 387.2 | 387.7 | 67.3% | [2024-01-11, Beijing News](https://m.bjnews.com.cn/detail/1704971856168579.html) |
| 2024 | 548.0 | 548.4 | 74.6% | [2025-01-13, Beijing News](https://m.bjnews.com.cn/detail/1736757251168421.html) |
| 2025 | 769.4 | 769.7 | 81.2% | [2026-01-16, Securities Times](https://www.stcn.com/article/detail/3596988.html) and [Zhitong/Sina](https://finance.sina.com.cn/stock/hkstock/hkstocknews/2026-01-16/doc-inhhnuuv5501330.shtml) |

These are media reports/republications, not independently inspected original
alliance tables. For 2025, 625.3 LFP + 144.1 NCM = 769.4, and 625.3/769.4
is 81.27% **within those two chemistries**. The 0.3 GWh difference from 769.7
is an unallocated difference; the available evidence does not establish that
all of it is another chemistry.

## Vehicle stock and rounding

[Xinhua, 2026-01-26, citing the Ministry of Public Security](https://www.xinhuanet.com/20260126/62f6b9393e264b9ebef0019a3efc4557/c.html)
reports 4397 NEVs and 3022 BEVs (10,000 vehicles) at year-end 2025, with a
published BEV share of 68.74%. Recomputing from rounded counts gives 68.73%;
keep a calculated share distinct from the published statistic.

[MPS, 2025-01-18](https://www.mps.gov.cn/n2254314/n6409334/c9939035/content.html)
reports 3140 NEVs and 2209 BEVs for 2024 and a published share of 70.34%;
the rounded-count calculation is 70.35%.

## Remaining limits

[People's Daily Overseas Edition, 2022-08-23](http://paper.people.com.cn/rmrbhwb/html/2022-08/23/content_25935571.htm)
supports only **about 70,000** NEV exports in 2020, not a precise 70,000
count or a 7.04% export share. Retain its approximate status.

The [ICCT July 2025 lifecycle study](https://theicct.org/publication/electric-cars-life-cycle-analysis-emissions-europe-jul25)
concerns EU passenger cars and reports lifecycle emissions in g CO2e/km.
It does not establish a general 1.0–2.0 tonnes/year reduction for all Chinese
NEVs. Treat the project's 1.5 tonnes/vehicle/year as an **illustrative assumption**,
not an ICCT-derived Chinese statistic. Multiplying year-end stock by a full-year
factor does not measure annual fleet emissions avoided.

Other historical observations remain individually marked according to the
evidence actually available; no missing publication date or source is invented.
