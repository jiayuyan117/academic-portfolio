"""Build the interactive bike-sharing visualisations and the tables behind them.

Input  : data/hour.csv, data/day.csv  (UCI Bike Sharing Dataset, 2011-2012)
Output : charts/*.html   four interactive figures (Plotly + Pyecharts)
         outputs/*.csv   the aggregates each figure is drawn from
         outputs/findings.json  the numbers quoted in README.md

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
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from pyecharts import options as opts
from pyecharts.charts import Scatter, Timeline
from pyecharts.commons.utils import JsCode


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CHARTS = ROOT / "charts"
OUTPUTS = ROOT / "outputs"

SEASONS = {1: "Spring", 2: "Summer", 3: "Fall", 4: "Winter"}
WEATHER = {1: "Clear", 2: "Mist/cloudy", 3: "Light rain/snow", 4: "Severe weather"}
SEASON_ORDER = ["Spring", "Summer", "Fall", "Winter"]

# Plotly.js is loaded from a CDN so each HTML file stays around 100 KB instead
# of embedding a ~3.5 MB copy of the library four times over.
PLOTLY_JS = "cdn"

RANDOM_STATE = 42


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
    figure.write_html(CHARTS / "01_sunburst.html", include_plotlyjs=PLOTLY_JS)


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
    figure.write_html(CHARTS / "02_density_contour.html", include_plotlyjs=PLOTLY_JS)


def daily_crosscheck(df: pd.DataFrame) -> pd.DataFrame:
    """Re-aggregate the hourly table to daily totals and compare with day.csv."""
    hourly = df.groupby("date", as_index=False).agg(
        hourly_cnt=("cnt", "sum"), hourly_records=("cnt", "size"))
    day = pd.read_csv(DATA / "day.csv")[
        ["dteday", "cnt", "season", "yr", "mnth", "workingday", "holiday"]
    ].rename(columns={"cnt": "day_csv_cnt"})
    day["date"] = parse_dates(day["dteday"])
    daily = hourly.merge(day.drop(columns="dteday"), on="date", how="outer")
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
        figure.add_trace(go.Heatmap(
            x=block["date"].dt.strftime("%Y-%m-%d"),
            y=block["date"].dt.dayofweek,
            z=block["day_csv_cnt"],
            customdata=block[["day_csv_cnt", "workingday", "holiday"]].astype(str),
            hovertemplate=("%{x}<br>rides=%{customdata[0]}"
                           "<br>workingday=%{customdata[1]}"
                           " &middot; holiday=%{customdata[2]}<extra></extra>"),

            visible=(year == years[0]), colorscale="YlGnBu",
            colorbar=dict(title="Rides/day"), name=str(year)))
    figure.update_layout(
        title=(f"Daily ride volume on the real calendar ({years[0]}-{years[-1]})"
               "<br><sub>Rows are weekdays. Use the buttons to switch year.</sub>"),
        xaxis=dict(type="category", tickangle=-60, nticks=24),
        yaxis=dict(tickmode="array", tickvals=list(range(7)),
                   ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
        margin=dict(t=100),
        updatemenus=[dict(
            x=0, y=1.12, xanchor="left", yanchor="bottom", direction="right", type="buttons",
            buttons=[dict(label=str(year), method="update",
                          args=[{"visible": [y == year for y in years]},
                                {"title": f"Daily ride volume on the real calendar - {year}"}])
                     for year in years])])
    figure.write_html(CHARTS / "03_calendar_heatmap.html", include_plotlyjs=PLOTLY_JS)


def build_season_timeline(df: pd.DataFrame) -> None:
    """Four weather dimensions in one frame, animated across the seasons.

    x = temperature, y = wind speed, marker size = rides in that hour,
    marker opacity = humidity. Axes are pinned to 0-1 so the frames of the
    animation stay comparable.
    """
    timeline = Timeline(init_opts=opts.InitOpts(width="1100px", height="650px"))
    max_rides = float(df["cnt"].max())
    for season in SEASON_ORDER:
        block = df[df["season_label"] == season]
        # Drop the quietest decile so the busy hours are not buried under noise.
        block = block[block["cnt"] >= block["cnt"].quantile(0.10)]
        block = block.sample(min(1000, len(block)), random_state=RANDOM_STATE)
        points = [{
            "value": [float(temp), float(wind)],
            "symbolSize": float(np.clip(4 + 24 * np.sqrt(rides / max_rides), 4, 28)),
            "itemStyle": {"color": f"rgba(31,119,180,{0.25 + 0.65 * float(hum):.2f})"},
        } for temp, wind, rides, hum in zip(
            block["temp"], block["windspeed"], block["cnt"], block["hum"])]

        chart = Scatter()
        chart.add_xaxis(block["temp"].round(3).tolist())
        chart.add_yaxis("Hours", points, label_opts=opts.LabelOpts(is_show=False))
        chart.set_global_opts(
            title_opts=opts.TitleOpts(
                title=f"{season}: temperature vs wind speed",
                subtitle="size = rides/hour, opacity = humidity"),
            xaxis_opts=opts.AxisOpts(name="Normalised temperature", min_=0, max_=1,
                                     type_="value"),
            yaxis_opts=opts.AxisOpts(name="Normalised wind speed", min_=0, max_=1),
            tooltip_opts=opts.TooltipOpts(formatter=JsCode(

                "function(p){return 'temp: '+p.value[0]+'<br>wind: '+p.value[1]"
                "+'<br>size encodes rides, opacity encodes humidity';}")))
        timeline.add(chart, season)
    timeline.add_schema(is_auto_play=True, play_interval=1800, is_loop_play=True)
    timeline.render(str(CHARTS / "04_season_timeline.html"))


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
        "registered_share": round(float(users.loc[1, "share"]), 4),
        "hourly_vs_daily_abs_diff": int(daily["crosscheck_diff"].fillna(0).abs().sum()),
        "busiest_day": {"date": peak["date"].strftime("%Y-%m-%d"),
                        "rides": int(peak["day_csv_cnt"])},

        "rides_by_time_period": {k: int(v) for k, v in by_period.items()},
    }
    (OUTPUTS / "findings.json").write_text(
        json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(findings, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()





