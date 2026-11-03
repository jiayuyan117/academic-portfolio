"""Session-level funnel analysis of the simulated cart event log.

Reads the Java simulator's outputs in ../data, writes figures and findings.json
to ../results. Every estimate is compared with the simulation's known truth.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
BOOT = 2000
REP_BOOT = 1000
STAGES = ["added", "checkout", "ordered"]


def load() -> dict:
    """Load simulator outputs; types are fixed so reruns are byte-stable."""
    params = json.loads((DATA / "params.json").read_text(encoding="utf-8"))
    raw = pd.read_csv(DATA / "raw_attempts.csv", dtype={"sku": str, "idempotency_key": str}, keep_default_na=False)
    acc = pd.read_csv(DATA / "accepted_events.csv", dtype={"sku": str, "idempotency_key": str}, keep_default_na=False)
    rej = pd.read_csv(DATA / "rejected_events.csv", dtype={"sku": str, "idempotency_key": str}, keep_default_na=False)
    truth = pd.read_csv(DATA / "truth_sessions.csv").set_index("session_id")
    reps = pd.read_csv(DATA / "replicate_sessions.csv")
    return {"params": params, "raw": raw, "acc": acc, "rej": rej, "truth": truth, "reps": reps}


def session_flags(acc: pd.DataFrame, sessions: pd.Index) -> pd.DataFrame:
    """One row per session: did the accepted log reach each funnel stage?"""
    kinds = {"added": "ADD", "checkout": "CHECKOUT", "ordered": "ORDER"}
    out = pd.DataFrame(index=sessions)
    for col, kind in kinds.items():
        hit = set(acc.loc[acc["type"] == kind, "session_id"])
        out[col] = sessions.isin(hit).astype(int)
    return out


def bootstrap_rates(flags: np.ndarray, rng: np.random.Generator, draws: int) -> np.ndarray:
    """Resample whole sessions; returns draws x stages matrix of stage shares."""
    n = flags.shape[0]
    idx = rng.integers(0, n, size=(draws, n))
    return flags[idx].mean(axis=1)


def interval(samples: np.ndarray) -> list[float]:
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return [round(float(lo), 6), round(float(hi), 6)]


def timestamp_audit(acc: pd.DataFrame) -> dict:
    """Compare server sequence order with client-timestamp order inside each session."""
    reordered = 0
    invalid = 0
    rank = {"VIEW": 0, "ADD": 1, "REMOVE": 1, "CHECKOUT": 2, "ORDER": 3}
    for _, g in acc.groupby("session_id", sort=False):
        by_seq = g.sort_values("seq")
        by_ts = g.sort_values(["client_ts", "seq"], kind="stable")
        if list(by_seq["seq"]) != list(by_ts["seq"]):
            reordered += 1
            stages = [rank[t] for t in by_ts["type"] if t != "VIEW"]
            if any(b < a for a, b in zip(stages, stages[1:])):
                invalid += 1
    return {"sessions_reordered_by_client_ts": reordered, "sessions_with_impossible_funnel_order": invalid}


def coverage(reps: pd.DataFrame, truth_rate: float, rng: np.random.Generator) -> dict:
    """Interval coverage of the true purchase rate across independent replicates."""
    rows = []
    for rep, g in reps.groupby("replicate"):
        ordered = g["ordered"].to_numpy(dtype=float)
        attempts = g["raw_order_attempts"].to_numpy(dtype=float)
        idx = rng.integers(0, len(g), size=(REP_BOOT, len(g)))
        s_lo, s_hi = np.percentile(ordered[idx].mean(axis=1), [2.5, 97.5])
        e_lo, e_hi = np.percentile(attempts[idx].mean(axis=1), [2.5, 97.5])
        rows.append((rep, ordered.mean(), s_lo, s_hi, attempts.mean(), e_lo, e_hi))
    df = pd.DataFrame(rows, columns=["rep", "s_est", "s_lo", "s_hi", "e_est", "e_lo", "e_hi"])
    df["s_cover"] = (df.s_lo <= truth_rate) & (truth_rate <= df.s_hi)
    df["e_cover"] = (df.e_lo <= truth_rate) & (truth_rate <= df.e_hi)
    return {"frame": df,
            "session_coverage": round(float(df.s_cover.mean()), 4),
            "event_count_coverage": round(float(df.e_cover.mean()), 4),
            "mean_event_count_bias_pp": round(float((df.e_est - truth_rate).mean() * 100), 3)}


def plot_funnel(path: Path, est: dict, ci: dict, truth: dict, naive: float) -> None:
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=150)
    x = np.arange(len(STAGES))
    vals = [est[s] for s in STAGES]
    err = np.array([[est[s] - ci[s][0], ci[s][1] - est[s]] for s in STAGES]).T
    ax.bar(x, vals, color="#146964", width=0.55, label="Accepted log, per session (95% bootstrap CI)")
    ax.errorbar(x, vals, yerr=err, fmt="none", ecolor="#14252c", capsize=6, lw=1.4)
    ax.scatter(x, [truth[s] for s in STAGES], marker="D", color="#9c6724", zorder=3, s=46,
               label="Simulation parameter (population rate)")
    ax.scatter([2], [naive], marker="X", color="#b23a3a", zorder=3, s=80,
               label="Raw ORDER attempts / sessions (event count)")
    ax.set_xticks(x, ["Added to cart", "Started checkout", "Placed order"])
    ax.set_ylabel("Share of sessions")
    ax.set_title("Counting events instead of sessions overstates purchase conversion")
    ax.set_ylim(0, max(vals + [naive]) * 1.25)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.01, 0.01, "Synthetic sessions from a seeded simulator; not real customer data.", fontsize=7.5, color="#586c74")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_coverage(path: Path, df: pd.DataFrame, truth_rate: float, cov: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), dpi=150, sharey=True)
    for ax, (pre, label, rate) in zip(axes, [("s", "Accepted log, per session", cov["session_coverage"]),
                                             ("e", "Raw ORDER attempts, per session", cov["event_count_coverage"])]):
        d = df.sort_values(f"{pre}_est").reset_index(drop=True)
        miss = ~d[f"{pre}_cover"]
        for ok, colour in [(False, "#146964"), (True, "#b23a3a")]:
            sel = d[miss == ok]
            ax.hlines(sel.index, sel[f"{pre}_lo"], sel[f"{pre}_hi"], color=colour, lw=1)
        ax.axvline(truth_rate, color="#9c6724", lw=1.6, ls="--")
        ax.set_title(f"{label}\n95% interval covers true rate in {rate:.1%} of replicates", fontsize=10)
        ax.set_xlabel("Estimated purchase conversion")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Replicate (sorted by estimate)")
    fig.suptitle(f"{len(df)} independent replicates of 1,000 sessions; dashed line = true rate {truth_rate:.4f}", fontsize=11)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_quality(path: Path, reasons: dict, audit: dict, n_sessions: int) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), dpi=150, gridspec_kw={"width_ratios": [1.4, 1]})
    names = sorted(reasons, key=reasons.get)
    axes[0].barh(names, [reasons[k] for k in names], color="#146964")
    for i, k in enumerate(names):
        axes[0].text(reasons[k], i, f" {reasons[k]}", va="center", fontsize=8.5)
    axes[0].set_title("Client attempts rejected by the server log", fontsize=10)
    axes[0].set_xlabel("Attempts")
    vals = [audit["sessions_reordered_by_client_ts"], audit["sessions_with_impossible_funnel_order"]]
    axes[1].bar(["Order changes\nif sorted by client time", "Sorted order is\nimpossible (e.g. ORDER\nbefore ADD)"],
                vals, color=["#9c6724", "#b23a3a"], width=0.55)
    for i, v in enumerate(vals):
        axes[1].text(i, v, f"{v}", ha="center", va="bottom", fontsize=9)
    axes[1].set_title(f"Accepted sessions affected by clock skew (of {n_sessions:,})", fontsize=10)
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> dict:
    RESULTS.mkdir(exist_ok=True)
    d = load()
    p = d["params"]
    rng = np.random.default_rng(p["seed"])
    sessions = d["truth"].index
    flags = session_flags(d["acc"], sessions)
    truth_flags = d["truth"][STAGES]
    mismatched = int((flags[STAGES] != truth_flags).any(axis=1).sum())

    pop = {"added": p["p_add"], "checkout": p["p_add"] * p["p_checkout_given_add"]}
    pop["ordered"] = pop["checkout"] * p["p_order_given_checkout"]
    est = {s: round(float(flags[s].mean()), 6) for s in STAGES}
    boot = bootstrap_rates(flags[STAGES].to_numpy(dtype=float), rng, BOOT)
    ci = {s: interval(boot[:, i]) for i, s in enumerate(STAGES)}
    raw_orders = int((d["raw"]["type"] == "ORDER").sum())
    naive = round(raw_orders / len(sessions), 6)
    step = {"checkout_given_added": round(est["checkout"] / est["added"], 6),
            "ordered_given_checkout": round(est["ordered"] / est["checkout"], 6)}

    reasons = {k: int(v) for k, v in d["rej"]["reason"].value_counts().sort_index().items()}
    audit = timestamp_audit(d["acc"])
    cov = coverage(d["reps"], pop["ordered"], rng)

    plot_funnel(RESULTS / "01_funnel_recovery.png", est, ci, pop, naive)
    plot_coverage(RESULTS / "02_interval_coverage.png", cov["frame"], pop["ordered"], cov)
    plot_quality(RESULTS / "03_log_quality_audit.png", reasons, audit, len(sessions))

    findings = {
        "sessions": len(sessions),
        "raw_attempts": len(d["raw"]),
        "accepted_events": len(d["acc"]),
        "rejected_attempts": len(d["rej"]),
        "sessions_where_accepted_log_differs_from_truth": mismatched,
        "population_rates": {k: round(v, 6) for k, v in pop.items()},
        "session_rates": est,
        "session_rates_ci95": ci,
        "step_conversion": step,
        "raw_order_attempts": raw_orders,
        "event_count_purchase_rate": naive,
        "event_count_overstatement_pp": round((naive - est["ordered"]) * 100, 3),
        "rejections_by_reason": reasons,
        "timestamp_audit": audit,
        "replicates": int(d["reps"]["replicate"].nunique()),
        "session_interval_coverage": cov["session_coverage"],
        "event_count_interval_coverage": cov["event_count_coverage"],
        "mean_event_count_bias_pp": cov["mean_event_count_bias_pp"],
    }
    (RESULTS / "findings.json").write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")
    return findings


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
