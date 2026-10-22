# Bike-Sharing Demand: Interactive Visualisation

**Four interactive figures with explicit encodings and offline support.**

`Python` · `Plotly` · `17,379 hourly observations`

## Offline charts

[Sunburst](charts/01_sunburst.html) · [Density contour](charts/02_density_contour.html)
· [Calendar heatmap](charts/03_calendar_heatmap.html)
· [Seasonal animation](charts/04_season_timeline.html)

All four HTML files embed Plotly.js and their data. After rebuilding, download
and open any chart locally with the network disconnected; no CDN, MathJax or
Pyecharts/ECharts assets are needed. The former Pyecharts timeline now uses Plotly
frames with Play/Pause and a season slider. Each chart carries an offline-support
note. Embedding the runtime increases each HTML by several MB.

## Data quality and findings

The UCI hourly file uses `2011/1/1`; the daily file uses `2011-01-01`.
`parse_dates()` normalises both before joining. Unmatched dates raise an error,
so a failed join cannot masquerade as zero reconciliation difference.

| Metric | Result |
| --- | ---: |
| Hourly observations | 17,379 |
| Hours with zero rides | 0 |
| Severe-weather hours | 3 |
| Registered-user share of rides | 81.2% |
| Busiest day | 2012-09-15, 8,714 rides |
| Hourly vs daily absolute difference | 0 rides |

Registered share is total registered rides divided by all rides, selected by
the `Registered` label rather than row position. It is not a share of unique users.

| Period | Total rides |
| --- | ---: |
| Day off-peak | 1,233,459 |
| Evening peak | 1,037,971 |
| Morning peak | 629,742 |
| Night | 284,998 |
| Night/early | 106,509 |

## Visual encodings and limits

1. **Sunburst:** season → weather → time of day; area/value = total rides;
   hover = share of parent.
2. **Density contour:** contours count observed hours; sampled markers encode
   rides/hour by size and colour. Observation density is not demand volume.
3. **Calendar:** daily totals on a weekday-by-week matrix, actual dates in hover,
   year buttons and a common colour scale. Blank padding does not mean zero rides.
4. **Seasonal animation:** temperature (x), wind speed (y), rides/hour (size),
   humidity (opacity). Axes remain 0–1. The quietest decile is excluded and up to
   1,000 hours per season are sampled with seed 42; it is not the full distribution.

## Business meaning and next decision

Registered riders account for 81.2% of recorded rides, and
evening-peak volume is 1.65 times morning-peak volume over equal four-hour
windows. These aggregates motivate checking evening availability and service
reliability for regular users before expanding generic acquisition campaigns.
They do not locate shortages or establish why people ride.

Before changing fleet allocation, join station-level inventory, failed rentals
and operating costs. Evaluate a small scheduling pilot against a comparable
baseline using unserved-demand rate and cost per completed ride, with explicit
weather and calendar controls. No pilot or causal evaluation has been run here.
The 3 severe-weather hours are insufficient for a reliable
severe-weather policy; 2011–2012 citywide observations also limit current transfer.

## Reproduce

From this project directory, in the centrally prepared Python environment:

```bash
python src/build_charts.py
python -m unittest discover -s tests -v
```

The build rewrites all four `charts/*.html`, aggregate tables, `outputs/findings.json`
and this README from `render_readme()`. All exports check for external script or
stylesheet tags and the presence of the embedded Plotly runtime. Browser rendering
with networking disabled remains the final visual acceptance check.

## Provenance

[UCI Bike Sharing Dataset](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset),
Fanaee-T & Gama (2013), Washington D.C. Capital Bikeshare, 2011–2012; inputs are
unmodified. Developed from a course visualisation assignment. AI participated in
analysis design, data-quality investigation, visual encoding, code, interpretation
and English writing. Portfolio extensions are not claimed as independently
designed original coursework.
