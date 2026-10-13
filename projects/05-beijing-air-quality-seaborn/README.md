# Beijing PM2.5, 2010–2014

**A ventilation story, not a temperature story — and 1,891 missing hours that should stay missing**

`Python` · `Seaborn` · `43,824 hourly observations` · `7 figures`

---

## Headline

Across five years of hourly readings, Beijing PM2.5 exceeded China's grade II
daily limit (75 µg/m³) in **48.5%** of hours and reached severe-pollution levels
(>250 µg/m³) in **7.3%**.

What explains the variation is air movement, not air temperature:

| Driver | Spearman ρ with PM2.5 |
| --- | ---: |
| **Cumulated wind speed** | **−0.360** |
| Dew point | +0.300 |
| Pressure | −0.142 |
| Temperature | **+0.011** |

Median PM2.5 in the calmest wind decile is **107 µg/m³** against **17 µg/m³** in
the windiest — a **6.3×** difference. By wind direction, northwesterlies run a
median of **31 µg/m³** against **98** in calm or variable hours.

![Ventilation](figures/03_ventilation_wind_speed.png)

## Two decisions that changed the conclusions

### 1 · Most of the missing data should not be imputed

2,067 PM2.5 hours are absent, spread over 214 gaps. The median gap is one hour —
but the longest is **155 consecutive hours**, and **1,341 hours sit inside gaps
longer than a day**. Linear interpolation across a six-day gap draws a smooth
ramp through what may have been an entire haze episode, then feeds that invented
shape into every correlation downstream.

This project fills only gaps of **≤3 hours** (176 hours, 0.4% of the series) and
leaves the remaining **1,891 hours missing**. Every figure reports the sample it
actually used.

![Gap audit](figures/01_missing_data_gap_audit.png)

### 2 · The temperature finding was an artefact of the statistic

Temperature gives Pearson *r* = **−0.091** but Spearman ρ = **+0.011**. When a
linear and a rank coefficient disagree on the *sign*, the association is not
monotonic and neither number belongs in a headline.

Binning temperature and plotting conditional medians shows why: PM2.5 rises and
falls twice across the temperature range, with local maxima near 0 °C and near
25 °C and the cleanest air at both extremes. That is a shape no single
coefficient can carry.

![Pearson vs Spearman](figures/05_pearson_vs_spearman.png)

![Temperature shape](figures/06_temperature_shape.png)

## Structure in time

Two cycles run at once — a winter heating season and a daily swing that bottoms
out in early afternoon and peaks after midnight. February and October are the
worst months; mid-afternoon is the cleanest hour in every month.

![Season and hour](figures/07_season_hour_heatmap.png)

## What this analysis does not claim

These are associations in observational data from a single monitoring station.
Wind clearing pollution is physically plausible, but the dataset cannot separate
transport from local emission, and `cbwd` is a source-defined combined category
rather than a measured bearing. `Ir` and `Is` count **cumulated hours** of rain
and snow, not millimetres, so they are not precipitation intensity. The 75 and
250 µg/m³ lines are *daily* standards drawn on hourly data for orientation only.

## Reproduce

```bash
pip install -r requirements.txt
python src/analyze.py
```

Writes `figures/*.png`, the tables in `outputs/`, and `outputs/findings.json` —
every number quoted above comes from that file, so this README cannot drift from
the data. The script asserts the input is a gap-free hourly index before
measuring gap lengths, because gap statistics on an irregular index would be
meaningless.

## Contents

- `src/analyze.py` — the whole pipeline, documented
- `figures/` — seven figures, 200 dpi
- `outputs/` — gap audit, correlations, wind deciles, temperature bins,
  month × hour means, plus `findings.json`
- `data/` — the source CSV, unmodified
- `source_materials/` — the original coursework script and the assignment brief

## Provenance

Data: [Beijing PM2.5 Dataset](https://archive.ics.uci.edu/dataset/381/beijing+pm2+5+data)
(Liang et al., 2015), UCI Machine Learning Repository — US Embassy Beijing PM2.5
readings paired with Beijing Capital International Airport meteorology,
2010-01-01 to 2014-12-31, used unmodified.

Developed from a course Seaborn assignment; the original script is kept in
`source_materials/` for comparison. The gap-length audit, the switch to rank
correlation, and the ventilation framing are changes I made for this portfolio
version. AI assistance was used for code structuring and English writing; the
methodological decisions and all interpretation are my own.
