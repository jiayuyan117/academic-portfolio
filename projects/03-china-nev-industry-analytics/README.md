# China's New Energy Vehicle Transition, 2015–2025

**A reproducible coursework analysis with selected observations verified and remaining limits recorded**

`Python` · `pandas` · `matplotlib` · `bilingual figure sets` · `7 tables, 16 figures`

---

## English reader's guide

This project compares annual NEV sales, the vehicle fleet, charging points,
battery installations, powertrain composition and exports. It also demonstrates
a simple carbon scenario. Its contribution is an auditable calculation and
visualization workflow; the supplied figures are **not yet a verified statistical
dataset**. The
[source audit dated 2026-10-21](../../docs/NEV_SOURCE_AUDIT.md) records supporting
evidence, corrections and unresolved definitions.

Start with the dashboard, then read the individual figures with their denominator
notes. The current numeric findings are generated from the input CSVs in
[`data/analysis_summary.json`](data/analysis_summary.json), including endpoint
ratios, the latest PHEV share change and export growth. Keeping the numeric
summary generated prevents an old headline from surviving a data correction.

The 116 numeric observations and one scenario parameter are maintained in
[`data/source/`](data/source/). Every field/year/value has a record in
[`provenance.json`](data/source/provenance.json): **21 `verified_external`,
93 `compiled_from_coursework`, 2 `needs_verification`, and 1 `assumption`**.
Verified records have an exact URL, publication date, observation-specific audit
summary and `source.evidence_type`: `government_original`,
`government_republication` or `secondary_media`. Media reports are not labelled
as independently inspected original statistical tables. The audit summaries are
paraphrases, not invented verbatim quotations.

The 2021 PHEV input is corrected from 60.6 to **60.3** (10,000 vehicles), following
the MIIT briefing dated 2022-01-12. The previous value is retained in the
provenance correction log. The BEV/PHEV series covers **all vehicle types**.

![Dashboard](charts_en/08_dashboard.png)

## Why this project exists

The aim is to turn a coursework analysis into a workflow a reader can inspect:
which values were supplied, how years were joined, what each ratio divides by,
and which assumptions remain unsupported. It is descriptive and does not
identify policy effects, market causation or investment returns.

## The analytical discipline

| Issue | How it is handled |
| --- | --- |
| Sales share can use different denominators | The 2025 published 47.9% uses all-vehicle sales **including exports**, confirmed by MOFCOM's republication of MIIT/CAAM (2026-01-15). The calculated 47.94% and published rounded value are separate columns. This is not domestic sales, registrations or passenger retail. |
| Charging has a statistical break | 2020–2024 EVCIPA counts and 2025 NEA connectors use different scope/reporting systems. NEA documented the change on 2025-07-31 and published year-end counts on 2026-01-21. Figures break the connecting lines and hatch the 2025 bars. The derived CSV exports the scope label. |
| Two battery chemistries are not necessarily the full market | Shares use LFP + ternary only. No residual is labelled as a verified “other chemistry” category. |
| Powertrain coverage | All vehicle types; shares use the BEV + PHEV subtotal, excluding fuel-cell vehicles. 2021 is supported by the MIIT/SCIO briefing, 2025 by Economic Observer reporting CAAM; 2022–2024 values remain unverified. |
| Carbon impact is assumed | The 1.5 t/vehicle-year parameter is an author-selected `assumption`, not a pending statistical observation or an ICCT-derived Chinese factor. Year-end fleet is an imperfect proxy for annual vehicle-years. |
| Export figures vary by basis and precision | 2025 CAAM counts are supported by government republication. The 2020 NEV count is **about** 70,000, so its calculated share is approximate. Historical scope and kit coverage are not fully verified. |

Ratios, subtotals, differences and cumulative scenarios share one implementation
in `src/data_pipeline.py`. Both rendering scripts start from the same validated
inputs and independently regenerate the seven derived CSVs. The powertrain table
is now `data/05_新能源汽车全车型技术路线_2021-2025.csv`; the misleading passenger-car
filename has been removed. Column labels identify battery/powertrain subtotals,
sales including exports, and the export residual.
The legacy Chinese chart 02 filename contains “协同增长” only for existing image
references; its updated title and content explicitly show the statistical break
and make no continuous-growth claim.

## Business interpretation and limits

- **Charging planning:** treat 2025 as a separate NEA snapshot. Differences across
  the scope break are not physical additions or continuous growth. A location
  decision also needs regional coverage, access restrictions, power, uptime and
  utilization; these annual aggregates cannot establish an investment case.
- **Battery procurement:** chemistry shares can frame questions about supplier
  exposure and product mix. Explaining the shift requires price, safety,
  performance and model-level evidence that this project does not contain.
- **Product planning:** compare endpoint shares with the latest annual change.
  A higher endpoint PHEV share does not imply uninterrupted growth or identify
  customer preferences.
- **Export strategy:** volume and mix help prioritize further market research,
  but revenue, margins, destinations, tariffs and local requirements are needed
  to evaluate profitability.
- **Sustainability communication:** the carbon figure illustrates sensitivity
  to a constant factor. It omits differences in mileage, grid intensity,
  manufacturing emissions, vehicle lifetime and BEV/PHEV usage. It must not be
  used as measured avoided emissions or a life-cycle assessment.

## Figures

English set (`charts_en/`, built by `src/build_figures_en.py`):

| | |
| --- | --- |
| ![Sales and penetration](charts_en/01_sales_and_penetration.png) | ![Fleet vs charging](charts_en/02_fleet_vs_charging.png) |
| ![Charger mix](charts_en/03_charger_mix.png) | ![Battery chemistry](charts_en/04_battery_chemistry.png) |
| ![Powertrain mix](charts_en/05_powertrain_mix.png) | ![Exports](charts_en/06_exports.png) |

The carbon scenario is kept visually separate because it combines the partly verified
fleet series with an explicit assumed factor:

![Carbon scenario](charts_en/07_carbon_scenario.png)

A Chinese figure set (`charts/`, built by `src/nev_visualization.py`) is also
included.

## Historical Office versions — ARCHIVE

**All existing Office documents outside `source_materials` are historical course
deliverables. Current results are the updated README, derived tables and figures.
Do not use embedded charts or narrative in the old Office files as current findings.**

The current project contains these two Office files, both historical:

- [Chinese historical portfolio](presentation/闫佳玉_新能源汽车产业数据分析作品集_中文.pptx)
- [English historical portfolio](presentation/Jiayu_Yan_NEV_Data_Analytics_Portfolio_EN.pptx)

## Reproduce

```bash
pip install -c ../../constraints.txt -r requirements.txt
python src/nev_visualization.py   # writes data/*.csv and the Chinese charts/
python src/build_figures_en.py    # independently rebuilds tables, writes charts_en/
python src/data_pipeline.py --check-outputs --check-figures
python -m unittest discover -s tests -v
```

No network access is required. For data-only rebuilding, run
`python src/data_pipeline.py --write`. To enforce externally verified evidence,
run `python src/data_pipeline.py --require-verified`; **this intentionally fails
for the current compilation**. Ordinary validation permits explicit unresolved
statuses and reports their counts. Strict mode requires evidence for observations
and excludes explicitly classified assumptions.

To correct a value, update its input CSV and matching provenance record together.
A verified record requires an exact document URL, publication date, evidence
type, observation-specific evidence summary and locator in the supplied dated audit.
The validator checks that these fields exist; a human still has to assess the
evidence. It does not visit URLs or certify their contents.

## Contents

- `data/source/` — six independent observation CSVs, one assumption CSV and field/year/value provenance
- `data/` — seven derived CSVs (Chinese column names) and a generated English JSON summary
- `charts_en/` — English figure set, 300 dpi
- `charts/` — Chinese figure set, 300 dpi
- `src/build_figures_en.py` — English renderer
- `src/nev_visualization.py` — Chinese renderer
- `src/data_pipeline.py` — shared schema, year alignment, provenance and arithmetic validation
- `tests/test_data_pipeline.py` — invalid-input, provenance, join and output regression tests
- `docs/DATA_SOURCES.zh-CN.md` — original compiled tables, candidate citations and unresolved definitions
- `docs/STORY.md`, `docs/PROJECT_PROFILE.zh-CN.md` — narrative framing
- `presentation/` — historical bilingual course decks; see ARCHIVE notice above

## Provenance and limitations

The supplied audit supports selected production, sales, exports, stock,
charging, battery and powertrain observations. The original CAAM image tables
were not independently transcribed; the EVCIPA 2024 original body was unavailable;
media evidence retains its secondary classification. Historical observations
without exact evidence remain explicitly unverified. The 2025 battery share
uses LFP + ternary only, and the gap against a reported full-market total is
unallocated, not proven to be another chemistry.

The annual project does not add a monthly series. No global avoided-emissions
claim is used to validate the carbon scenario. AI assistance was used to integrate
the supplied source audit, update code and prose, and check local consistency.
Original source materials and historical Office files were not edited.
