"""Offline input, provenance and arithmetic validation shared by both renderers."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "source"
DATA = ROOT / "data"
SCHEMAS = {
    "sales": (2015, 2025, {"auto_sales_10k": "10k_vehicles", "nev_output_10k": "10k_vehicles",
                          "nev_sales_10k": "10k_vehicles", "reported_share_pct": "percent"}),
    "fleet": (2015, 2025, {"nev_fleet_10k": "10k_vehicles", "bev_fleet_10k": "10k_vehicles"}),
    "charging": (2020, 2025, {"chargers_total_10k": "10k_chargers", "chargers_public_10k": "10k_chargers"}),
    "battery": (2018, 2025, {"lfp_gwh": "GWh", "nmc_gwh": "GWh"}),
    "powertrain": (2021, 2025, {"bev_sales_10k": "10k_vehicles", "phev_sales_10k": "10k_vehicles"}),
    "exports": (2020, 2025, {"nev_exports_10k": "10k_vehicles", "total_exports_10k": "10k_vehicles"}),
}
TABLES = {
    "sales": "01_汽车与新能源汽车产销_2015-2025.csv",
    "fleet": "02_新能源汽车保有量_2015-2025.csv",
    "charging": "03_充电基础设施_2020-2025.csv",
    "battery": "04_动力电池装车量_2018-2025.csv",
    "powertrain": "05_新能源汽车全车型技术路线_2021-2025.csv",
    "exports": "06_新能源汽车出口_2020-2025.csv",
    "carbon": "07_绿色低碳成效情景估算_2015-2025.csv",
}
COLUMNS = {
    "year": "年份", "auto_sales_10k": "汽车总销量_万辆", "nev_output_10k": "新能源汽车产量_万辆",
    "nev_sales_10k": "新能源汽车销量_万辆", "nev_share_of_new_sales_pct": "新能源汽车占全车型销量含出口_计算百分比",
    "reported_share_pct": "原始记录销量占比_百分比",
    "nev_fleet_10k": "新能源汽车保有量_万辆", "bev_fleet_10k": "其中纯电动汽车保有量_万辆",
    "bev_share_pct": "纯电动占比_百分比", "chargers_total_10k": "充电设施总量_万个",
    "chargers_public_10k": "公共充电设施_万个", "chargers_private_10k": "私人充电设施_万个",
    "public_share_pct": "公共占比_百分比", "vehicles_per_charger": "车桩比_辆每桩",
    "lfp_gwh": "磷酸铁锂装车量_GWh", "nmc_gwh": "三元锂电池装车量_GWh",
    "total_gwh": "两类电池装车量小计_GWh", "lfp_share_pct": "磷酸铁锂占两类小计_百分比",
    "bev_sales_10k": "纯电动汽车销量_万辆", "phev_sales_10k": "插电式混动汽车销量_万辆",
    "total_10k": "纯电与插混全车型小计_万辆", "phev_share_pct": "插混占两类小计_百分比",
    "nev_exports_10k": "新能源汽车出口_万辆", "total_exports_10k": "汽车出口总量_万辆",
    "ice_exports_10k": "其余汽车出口差额_万辆", "nev_share_of_exports_pct": "新能源出口占比_百分比",
    "statistical_scope": "充电统计口径",
    "annual_co2_avoided_100mt": "年度减碳量估算_亿吨",
    "cumulative_co2_avoided_100mt": "累计减碳量估算_亿吨",
}
NOTE_ZH = "部分数值已按来源审计核对，其余历史值待核实；证据等级见 data/source/provenance.json"
NOTE_EN = "Selected observations source-checked; other historical values unverified. Evidence: data/source/provenance.json."
STATUSES = {"compiled_from_coursework", "needs_verification", "verified_external", "assumption"}
EVIDENCE_TYPES = {"government_original", "government_republication", "secondary_media"}
CHARGING_BREAK_YEAR = 2025
CHARGING_NOTE_ZH = "2025 年 NEA 调整统计范围与报送制度（充电枪口）；与此前 EVCIPA 不可直接比较，跨断点不计算增长"
CHARGING_NOTE_EN = "2025 NEA connector scope/reporting break vs EVCIPA; differences across the break are not physical additions."
RECORD_COLUMNS = ["dataset", "field", "year", "value", "status", "source_ids"]
FIGURES = {
    "charts": [
        "01_新能源汽车销量与渗透率.png", "02_保有量与充电设施协同增长.png",
        "03_充电设施结构演变.png", "04_动力电池装车量结构.png",
        "05_技术路线结构.png", "06_新能源汽车出口.png", "07_减碳量情景估算.png", "08_综合看板.png",
    ],
    "charts_en": [
        "01_sales_and_penetration.png", "02_fleet_vs_charging.png", "03_charger_mix.png",
        "04_battery_chemistry.png", "05_powertrain_mix.png", "06_exports.png",
        "07_carbon_scenario.png", "08_dashboard.png",
    ],
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def charging_segments(frame):
    """Separate reporting regimes so charts cannot imply a continuous 2024-2025 series."""
    return (frame.loc[frame.year < CHARGING_BREAK_YEAR],
            frame.loc[frame.year >= CHARGING_BREAK_YEAR])


def plot_charging_segments(ax, frame, field, scale=1, **kwargs):
    lines = []
    for segment in charging_segments(frame):
        lines.extend(ax.plot(segment.year, segment[field] / scale, **kwargs))
        kwargs = {**kwargs, "label": "_nolegend_"}
    return lines


def validate_inputs(frames, factor):
    """Exact schemas and year coverage; reject invalid inputs before any output is written."""
    require(set(frames) == set(SCHEMAS), "Input dataset schema mismatch")
    require(np.isfinite(factor) and factor > 0, "carbon_factor must be finite and positive")
    for name, (first, last, fields) in SCHEMAS.items():
        df = frames[name]
        require(list(df.columns) == ["year", *fields], f"{name}: column schema mismatch")
        require(all(pd.api.types.is_numeric_dtype(df[c]) for c in df), f"{name}: numeric schema required")
        require(np.isfinite(df.to_numpy(dtype=float)).all(), f"{name}: null or non-finite value")
        require((df.year % 1 == 0).all(), f"{name}: year must be integer")
        require(df.year.is_unique, f"{name}: duplicate year")
        require(set(df.year) == set(range(first, last + 1)), f"{name}: missing or unexpected year")
        require((df[list(fields)] > 0).all().all(), f"{name}: values must be positive")
    for name, part, total in [
        ("sales", "nev_sales_10k", "auto_sales_10k"),
        ("fleet", "bev_fleet_10k", "nev_fleet_10k"),
        ("charging", "chargers_public_10k", "chargers_total_10k"),
        ("exports", "nev_exports_10k", "total_exports_10k"),
    ]:
        require((frames[name][part] <= frames[name][total]).all(), f"{name}: subset exceeds total")
    sales = frames["sales"]
    calculated = sales.nev_sales_10k / sales.auto_sales_10k * 100
    # The old input contains a one-decimal reported percentage, retained independently.
    require(np.allclose(calculated.round(1), sales.reported_share_pct, rtol=0, atol=1e-8),
            "sales: reported percentage disagrees with supplied numerator/denominator")


def validate_provenance(frames, factor, provenance, require_verified=False):
    """Each numeric input has exactly one value/year/field record and a resolvable source."""
    require(provenance.get("schema_version") == 1, "Unsupported provenance schema")
    require(provenance.get("record_columns") == RECORD_COLUMNS, "Provenance record schema mismatch")
    audit = provenance.get("audit", {})
    require(audit.get("path_from_project") and audit.get("reviewer") and audit.get("date"),
            "Missing supplied audit identity")
    date.fromisoformat(audit["date"])
    break_info = provenance.get("series_breaks", {}).get("charging", {})
    require(break_info.get("year") == CHARGING_BREAK_YEAR
            and "nea_break_2025" in break_info.get("source_ids", []), "Missing charging scope break")
    expected = {}
    units = {}
    for name, (_, _, fields) in SCHEMAS.items():
        for field, unit in fields.items():
            units[f"{name}.{field}"] = unit
            for row in frames[name].itertuples(index=False):
                expected[(name, field, int(row.year))] = float(getattr(row, field))
    expected[("assumptions", "carbon_factor", None)] = factor
    units["assumptions.carbon_factor"] = "t_CO2_per_vehicle_year"
    require(set(provenance.get("fields", {})) == set(units), "Provenance field coverage mismatch")
    for field, unit in units.items():
        metadata = provenance["fields"][field]
        require(metadata.get("unit") == unit and metadata.get("scope") and metadata.get("origin_symbol"),
                f"{field}: missing scope/origin or incorrect unit")
    derived_keys = {f"{key}.{column}" for key, df in derive(frames, factor).items()
                    for column in df.columns if column != "year" and f"{key}.{column}" not in units}
    require(set(provenance.get("derivations", {})) == derived_keys, "Derived provenance coverage mismatch")
    for key, lineage in provenance["derivations"].items():
        require(lineage.get("formula") and lineage.get("alignment") and lineage.get("inputs")
                and all(field in units for field in lineage["inputs"]),
                f"{key}: invalid derived lineage")
    seen = set()
    counts = Counter()
    for row in provenance.get("records", []):
        require(isinstance(row, list) and len(row) == len(RECORD_COLUMNS), "Malformed provenance record")
        dataset, field, year, value, status, source_ids = row
        require(year is None or (isinstance(year, int) and not isinstance(year, bool)),
                "Provenance year must be an integer or null")
        key = (dataset, field, year)
        require(key in expected, f"Unexpected provenance key: {key}")
        require(key not in seen, f"Duplicate provenance key: {key}")
        seen.add(key)
        require(isinstance(value, (int, float)) and not isinstance(value, bool)
                and np.isfinite(value) and value == expected[key], f"Provenance value mismatch: {key}")
        require(status in STATUSES, f"Unknown provenance status: {key}")
        require((status == "assumption") == (dataset == "assumptions"),
                f"Assumption classification mismatch: {key}")
        require(isinstance(source_ids, list) and source_ids, f"Missing source: {key}")
        sources = provenance.get("sources", {})
        require(all(sid in sources for sid in source_ids), f"Unknown source ID: {key}")
        for sid in source_ids:
            source = sources[sid]
            require(source.get("locator"), f"{sid}: source locator required")
            if source.get("kind") == "local_compilation":
                path = (ROOT / source.get("path", "")).resolve()
                require(path.is_relative_to(ROOT) and path.is_file(), f"{sid}: missing local source")
            else:
                parsed = urlparse(source.get("url", ""))
                require(parsed.scheme in {"http", "https"} and parsed.netloc
                        and parsed.path not in {"", "/"}, f"{sid}: exact document URL required")
        if status == "verified_external":
            # The supplied audit is the evidence; summaries are not fabricated verbatim quotes.
            evidence = provenance.get("verification", {}).get(f"{dataset}.{field}.{year}", {})
            sid = evidence.get("source_id")
            require(sid in source_ids and sources[sid].get("kind") == "verified_document"
                    and sources[sid].get("verified") is True
                    and sources[sid].get("evidence_type") in EVIDENCE_TYPES
                    and sources[sid].get("published_at")
                    and all(evidence.get(k) for k in ("evidence_summary", "audit_locator")),
                    f"Verified status lacks observation-specific evidence: {key}")
            date.fromisoformat(sources[sid]["published_at"])
        counts[status] += 1
    require(seen == set(expected), f"Missing provenance records: {set(expected) - seen}")
    if require_verified:
        require(counts["verified_external"] == len(expected) - counts["assumption"],
                f"External verification incomplete: {dict(counts)}")
    return dict(counts)


def load_inputs(source_dir=SOURCE, require_verified=False):
    source_dir = Path(source_dir)
    frames = {name: pd.read_csv(source_dir / f"{name}.csv") for name in SCHEMAS}
    assumptions = pd.read_csv(source_dir / "assumptions.csv")
    require(list(assumptions.columns) == ["parameter", "value", "unit"]
            and len(assumptions) == 1, "Assumptions schema mismatch")
    require(assumptions.iloc[0].parameter == "carbon_factor"
            and assumptions.iloc[0].unit == "t_CO2_per_vehicle_year", "Unknown assumption or unit")
    factor = float(assumptions.iloc[0].value)
    provenance = json.loads((source_dir / "provenance.json").read_text(encoding="utf-8"))
    validate_inputs(frames, factor)
    validate_provenance(frames, factor, provenance, require_verified)
    return {key: df.sort_values("year").reset_index(drop=True) for key, df in frames.items()}, factor, provenance


def derive(frames, factor):
    """Ratios use the supplied series; no domestic-only, passenger-only or causal assertion."""
    validate_inputs(frames, factor)
    f = {key: df.sort_values("year").reset_index(drop=True).copy() for key, df in frames.items()}
    s = f["sales"]
    s["nev_share_of_new_sales_pct"] = (s.nev_sales_10k / s.auto_sales_10k * 100).round(2)
    fleet = f["fleet"]
    fleet["bev_share_pct"] = (fleet.bev_fleet_10k / fleet.nev_fleet_10k * 100).round(2)
    c = f["charging"].merge(fleet[["year", "nev_fleet_10k"]], on="year", how="left",
                            validate="one_to_one")
    require(c.nev_fleet_10k.notna().all(), "Missing fleet year for charging alignment")
    c["chargers_private_10k"] = c.chargers_total_10k - c.chargers_public_10k
    c["public_share_pct"] = (c.chargers_public_10k / c.chargers_total_10k * 100).round(2)
    c["vehicles_per_charger"] = (c.nev_fleet_10k / c.chargers_total_10k).round(2)
    c["statistical_scope"] = np.where(c.year < CHARGING_BREAK_YEAR,
                                     "EVCIPA_2020_2024", "NEA_connectors_2025_revised")
    f["charging"] = c
    b = f["battery"]
    b["total_gwh"] = b.lfp_gwh + b.nmc_gwh
    b["lfp_share_pct"] = (b.lfp_gwh / b.total_gwh * 100).round(2)
    p = f["powertrain"]
    p["total_10k"] = p.bev_sales_10k + p.phev_sales_10k
    p["bev_share_pct"] = (p.bev_sales_10k / p.total_10k * 100).round(2)
    p["phev_share_pct"] = (p.phev_sales_10k / p.total_10k * 100).round(2)
    e = f["exports"]
    e["ice_exports_10k"] = e.total_exports_10k - e.nev_exports_10k
    e["nev_share_of_exports_pct"] = (e.nev_exports_10k / e.total_exports_10k * 100).round(2)
    carbon = fleet[["year", "nev_fleet_10k"]].copy()
    # 10,000 vehicles * t/vehicle / 100,000,000 t = 1/10,000 hundred-million t.
    carbon["annual_co2_avoided_100mt"] = carbon.nev_fleet_10k * factor / 10000
    carbon["cumulative_co2_avoided_100mt"] = carbon.annual_co2_avoided_100mt.cumsum()
    f["carbon"] = carbon
    # Keep six decimals for carbon so annual sums and cumulative outputs reconcile.
    return {key: df.round(6) for key, df in f.items()}


def validate_outputs(outputs, inputs, factor):
    """Detect stale/tampered exports, schema drift and broken formula/year alignment."""
    expected = derive(inputs, factor)
    require(set(outputs) == set(TABLES), "Derived table coverage mismatch")
    for key, reference in expected.items():
        actual = outputs[key]
        require(list(actual.columns) == list(reference.columns), f"{key}: output schema mismatch")
        require(actual.year.is_unique, f"{key}: duplicate output year")
        try:
            pd.testing.assert_frame_equal(actual.reset_index(drop=True), reference,
                                          check_dtype=False, check_exact=False, atol=1e-7, rtol=0)
        except AssertionError as exc:
            raise ValueError(f"{key}: output values/year order disagree with inputs and arithmetic") from exc


def build_tables(write=False, source_dir=SOURCE, output_dir=DATA):
    inputs, factor, provenance = load_inputs(source_dir)
    tables = derive(inputs, factor)
    validate_outputs(tables, inputs, factor)
    if write:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for key, df in tables.items():
            df.rename(columns=COLUMNS).to_csv(output_dir / TABLES[key], index=False,
                                             encoding="utf-8-sig", float_format="%.6f")
        summary = {
            "data_status": validate_provenance(inputs, factor, provenance),
            "note": NOTE_EN,
            "charging_scope_break": provenance["series_breaks"]["charging"],
            "precision_notes": provenance["precision_notes"],
            "carbon_factor_t_per_vehicle_year": factor,
            "findings_en": summary_lines(tables, factor),
        }
        (output_dir / "analysis_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return tables, factor


def summary_lines(f, factor):
    s, c, b, p, e, carbon = (f[k] for k in ("sales", "charging", "battery", "powertrain", "exports", "carbon"))
    start, end = s.iloc[0], s.iloc[-1]
    return [
        f"Compiled NEV sales, {int(start.year)}-{int(end.year)}: "
        f"{start.nev_sales_10k / 100:.3f} to {end.nev_sales_10k / 100:.3f} million; "
        f"end/start = {end.nev_sales_10k / start.nev_sales_10k:.2f}x.",
        f"Calculated share of supplied vehicle sales: {start.nev_share_of_new_sales_pct:.2f}% to "
        f"{end.nev_share_of_new_sales_pct:.2f}%; all vehicle types including exports. "
        f"2025 published share {end.reported_share_pct:.1f}% is retained separately.",
        f"2025 NEA revised-scope snapshot: fleet/connectors {c.vehicles_per_charger.iloc[-1]:.2f}; "
        f"public share {c.public_share_pct.iloc[-1]:.2f}%. " + CHARGING_NOTE_EN,
        f"LFP / (LFP + ternary), {int(b.year.iloc[-1])}: {b.lfp_share_pct.iloc[-1]:.2f}%; "
        f"two-chemistry subtotal {b.total_gwh.iloc[-1]:.1f} GWh.",
        f"PHEV / (BEV + PHEV): {p.phev_share_pct.iloc[0]:.2f}% to {p.phev_share_pct.iloc[-1]:.2f}%; "
        f"latest change {p.phev_share_pct.iloc[-1] - p.phev_share_pct.iloc[-2]:+.2f} percentage points; "
        "all vehicle types; historical values remain individually unverified.",
        f"NEV export share: approximately {e.nev_share_of_exports_pct.iloc[0]:.1f}% in 2020 to "
        f"{e.nev_share_of_exports_pct.iloc[-1]:.2f}%; latest annual volume growth "
        f"{(e.nev_exports_10k.iloc[-1] / e.nev_exports_10k.iloc[-2] - 1) * 100:.2f}%.",
        f"Illustrative year-end fleet scenario at {factor:g} t CO2/vehicle-year: "
        f"latest annual {carbon.annual_co2_avoided_100mt.iloc[-1]:.6f}, "
        f"cumulative {carbon.cumulative_co2_avoided_100mt.iloc[-1]:.6f} hundred million tonnes. "
        "Not measured emissions or a life-cycle assessment; factor is classified as an assumption.",
    ]


def validate_figures(root=ROOT):
    """Check the deliverable manifest, decodability, dimensions and 300-dpi metadata."""
    from PIL import Image

    checked = []
    for directory, names in FIGURES.items():
        path = Path(root) / directory
        require({p.name for p in path.glob("*.png")} == set(names), f"{directory}: figure manifest mismatch")
        for name in names:
            with Image.open(path / name) as image:
                require(image.format == "PNG" and min(image.size) >= 1000,
                        f"{name}: invalid format or insufficient resolution")
                require(all(abs(dpi - 300) < 1 for dpi in image.info.get("dpi", (0, 0))),
                        f"{name}: expected 300 dpi")
                image.load()
                checked.append((directory, name, image.size))
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate seven derived CSVs and JSON summary")
    parser.add_argument("--check-outputs", action="store_true", help="Check existing CSVs against the validated inputs")
    parser.add_argument("--require-verified", action="store_true", help="Require external evidence for observations; exclude explicit assumptions")
    parser.add_argument("--check-figures", action="store_true", help="Check bilingual PNG manifest, integrity and resolution")
    args = parser.parse_args()
    inputs, factor, provenance = load_inputs(require_verified=args.require_verified)
    tables, _ = build_tables(write=args.write)
    if args.check_outputs:
        require({p.name for p in DATA.glob("*.csv")} == set(TABLES.values()), "Derived CSV manifest mismatch")
        inverse = {v: k for k, v in COLUMNS.items()}
        outputs = {k: pd.read_csv(DATA / name, encoding="utf-8-sig").rename(columns=inverse)
                   for k, name in TABLES.items()}
        validate_outputs(outputs, inputs, factor)
    if args.check_figures:
        checked = validate_figures()
        print(f"PASS: {len(checked)} decodable PNGs (8 Chinese + 8 English), each at 300 dpi")
    print("PASS: input schema, unique years, source coverage and arithmetic consistency")
    print("Source status:", validate_provenance(inputs, factor, provenance))
    print(NOTE_EN)
    for line in summary_lines(tables, factor):
        print(line)


if __name__ == "__main__":
    main()
