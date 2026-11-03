"""Paired job-cluster intervals for the two independent BIO channels."""
import argparse
from pathlib import Path
import numpy as np
from skill_extraction import CHANNELS, METHODS, OUT, load, save, require_equal, validate_spans


def paired_interval(first, second, replicates=1000, seed=2026):
    if len(first) != len(second) or not first or replicates < 1:
        raise ValueError("Invalid paired prediction count or bootstrap repetitions")
    for left, right in zip(first, second):
        for key in ("sentence_id", "source", "job_idx", "channel", "tokens_sha256", "token_count", "gold"):
            require_equal(left[key], right[key], "paired." + key)
    arrays, keys = [], None
    for rows in (first, second):
        counts = {}
        for row in rows:
            key = (row["source"], row["job_idx"])
            gold = validate_spans(row["gold"], row["token_count"])
            predicted = validate_spans(row["prediction"], row["token_count"])
            counts.setdefault(key, np.zeros(3, dtype=np.int64))
            counts[key] += (len(gold & predicted), len(predicted - gold), len(gold - predicted))
        current = sorted(counts)
        if keys is not None:
            require_equal(current, keys, "job clusters")
        keys = current
        arrays.append(np.asarray([counts[key] for key in keys]))
    arrays = np.asarray(arrays)
    def f1(counts):
        return 2 * counts[..., 0] / np.maximum(1, 2 * counts[..., 0] + counts[..., 1] + counts[..., 2])
    observed = float(f1(arrays[1].sum(0)) - f1(arrays[0].sum(0)))
    rng, draws = np.random.default_rng(seed), []
    for _ in range(replicates):
        weights = np.bincount(rng.integers(0, len(keys), len(keys)), minlength=len(keys))
        sampled = np.einsum("mgc,g->mc", arrays, weights)
        draws.append(float(f1(sampled[1]) - f1(sampled[0])))
    return {
        "delta_f1_context_minus_lexicon": observed,
        "ci95": np.quantile(draws, [0.025, 0.975]).tolist(),
        "job_clusters": len(keys), "replicates": replicates, "seed": seed,
        "method": "Paired test job-cluster percentile bootstrap; no multiplicity correction",
    }


def calculate(output_dir=OUT, replicates=1000):
    output_dir = Path(output_dir)
    return {
        channel: paired_interval(*(load(output_dir / f"test_{channel}_{method}.json") for method in METHODS),
                                 replicates=replicates)
        for channel in CHANNELS
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUT)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    result = calculate(args.output_dir, args.bootstrap)
    target = args.output_dir / "paired_intervals.json"
    if args.verify:
        require_equal(result, load(target), "extraction intervals")
        print("Extraction paired intervals verified")
    else:
        save(target, result)
        print(result)
