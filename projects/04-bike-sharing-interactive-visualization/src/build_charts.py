"""Build the interactive bike-sharing visualisations and the tables behind them.

Input  : data/hour.csv, data/day.csv  (UCI Bike Sharing Dataset, 2011-2012)
Output : charts/*.html   four self-contained, offline Plotly figures
         outputs/*.csv   the aggregates each figure is drawn from
         outputs/findings.json, README.md  computed findings and report

Design notes
------------
* Every figure states what each visual channel encodes, because the common
  failure mode in these charts is a legend that silently mixes "number of
  observations" with "number of rides".
* The density contour is a *sample-count* density. Ride volume is encoded by
  marker size on a separate scatter layer, never by the contour fill.
* The calendar heatmap uses real calendar dates and the daily totals from
  day.csv, and the hourly table is independently re-aggregated to cross-check
  them. The cross-check difference is reported rather than assumed to be zero.
"""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHARTS = ROOT / "charts"
OUTPUTS = ROOT / "outputs"

SEASONS = {1: "Spring", 2: "Summer", 3: "Fall", 4: "Winter"}
WEATHER = {1: "Clear", 2: "Mist/cloudy", 3: "Light rain/snow", 4: "Severe weather"}
SEASON_ORDER = ["Spring", "Summer", "Fall", "Winter"]

# Each delivered HTML carries its own runtime and data, including the animation.
PLOTLY_JS = True

RANDOM_STATE = 42


class _ResourceParser(HTMLParser):
    """Inspect tags without mistaking URLs inside Plotly.js for asset loads."""

    def __init__(self):
        super().__init__()
        self.external_resources = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "iframe", "img", "source"} and attrs.get("src"):
            self.external_resources.append(attrs["src"])
        if tag == "link" and attrs.get("href"):
            self.external_resources.append(attrs["href"])


def validate_offline_html(html: str) -> None:
    parser = _ResourceParser()
    parser.feed(html)
    if parser.external_resources:
        raise ValueError(f"HTML requires external assets: {parser.external_resources}")
    if "plotly.js v" not in html.lower() or "Plotly.newPlot" not in html:
        raise ValueError("Missing inline Plotly runtime or chart")


def write_offline_html(figure: go.Figure, filename: str) -> None:
    """One export path for every chart; no CDN or MathJax download."""
    if not figure.layout.sliders:
        figure.update_layout(margin_b=90)
    html = figure.to_html(
        include_plotlyjs=PLOTLY_JS, include_mathjax=False, full_html=True,
        auto_play=False, config={"responsive": True, "displaylogo": False})
    html = html.replace(
        "</body>",
        '<p style="margin:12px 24px;font:13px sans-serif;color:#536471">'
        'Offline supported: this chart includes everything needed to view it.</p></body>')
    validate_offline_html(html)
    (CHARTS / filename).write_text(html, encoding="utf-8")


def time_period(hour: int) -> str:
    """Bucket an hour-of-day into the five commuting periods used throughout."""
    if hour <= 5:
        return "Night/early"
    if hour <= 9:
        return "Morning peak"
    if hour <= 16:
        return "Day off-peak"
    if hour <= 20:
        return "Evening peak"
    return "Night"


def parse_dates(series: pd.Series) -> pd.Series:
    """Parse the ``dteday`` column of either input file.

    The two shipped files do not agree on a date format: ``hour.csv`` stores
    ``2011/1/1`` while ``day.csv`` stores ``2011-01-01``. Joining them on the
    raw string therefore matches nothing, which silently voids any
    hourly-vs-daily reconciliation. Both are normalised to datetimes here and
    the join below uses that normalised key.
    """
    return pd.to_datetime(series, format="mixed").dt.normalize()


def load_hourly() -> pd.DataFrame:

    df = pd.read_csv(DATA / "hour.csv")
    df["date"] = parse_dates(df["dteday"])
    df["timestamp"] = df["date"] + pd.to_timedelta(df["hr"], unit="h")

    df["season_label"] = df["season"].map(SEASONS)
    df["weather_label"] = df["weathersit"].map(WEATHER)
    df["time_period"] = df["hr"].map(time_period)
    non_zero = df["cnt"].replace(0, np.nan)
    df["share_registered"] = df["registered"] / non_zero
    df["share_casual"] = df["casual"] / non_zero
    return df


def user_type_share(df: pd.DataFrame) -> pd.DataFrame:
    """Casual vs registered split of total rides."""
    table = pd.DataFrame({
        "user_type": ["Casual", "Registered"],
        "rides": [int(df["casual"].sum()), int(df["registered"].sum())],
    })
    table["share"] = table["rides"] / table["rides"].sum()
    return table


def registered_share(users: pd.DataFrame) -> float:
    """Select by user type, independently of row order or integer labels."""
    indexed = users.set_index("user_type")
    if not indexed.index.is_unique:
        raise ValueError("User types must be unique")
    return float(indexed.loc["Registered", "share"])


def sunburst_table(df: pd.DataFrame) -> pd.DataFrame:
    """Rides aggregated over season -> weather -> time period."""
    table = df.groupby(["season_label", "weather_label", "time_period"], as_index=False).agg(
        rides=("cnt", "sum"), records=("cnt", "size"))
    parent_total = table.groupby(["season_label", "weather_label"])["rides"].transform("sum")
    table["share_of_parent"] = table["rides"] / parent_total
    return table


def build_sunburst(table: pd.DataFrame) -> None:
    """Three-level composition of ride volume, with explicit parent shares."""
    labels, parents, values = ["All"], [""], [int(table["rides"].sum())]
    for season, by_season in table.groupby("season_label"):
        labels.append(season)
        parents.append("All")
        values.append(int(by_season["rides"].sum()))
        for weather, by_weather in by_season.groupby("weather_label"):
            node = f"{season} | {weather}"
            labels.append(node)
            parents.append(season)
            values.append(int(by_weather["rides"].sum()))
            for row in by_weather.itertuples():
                labels.append(f"{node} | {row.time_period}")
                parents.append(node)
                values.append(int(row.rides))

    figure = go.Figure(go.Sunburst(
        labels=labels, parents=parents, values=values, branchvalues="total",
        hovertemplate=("<b>%{label}</b><br>Rides: %{value:,}"
                       "<br>Share of parent: %{percentParent:.1%}<extra></extra>")))
    figure.update_layout(
        title=("Ride composition: season &#8594; weather &#8594; time of day"
               "<br><sub>Area and value are total rides. Click a ring to drill in.</sub>"),
        margin=dict(t=90, l=10, r=10, b=10))
    write_offline_html(figure, "01_sunburst.html")


def build_density_contour(df: pd.DataFrame) -> None:
    """Where in temperature-humidity space the observations live, and how busy they are.

    The filled contours are a density of *observations*. Ride volume appears
    only as marker size and colour on the sampled scatter layer, so the two
    quantities can never be read off the same channel.
    """
    sample = df.sample(min(1200, len(df)), random_state=RANDOM_STATE)
    figure = go.Figure()
    figure.add_trace(go.Histogram2dContour(
        x=df["temp"], y=df["hum"], colorscale="Blues", contours_coloring="fill",
        nbinsx=35, nbinsy=35, name="Observation density", showscale=False))
    figure.add_trace(go.Scatter(
        x=sample["temp"], y=sample["hum"], mode="markers",
        customdata=sample[["cnt", "season_label", "weather_label", "time_period"]],
        marker=dict(size=np.clip(np.sqrt(sample["cnt"]), 3, 28), color=sample["cnt"],
                    colorscale="Viridis", showscale=True,
                    colorbar=dict(title="Rides/hour"), line=dict(width=0)),
        hovertemplate=("temp=%{x:.2f} &nbsp; hum=%{y:.2f}"
                       "<br>rides/hour=%{customdata[0]}"
                       "<br>%{customdata[1]} &middot; %{customdata[2]}"
                       " &middot; %{customdata[3]}<extra></extra>"),
        name="Sampled hours"))
    figure.update_layout(
        title=("Demand in temperature-humidity space"
               "<br><sub>Contours = how many hours fall in that cell. "
               "Marker size and colour = rides in that hour.</sub>"),
        xaxis_title="Normalised temperature", yaxis_title="Normalised humidity",
        margin=dict(t=90))
    write_offline_html(figure, "02_density_contour.html")


def daily_crosscheck(df: pd.DataFrame) -> pd.DataFrame:
    """Re-aggregate the hourly table to daily totals and compare with day.csv."""
    hourly = df.groupby("date", as_index=False).agg(
        hourly_cnt=("cnt", "sum"), hourly_records=("cnt", "size"))
    day = pd.read_csv(DATA / "day.csv")[
        ["dteday", "cnt", "season", "yr", "mnth", "workingday", "holiday"]
    ].rename(columns={"cnt": "day_csv_cnt"})
    day["date"] = parse_dates(day["dteday"])
    daily = hourly.merge(day.drop(columns="dteday"), on="date", how="outer",
                         validate="one_to_one")
    if daily[["hourly_cnt", "day_csv_cnt"]].isna().any().any():
        raise ValueError("Hourly/daily reconciliation has unmatched calendar dates")
    daily["year"] = daily["date"].dt.year
    daily["weekday"] = daily["date"].dt.day_name()
    daily["crosscheck_diff"] = daily["hourly_cnt"] - daily["day_csv_cnt"]
    return daily.sort_values("date").reset_index(drop=True)



def build_calendar_heatmap(daily: pd.DataFrame) -> None:
    """Calendar view on real dates, one selectable layer per year."""
    years = sorted(int(y) for y in daily["year"].dropna().unique())
    figure = go.Figure()
    for year in years:
        block = daily[daily["year"] == year]
        # Heatmap z is a matrix: weekday rows and Monday-based week columns.
        # Padding is blank, not a fabricated zero-demand observation.
        monday = block["date"].min() - pd.Timedelta(days=block["date"].min().dayofweek)
        week = ((block["date"] - monday).dt.days // 7).to_numpy()
        weekdays = block["date"].dt.dayofweek.to_numpy()
        weeks = pd.date_range(monday, periods=int(week.max()) + 1, freq="7D")
        values = np.full((7, len(weeks)), np.nan)
        hover = np.full((7, len(weeks), 4), "", dtype=object)
        values[weekdays, week] = block["day_csv_cnt"].to_numpy()
        hover[weekdays, week] = np.column_stack([
            block["date"].dt.strftime("%Y-%m-%d"),
            block[["day_csv_cnt", "workingday", "holiday"]].astype(str)])
        figure.add_trace(go.Heatmap(
            x=weeks.strftime("%Y-%m-%d"), y=list(range(7)), z=values,
            customdata=hover, hoverongaps=False,
            hovertemplate=("%{customdata[0]}<br>rides=%{customdata[1]}"
                           "<br>workingday=%{customdata[2]}"
                           " &middot; holiday=%{customdata[3]}<extra></extra>"),
            zmin=0, zmax=float(daily["day_csv_cnt"].max()),
            visible=(year == years[0]), colorscale="YlGnBu",
            colorbar=dict(title="Rides/day"), name=str(year)))
    figure.update_layout(
        title=(f"Daily ride volume on the real calendar ({years[0]}-{years[-1]})"
               "<br><sub>Rows are weekdays. Use the buttons to switch year.</sub>"),
        xaxis=dict(type="date", title="Week starting Monday", tickangle=-60, nticks=12),
        yaxis=dict(tickmode="array", tickvals=list(range(7)),
                   ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
        margin=dict(t=100),
        updatemenus=[dict(
            x=0, y=1.12, xanchor="left", yanchor="bottom", direction="right", type="buttons",
            buttons=[dict(label=str(year), method="update",
                          args=[{"visible": [y == year for y in years]},
                                {"title": f"Daily ride volume on the real calendar - {year}"}])
                     for year in years])])
    write_offline_html(figure, "03_calendar_heatmap.html")


def build_season_timeline(df: pd.DataFrame) -> None:
    """Four weather dimensions in one frame, animated across the seasons.

    x = temperature, y = wind speed, marker size = rides in that hour,
    marker opacity = humidity. Axes are pinned to 0-1 so the frames of the
    animation stay comparable.
    """
    frames = []
    max_rides = float(df["cnt"].max())
    for season in SEASON_ORDER:
        block = df[df["season_label"] == season]
        # Drop the quietest decile so the busy hours are not buried under noise.
        block = block[block["cnt"] >= block["cnt"].quantile(0.10)]
        block = block.sample(min(1000, len(block)), random_state=RANDOM_STATE)
        scatter = go.Scatter(
            x=block["temp"], y=block["windspeed"], mode="markers", name=season,
            marker=dict(
                size=np.clip(4 + 24 * np.sqrt(block["cnt"] / max_rides), 4, 28),
                sizemode="diameter", color="#1f77b4",
                opacity=0.25 + 0.65 * block["hum"]),
            customdata=block[["cnt", "hum"]],
            hovertemplate=(
                "temp=%{x:.3f}<br>wind=%{y:.3f}<br>rides/hour=%{customdata[0]}"
                "<br>humidity=%{customdata[1]:.3f}<extra>%{fullData.name}</extra>"))
        frames.append(go.Frame(name=season, data=[scatter], traces=[0]))
    figure = go.Figure(data=frames[0].data, frames=frames)
    animation = dict(frame=dict(duration=1800, redraw=True),
                     transition=dict(duration=0), fromcurrent=True)
    figure.update_layout(
        title=("Seasonal temperature vs wind speed"
               "<br><sub>Size = rides/hour; opacity = humidity. "
               "Quietest decile excluded; at most 1,000 sampled hours per season.</sub>"),
        height=750, margin=dict(t=100, b=190),
        xaxis=dict(title="Normalised temperature", range=[0, 1], autorange=False),
        yaxis=dict(title="Normalised wind speed", range=[0, 1], autorange=False),
        sliders=[dict(active=0, y=-0.08, currentvalue=dict(prefix="Season: "), steps=[
            dict(label=season, method="animate",
                 args=[[season], dict(mode="immediate",
                                      frame=dict(duration=0, redraw=True),
                                      transition=dict(duration=0))])
            for season in SEASON_ORDER])],
        updatemenus=[dict(type="buttons", direction="right", x=0, y=-0.28,
                         xanchor="left", yanchor="top", buttons=[
            dict(label="Play", method="animate", args=[None, animation]),
            dict(label="Pause", method="animate",
                 args=[[None], dict(mode="immediate", frame=dict(duration=0),
                                    transition=dict(duration=0))])])])
    write_offline_html(figure, "04_season_timeline.html")


def render_readme(findings: dict) -> str:
    """Keep the report's numbers and offline delivery contract in the pipeline."""
    f = findings
    periods = "\n".join(f"| {name} | {rides:,} |"
                        for name, rides in f["rides_by_time_period"].items())
    ratio = (f["rides_by_time_period"]["Evening peak"]
             / f["rides_by_time_period"]["Morning peak"])
    return f"""# Bike-Sharing Demand: Interactive Visualisation

**Four interactive figures with explicit encodings and offline support.**

`Python` · `Plotly` · `{f['hourly_rows']:,} hourly observations`

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
| Hourly observations | {f['hourly_rows']:,} |
| Hours with zero rides | {f['zero_count_hours']:,} |
| Severe-weather hours | {f['severe_weather_hours']:,} |
| Registered-user share of rides | {f['registered_share']:.1%} |
| Busiest day | {f['busiest_day']['date']}, {f['busiest_day']['rides']:,} rides |
| Hourly vs daily absolute difference | {f['hourly_vs_daily_abs_diff']:,} rides |

Registered share is total registered rides divided by all rides, selected by
the `Registered` label rather than row position. It is not a share of unique users.

| Period | Total rides |
| --- | ---: |
{periods}

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

Registered riders account for {f['registered_share']:.1%} of recorded rides, and
evening-peak volume is {ratio:.2f} times morning-peak volume over equal four-hour
windows. These aggregates motivate checking evening availability and service
reliability for regular users before expanding generic acquisition campaigns.
They do not locate shortages or establish why people ride.

Before changing fleet allocation, join station-level inventory, failed rentals
and operating costs. Evaluate a small scheduling pilot against a comparable
baseline using unserved-demand rate and cost per completed ride, with explicit
weather and calendar controls. No pilot or causal evaluation has been run here.
The {f['severe_weather_hours']} severe-weather hours are insufficient for a reliable
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
unmodified. Developed from a course visualisation assignment. AI assistance was
used for code structuring and English writing.
"""


def main() -> None:
    CHARTS.mkdir(exist_ok=True)
    OUTPUTS.mkdir(exist_ok=True)

    df = load_hourly()
    users = user_type_share(df)
    sun = sunburst_table(df)
    daily = daily_crosscheck(df)

    users.to_csv(OUTPUTS / "02_user_type_share.csv", index=False, encoding="utf-8-sig")
    sun.to_csv(OUTPUTS / "03_sunburst_aggregation.csv", index=False, encoding="utf-8-sig")
    daily.to_csv(OUTPUTS / "04_daily_calendar_crosscheck.csv", index=False,
                 encoding="utf-8-sig")

    build_sunburst(sun)
    build_density_contour(df[df["cnt"] > 0])
    build_calendar_heatmap(daily)
    build_season_timeline(df[df["cnt"] > 0])

    peak = daily.loc[daily["day_csv_cnt"].idxmax()]
    by_period = df.groupby("time_period")["cnt"].sum()
    findings = {
        "hourly_rows": int(len(df)),
        "zero_count_hours": int((df["cnt"] == 0).sum()),
        "severe_weather_hours": int((df["weathersit"] == 4).sum()),
        "registered_share": round(registered_share(users), 4),
        "hourly_vs_daily_abs_diff": int(daily["crosscheck_diff"].abs().sum()),
        "offline_support": {"supported": True, "renderer": "Plotly",
                            "javascript": "inline", "external_assets": []},
        "busiest_day": {"date": peak["date"].strftime("%Y-%m-%d"),
                        "rides": int(peak["day_csv_cnt"])},

        "rides_by_time_period": {k: int(v) for k, v in by_period.items()},
    }
    (OUTPUTS / "findings.json").write_text(
        json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")
    (ROOT / "README.md").write_text(render_readme(findings), encoding="utf-8")
    print(json.dumps(findings, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()





