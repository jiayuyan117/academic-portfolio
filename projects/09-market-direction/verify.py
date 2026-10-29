"""Independently recompute saved evidence, then compare a complete fresh rerun."""
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
from run import ROOT, SOURCE_SHA256, block_interval, scores


def verify():
    out = ROOT / "results"
    frames = {p.stem: pd.read_csv(p) for p in sorted(out.glob("*.csv"))}
    meta = json.loads((out / "manifest.json").read_text())
    assert meta["source_sha256"] == SOURCE_SHA256
    predictions = frames["predictions"]
    assert not predictions.duplicated(["origin", "model"]).any()
    assert predictions.probability.between(0, 1).all()
    assert (pd.to_datetime(predictions.target_date) > pd.to_datetime(predictions.origin)).all()
    reference_dates = predictions[predictions.model == "prior"].origin.tolist()
    for name, g in predictions.groupby("model"):
        assert g.origin.tolist() == reference_dates
        expected = frames["metrics"].set_index("model").loc[name]
        for key, value in scores(g.y, g.probability).items():
            np.testing.assert_allclose(value, expected[key], rtol=1e-9, atol=1e-11)
    for (fold, name), g in predictions.groupby(["fold", "model"]):
        expected = frames["fold_metrics"].set_index(["fold", "model"]).loc[(fold, name)]
        for key, value in scores(g.y, g.probability).items():
            np.testing.assert_allclose(value, expected[key], rtol=1e-9, atol=1e-11)
        if name == "prior":
            assert g.probability.nunique() == 1
    wide = predictions.pivot(index="origin", columns="model", values="probability")
    y = predictions[predictions.model == "prior"].set_index("origin").y.reindex(wide.index)
    for row in frames["intervals"].itertuples():
        delta = (wide[row.model] - y)**2 - (wide.prior - y)**2
        np.testing.assert_allclose(delta.mean(), row.delta_brier, atol=1e-11)
        np.testing.assert_allclose(block_interval(delta.to_numpy(), row.block),
                                   [row.low, row.high], atol=1e-11)
    splits = frames["splits"]
    assert (pd.to_datetime(splits.train_last_target) < pd.to_datetime(splits.test_first_origin)).all()
    assert splits.test_n.sum() == len(reference_dates) == meta["test_rows"]
    selected = frames["development"].groupby("model").brier.mean().idxmin()
    assert selected == meta["selected"]
    assert selected != "prior" or np.allclose(wide.selected, wide.prior, rtol=0, atol=0)
    print("Saved metrics, fold metrics, all 24 intervals, dates and selection verified.", flush=True)
    subprocess.run([sys.executable, str(ROOT / "run.py")], cwd=ROOT, check=True)
    for name, expected in frames.items():
        actual = pd.read_csv(out / f"{name}.csv")
        pd.testing.assert_frame_equal(actual, expected, check_exact=False, rtol=1e-8, atol=1e-10)
    print("PASS: fresh full rerun matches all six committed CSV tables.", flush=True)


if __name__ == "__main__":
    verify()
