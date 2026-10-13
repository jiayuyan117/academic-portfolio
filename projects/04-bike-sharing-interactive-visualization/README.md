# Bike-Sharing Demand: Interactive Visualisation

**Four interactive figures where every visual channel is labelled — and a silent join bug found in the source data**

`Python` · `Plotly` · `Pyecharts` · `17,379 hourly observations`

**Live charts:** [sunburst](https://jiayuyan117.github.io/academic-portfolio/projects/04-bike-sharing-interactive-visualization/charts/01_sunburst.html)
· [density](https://jiayuyan117.github.io/academic-portfolio/projects/04-bike-sharing-interactive-visualization/charts/02_density_contour.html)
· [calendar](https://jiayuyan117.github.io/academic-portfolio/projects/04-bike-sharing-interactive-visualization/charts/03_calendar_heatmap.html)
· [seasonal animation](https://jiayuyan117.github.io/academic-portfolio/projects/04-bike-sharing-interactive-visualization/charts/04_season_timeline.html)

---

## The finding that matters most

The UCI Bike Sharing Dataset ships two files that are meant to reconcile:
`hour.csv` (17,379 hourly records) and `day.csv` (731 daily totals). They store
the same date column in **two different formats**:

| File | `dteday` |
| --- | --- |
| `hour.csv` | `2011/1/1` |
| `day.csv` | `2011-01-01` |

A natural `merge(hour, day, on="dteday")` therefore matches **0 of 731 days**. An
outer join silently returns twice as many rows, half of them `NaN`, and any
"hourly totals equal daily totals" check written on top of it passes
vacuously — it is comparing nothing to nothing.

Parsing both columns to datetimes first and joining on the normalised date gives
a real reconciliation: the two files **do** agree, absolute difference **0** rides
across all 731 days. Same conclusion as the naive version, reached for a reason
instead of by accident. The guard lives in `parse_dates()` in
`src/build_charts.py`, with a comment explaining why it exists.

## What the data says

| | |
| --- | --- |
| Hourly observations | 17,379 |
| Hours with zero rides | 0 |
| Hours in severe weather (code 4) | 3 |
| Registered-user share of all rides | **81.2%** |
| Busiest day | 2012-09-15, 8,714 rides |
| Hourly vs daily reconciliation | 0 rides difference over 731 days |

Ride volume by time of day — the evening peak carries 1.6× the morning peak,
which is the asymmetry a commuting-only story would miss:

| Period | Rides |
| --- | ---: |
| Day off-peak (10–16) | 1,233,459 |
| Evening peak (17–20) | 1,037,971 |
| Morning peak (6–9) | 629,742 |
| Night (21–23) | 284,998 |
| Night/early (0–5) | 106,509 |

Only three hours of severe weather exist in two years, so any claim about how
severe weather affects demand would rest on three observations. It is reported as
a count, and no such claim is made.

## The visualisation discipline

The failure mode in charts like these is a visual channel that quietly mixes
*how many observations* with *how many rides*. Each figure states what every
channel encodes:

1. **Sunburst** — season → weather → time of day. Area and value are total rides;
   the hover shows share of parent so a ring can be read without eyeballing it.
2. **Density contour** — the filled contours are a density of **observations**.
   Ride volume appears only as marker size and colour on a separate scatter
   layer, so the two quantities can never be read off the same channel.
3. **Calendar heatmap** — real calendar dates, not a synthetic index, with one
   selectable layer per year. Built on the join described above.
4. **Seasonal animation** (Pyecharts) — four dimensions in one frame:
   temperature (x), wind speed (y), rides (marker size), humidity (opacity).
   Axes pinned to 0–1 so frames stay comparable; the quietest decile is dropped
   so the busy hours are not buried.

Plotly.js is loaded from a CDN rather than inlined, which takes the sunburst HTML
from 4.8 MB to 13 KB.

## Reproduce

```bash
pip install -r requirements.txt
python src/build_charts.py
```

Writes `charts/*.html`, the aggregate tables in `outputs/`, and
`outputs/findings.json` — every number quoted in this README comes from that file,
so the README cannot drift from the data.

## Contents

- `src/build_charts.py` — the whole pipeline, documented
- `charts/` — four interactive HTML figures
- `outputs/` — the aggregates behind each figure, plus `findings.json`
- `data/` — `hour.csv`, `day.csv` and the original dataset readme

## Provenance

Data: [UCI Bike Sharing Dataset](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset)
(Fanaee-T & Gama, 2013), Washington D.C. Capital Bikeshare, 2011–2012, used
unmodified. Developed from a course visualisation assignment; the code was
rewritten for this portfolio. AI assistance was used for code structuring and
English writing; the data-quality investigation and the encoding decisions are my
own.
