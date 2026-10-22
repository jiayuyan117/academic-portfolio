# China's New Energy Vehicle Transition, 2015–2025

**Author: 闫佳玉 / Jiayu Yan. Original coursework independently completed by the author.**

**Turning eleven years of public industry statistics into a reproducible, caveat-explicit analysis**

`Python` · `pandas` · `matplotlib` · `bilingual figure sets` · `7 tables, 16 figures`

---

## Headline

Between 2015 and 2025 China's NEV sales grew roughly **50×**, from 0.33 to 16.49
million units, and NEV share of all-vehicle sales including exports went from
**1.3% to 47.9%**.
The more interesting findings are the ones that run against the simple story:

- **Charging counts have a 2025 statistical break.** EVCIPA historical counts and
  NEA's 2025 connector snapshot use different reporting scopes. Cross-break ratios
  cannot establish continuous growth or public-charging accessibility.
- **Battery chemistry reversed.** LFP went from 40% of installed capacity in 2018
  to **81%** in 2025 within the LFP + ternary subtotal.
- **Powertrain shares vary over time.** PHEV share of the BEV + PHEV subtotal
  rose from 17% in 2021 to **36%** in 2025, but fell **4.42 percentage points**
  in the latest year. This covers all vehicle types, excluding fuel-cell vehicles.
- **Export mix changed.** NEVs went from approximately 7% in 2020 to **37%**
  of China's vehicle exports in 2025.

![Dashboard](charts_en/08_dashboard.png)

## Why this project exists

Macro industry narratives are easy to assert and hard to check. The aim here was
to take a familiar claim — "China electrified its car market" — and rebuild it
from published statistics in a way a reader can audit line by line: which series,
which definition, which denominator, and which numbers are *mine* rather than
official.

## The analytical discipline

| Issue | How it is handled |
| --- | --- |
| Sales shares use different denominators | The 2025 47.9% uses CAAM **all-vehicle sales including exports**, not domestic sales or registrations |
| Charging has a 2025 statistical break | Figures separate the 2025 NEA snapshot from 2020–2024 EVCIPA counts |
| Battery subtotals differ from the full market | Shares use LFP + ternary; the residual is unallocated, not verified as other chemistries |
| Carbon impact is not an official statistic | 1.5 t CO₂ per vehicle-year is an author-selected assumption, not measured avoided emissions or a life-cycle assessment |
| Export figures vary by basis | Historical scope and kit coverage are not fully verified; rounded inputs remain labelled |

The [source audit](../../docs/NEV_SOURCE_AUDIT.md) records corrections and unresolved
definitions. Field-level provenance contains 21 `verified_external`, 93
`compiled_from_coursework`, 2 `needs_verification` observations and 1 `assumption`.
Headline endpoint comparisons describe the compilation, not a fully verified series.

Every derived indicator — new-vehicle penetration, vehicles per charger,
chemistry share, PHEV share, export share — is computed in code from the source
tables, not copied from a press release.

## Figures

English set (`charts_en/`, built by `src/build_figures_en.py`):

| | |
| --- | --- |
| ![Sales and penetration](charts_en/01_sales_and_penetration.png) | ![Fleet vs charging](charts_en/02_fleet_vs_charging.png) |
| ![Charger mix](charts_en/03_charger_mix.png) | ![Battery chemistry](charts_en/04_battery_chemistry.png) |
| ![Powertrain mix](charts_en/05_powertrain_mix.png) | ![Exports](charts_en/06_exports.png) |

The scenario estimate is kept visually separate because it combines fleet counts
with an assumed emissions factor:

![Carbon scenario](charts_en/07_carbon_scenario.png)

A Chinese figure set (`charts/`, built by `src/nev_visualization.py`) is included.
Chinese/English slide decks (`presentation/`) are historical course deliverables;
their embedded figures and narrative are not the current findings.

## Reproduce

```bash
pip install -c ../../constraints.txt -r requirements.txt
python src/nev_visualization.py   # writes data/*.csv and the Chinese charts/
python src/build_figures_en.py    # rebuilds tables and writes charts_en/
python src/data_pipeline.py --check-outputs --check-figures
python -m unittest discover -s tests -v
```

No network access is required. Both renderers use `src/data_pipeline.py` and
validated inputs from `data/source/` to regenerate the seven derived CSVs.
Strict source verification (`python src/data_pipeline.py --require-verified`)
intentionally fails while unresolved source records remain.

## Contents

- `data/` — the seven compiled tables (CSV, Chinese column names)
- `charts_en/` — English figure set, 300 dpi
- `charts/` — Chinese figure set, 300 dpi
- `src/build_figures_en.py` — English renderer
- `src/nev_visualization.py` — Chinese renderer
- `src/data_pipeline.py` — shared validation and derived indicators
- `data/source/` — source observations, assumptions and field-level provenance
- `docs/DATA_SOURCES.zh-CN.md` — compiled tables and candidate citations; see the source audit for verification status
- `docs/STORY.md`, `docs/PROJECT_PROFILE.zh-CN.md` — narrative framing
- `presentation/` — historical bilingual decks

## Provenance and limitations

The compilation draws on industry statistics with verification status recorded
per observation. This descriptive analysis contains no causal estimate of policy
effects; the carbon figure is a scenario rather than a measurement.
Original coursework was independently completed by 闫佳玉 / Jiayu Yan.
Portfolio refinements used AI for analysis design, code, interpretation, writing,
translation and verification. Original materials are retained for comparison.
