"""Independent, course-inspired temporal evaluation; see report.html for attribution."""
from pathlib import Path
import hashlib
import io
import json
import platform
import urllib.request
import zipfile

import numpy as np
import pandas as pd
import sklearn
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

ROOT = Path(__file__).resolve().parent
URL = "https://archive.ics.uci.edu/static/public/247/istanbul+stock+exchange.zip"
SEED = 20261029
SOURCE_SHA256 = "a30838316290a83a98a52a46c30174e0204c963c0877627954ebc74111668922"
LOCAL = ["return", "mean5", "std5", "mean20", "std20"]
FOREIGN = ["SP", "DAX", "FTSE", "NIKKEI", "BOVESPA", "EU", "EM"]


def load_data():
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    archive = cache / "uci247.zip"
    if not archive.exists():
        with urllib.request.urlopen(URL, timeout=60) as response:
            archive.write_bytes(response.read())
    blob = archive.read_bytes()
    if hashlib.sha256(blob).hexdigest() != SOURCE_SHA256:
        raise ValueError("Source archive changed; investigate provenance before proceeding.")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        member = next(n for n in z.namelist() if n.endswith(".xlsx"))
        raw = pd.read_excel(io.BytesIO(z.read(member)), header=1)
    print("Source columns:", list(raw.columns), "shape:", raw.shape, flush=True)
    assert list(raw.columns) == ["date", "ISE", "ISE.1", *FOREIGN], "Source schema changed"
    raw.columns = ["date", "ISE", "ISE_USD", *FOREIGN]
    raw["date"] = pd.to_datetime(raw["date"], errors="raise")
    raw = raw.set_index("date")
    assert raw.index.is_monotonic_increasing and raw.index.is_unique
    assert np.isfinite(raw.to_numpy()).all()
    return raw, hashlib.sha256(blob).hexdigest()


def features(raw):
    """Forecast after Istanbul close t; foreign inputs deliberately lagged one row."""
    r = raw.ISE
    x = pd.DataFrame({"return": r, "mean5": r.rolling(5).mean(),
                      "std5": r.rolling(5).std(), "mean20": r.rolling(20).mean(),
                      "std20": r.rolling(20).std()}, index=raw.index)
    for name in FOREIGN:
        x[name] = raw[name].shift(1)
    x["target_date"] = pd.Series(raw.index, index=raw.index).shift(-1)
    x["next_return"] = r.shift(-1)
    x = x.dropna()
    x["y"] = (x.next_return > 0).astype(int)
    return x


def model(name):
    if name.startswith("lr"):
        c = float(name.split("_")[1])
        return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=2000))
    if name == "pca":
        return make_pipeline(StandardScaler(), PCA(n_components=2),
                             LogisticRegression(C=0.1, max_iter=2000))
    if name == "tree":
        return DecisionTreeClassifier(max_depth=3, min_samples_leaf=20, random_state=SEED)
    return RandomForestClassifier(n_estimators=200, max_depth=int(name.split("_")[1]),
                                  min_samples_leaf=20, random_state=SEED, n_jobs=1)


def predict(name, train, test, cols):
    if name == "prior":
        return np.full(len(test), train.y.mean())
    if name == "half":
        return np.full(len(test), 0.5)
    fit = model(name).fit(train[cols], train.y)
    return fit.predict_proba(test[cols])[:, 1]


def scores(y, p):
    return {"brier": brier_score_loss(y, p), "log_loss": log_loss(y, p, labels=[0, 1]),
            "accuracy": accuracy_score(y, p >= .5),
            "auc": roc_auc_score(y, p) if len(np.unique(y)) == 2 else None}


def block_interval(delta, block=10, draws=4000):
    """Paired circular moving-block bootstrap of fixed out-of-sample losses."""
    rng = np.random.default_rng(SEED)
    n = len(delta)
    starts = rng.integers(0, n, size=(draws, int(np.ceil(n / block))))
    indices = ((starts[..., None] + np.arange(block)) % n).reshape(draws, -1)[:, :n]
    return np.quantile(np.asarray(delta)[indices].mean(axis=1), [.025, .975]).tolist()


def run():
    raw, sha = load_data()
    s = features(raw)
    # Protocol fixed before the first experiment: first 300 usable rows develop;
    # three forward validation windows, then consecutive 50-row outer test blocks.
    candidates = ["prior", "lr_0.1", "lr_1.0", "tree", "rf_2", "rf_4"]
    tuning = []
    for name in candidates:
        for start in (150, 200, 250):
            tr, va = s.iloc[:start-1], s.iloc[start:start+50]
            assert tr.target_date.max() < va.index.min()
            tuning.append({"model": name, "start": start,
                           **scores(va.y, predict(name, tr, va, LOCAL))})
    tune = pd.DataFrame(tuning)
    winner = tune.groupby("model").brier.mean().sort_values(kind="stable").index[0]
    print("Development-selected:", winner, flush=True)
    rows, splits = [], []
    specs = {"selected": (winner, LOCAL, None), "prior": ("prior", LOCAL, None),
             "half": ("half", LOCAL, None), "local_lr": ("lr_0.1", LOCAL, None),
             "return_only": ("lr_0.1", ["return"], None),
             "lagged_global_lr": ("lr_0.1", LOCAL + FOREIGN, None),
             "pca_lr": ("pca", LOCAL, None),
             "rolling252": (winner, LOCAL, 252)}
    for fold, start in enumerate(range(300, len(s), 50)):
        tr, te = s.iloc[:start-1], s.iloc[start:start+50]
        assert tr.target_date.max() < te.index.min()
        splits.append({"fold": fold, "train_n": len(tr), "test_n": len(te),
                       "train_last_target": str(tr.target_date.max().date()),
                       "test_first_origin": str(te.index.min().date()),
                       "test_last_target": str(te.target_date.max().date())})
        for label, (name, cols, window) in specs.items():
            training = tr if window is None else tr.iloc[-window:]
            probabilities = predict(name, training, te, cols)
            for date, target, y, p in zip(te.index, te.target_date, te.y, probabilities):
                rows.append({"fold": fold, "origin": date.date().isoformat(),
                             "target_date": target.date().isoformat(), "model": label,
                             "y": int(y), "probability": float(p)})
        print("Outer fold", fold, "train", len(tr), "test", len(te), flush=True)
    pred = pd.DataFrame(rows)
    metrics = pd.DataFrame([{"model": name, **scores(g.y, g.probability)}
                           for name, g in pred.groupby("model")])
    fold_metrics = pd.DataFrame([{"fold": f, "model": name, **scores(g.y, g.probability)}
                                for (f, name), g in pred.groupby(["fold", "model"])])
    wide = pred.pivot(index="origin", columns="model", values="probability")
    y = pred[pred.model == "prior"].set_index("origin").y.reindex(wide.index)
    intervals = []
    for name in wide:
        delta = (wide[name] - y)**2 - (wide.prior - y)**2
        for block in (5, 10, 20):
            lo, hi = block_interval(delta.to_numpy(), block)
            intervals.append({"model": name, "block": block, "delta_brier": delta.mean(),
                              "low": lo, "high": hi})
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    for filename, frame in {"development": tune, "predictions": pred, "metrics": metrics,
                            "fold_metrics": fold_metrics, "intervals": pd.DataFrame(intervals),
                            "splits": pd.DataFrame(splits)}.items():
        frame.to_csv(out / f"{filename}.csv", index=False, float_format="%.12g")
    metadata = {"source_url": URL, "source_sha256": sha, "source_rows": len(raw),
                "source_first": str(raw.index.min().date()), "source_last": str(raw.index.max().date()),
                "usable_rows": len(s), "development_rows": 300, "test_rows": len(wide),
                "selected": winner, "seed": SEED, "bootstrap_draws": 4000,
                "python": platform.python_version(), "numpy": np.__version__,
                "pandas": pd.__version__, "sklearn": sklearn.__version__,
                "license": "CC BY 4.0", "doi": "10.24432/C54P4J"}
    (out / "manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(metrics.to_string(index=False), flush=True)
    print(pd.DataFrame(intervals).query("model == 'selected'").to_string(index=False))
    from render import render
    render()


if __name__ == "__main__":
    run()
