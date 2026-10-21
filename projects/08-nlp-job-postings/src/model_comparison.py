"""Fixed-cohort TF-IDF, three-epoch CNN and frozen MiniLM comparison.

Train writes only IDs, groups, labels, predictions and aggregate metadata to
the output directory. Models, vocabularies and embeddings remain under
PROJECT/.runtime/comparison. Verify reads existing artifacts without fitting,
downloading, importing deep-learning libraries or writing expected results.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sys

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC
from threadpoolctl import threadpool_limits

from classification import PROJECT, metrics, prepare

SEED = 42
SIZES = {"train": 12000, "valid": 2000, "test": 2944}
MODEL_NAMES = {"tfidf": "fair_tfidf", "cnn": "cnn", "minilm": "minilm"}
GRID = (0.1, 1.0, 10.0)
REVISION = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
ENCODER = "sentence-transformers/all-MiniLM-L6-v2"
RUNTIME = PROJECT / ".runtime" / "comparison"
FIELDS = ("id", "group", "true", "predicted")


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def object_digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=True, allow_nan=False
    ).encode("utf-8")).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def equal(actual, expected, context):
    if actual != expected:
        raise ValueError("Mismatch: " + context)


def close(actual, expected, context):
    """Compare every metric, including all report entries and confusion cells."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError("Metric keys differ: " + context)
        for key in expected:
            close(actual[key], expected[key], context + "." + key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError("Metric dimensions differ: " + context)
        for i, (left, right) in enumerate(zip(actual, expected)):
            close(left, right, context + "." + str(i))
    elif isinstance(expected, (int, float)):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)):
            raise ValueError("Invalid numeric metric: " + context)
        if not np.isfinite(actual) or not np.isclose(actual, expected, rtol=0, atol=1e-12):
            raise ValueError("Metric value differs: " + context)
    else:
        equal(actual, expected, context)


def cohort(data_dir):
    records, labels = prepare(data_dir)
    y = np.array([row["label"] for row in records])
    selected, split_ids = {}, {}
    # Preserve jobs.csv order, matching the supplied study's subset procedure.
    for split, count in SIZES.items():
        indices = np.array([i for i, row in enumerate(records) if row["split"] == split])
        if len(indices) < count:
            raise ValueError(f"{split} requires {count} rows; found {len(indices)}")
        if len(indices) > count:
            indices = train_test_split(
                indices, train_size=count, stratify=y[indices], random_state=SEED
            )[0]
        if set(y[indices]) != set(labels):
            raise ValueError("A selected split is missing categories: " + split)
        selected[split] = indices
        split_ids[split] = [records[i]["id"] for i in indices]
    # Compact arrays in the exact published selection order.
    rows = [records[i] for split in SIZES for i in selected[split]]
    ranges, start = {}, 0
    for split, count in SIZES.items():
        ranges[split] = np.arange(start, start + count)
        start += count
    return rows, labels, ranges, split_ids


def specification(name):
    if name == "tfidf":
        return {
            "estimator": "LinearSVC", "C_grid": list(GRID), "max_iter": 5000,
            "dual": "auto", "ngram_range": [1, 2], "min_df": 3, "max_df": 0.98,
            "max_features": 100000, "sublinear_tf": True, "dtype": "float64",
            "fit_vocabulary": "selected training split only",
            "selection": "validation macro_f1; first C wins ties; no refit",
            "truncation": {"max_tokens": None, "unit": "full description"},
        }
    if name == "cnn":
        return {
            "estimator": "TextCNN", "embedding": 64, "filters": 64,
            "kernels": [3, 4, 5], "dropout": 0.3, "vocab_limit": 30000,
            "padding_id": 0, "unknown_id": 1, "epochs": 3, "batch": 64,
            "optimizer": "Adam", "lr": 0.001, "loss": "CrossEntropyLoss",
            "tokenizer": r"re.findall(r'\b\w+\b', text.casefold())",
            "fit_vocabulary": "selected training split only",
            "selection": "fixed final epoch 3; no early stopping",
            "truncation": {"max_tokens": 256, "unit": "regex word tokens"},
        }
    return {
        "estimator": "LogisticRegression", "C_grid": list(GRID), "max_iter": 500,
        "encoder": ENCODER, "revision": REVISION, "frozen": True, "batch": 32,
        "pooling": "attention-mask mean then L2 normalize",
        "selection": "validation macro_f1; first C wins ties; no refit",
        "truncation": {"max_tokens": 256, "unit": "wordpieces including special tokens"},
    }


def versions(name):
    packages = ["numpy", "scipy", "scikit-learn", "joblib", "threadpoolctl"]
    if name in ("cnn", "minilm"):
        packages.append("torch")
    if name == "minilm":
        packages.extend(["transformers", "huggingface-hub"])
    result = {}
    for package in packages:
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = "not installed"
    return result


def base_config(name, data_dir, rows, labels, splits, split_ids):
    source = Path(__file__).resolve()
    return {
        "schema": 1, "model": MODEL_NAMES[name], "seed": SEED,
        "input_sha256": {"jobs.csv": digest(Path(data_dir) / "jobs.csv")},
        "source_sha256": {
            "model_comparison.py": digest(source),
            "classification.py": digest(source.with_name("classification.py")),
            "skill_extraction.py": digest(source.with_name("skill_extraction.py")),
            "requirements.txt": digest(PROJECT / "requirements.txt"),
            "requirements-deep.txt": digest(PROJECT / "requirements-deep.txt"),
        },
        "labels": labels, "split_names": list(SIZES), "split_counts": SIZES,
        "split_ids_sha256": object_digest(split_ids),
        "split_ids_file": "fair_split_ids.json",
        "class_counts": {
            split: dict(sorted(Counter(rows[i]["label"] for i in ix).items()))
            for split, ix in splits.items()
        },
        "sampling": "jobs.csv order; stratified per split; seed 42; exact sizes",
        "input_field": "text (job description only)",
        "parameters": specification(name),
        "fairness_note": (
            "Identical selected rows and employer-isolated splits. TF-IDF reads full "
            "descriptions; CNN reads 256 regex tokens; MiniLM reads 256 wordpieces "
            "including special tokens. These are different truncation budgets."
        ),
        "runtime_root": ".runtime/comparison",
    }


def write_predictions(path, rows, indices, predicted):
    if len(predicted) != len(indices):
        raise ValueError("Prediction count mismatch")
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for i, prediction in zip(indices, predicted):
            writer.writerow({
                "id": rows[i]["id"], "group": rows[i]["group"],
                "true": rows[i]["label"], "predicted": str(prediction),
            })


def read_predictions(path, rows, indices, labels):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        equal(reader.fieldnames, list(FIELDS), "prediction columns")
        predictions = list(reader)
    equal(len(predictions), len(indices), "prediction row count")
    for prediction, i in zip(predictions, indices):
        equal(set(prediction), set(FIELDS), "prediction fields")
        for column, field in (("id", "id"), ("group", "group"), ("true", "label")):
            equal(prediction[column], rows[i][field], "prediction " + column)
        if prediction["predicted"] not in labels:
            raise ValueError("Unknown predicted category")
    return [prediction["predicted"] for prediction in predictions]


def select_linear(matrix, y, splits, labels, rows, output, logistic):
    """Own selector: classification.fit_select supports LinearSVC only.

    Retain each candidate's validation predictions so verify can independently
    recompute selection scores as well as all held-out test metrics.
    """
    validation, grid, best, best_score = {}, [], None, -1.0
    for index, value in enumerate(GRID):
        model = (
            LogisticRegression(C=value, max_iter=500, random_state=SEED)
            if logistic else
            LinearSVC(C=value, dual="auto", random_state=SEED, max_iter=5000)
        )
        model.fit(matrix[splits["train"]], y[splits["train"]])
        predicted = model.predict(matrix[splits["valid"]])
        filename = f"validation_c{index}.csv"
        write_predictions(output / filename, rows, splits["valid"], predicted)
        scores = metrics(y[splits["valid"]], predicted, labels)
        validation[filename] = scores
        grid.append({"C": value, "valid_macro_f1": scores["macro_f1"]})
        if scores["macro_f1"] > best_score:
            best, best_score = model, scores["macro_f1"]
    return (
        best.predict(matrix[splits["test"]]), best, validation,
        {"C": float(best.C), "validation_grid": grid},
    )


def train_tfidf(texts, y, splits, labels, rows, output, cache):
    import joblib

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2), min_df=3, max_df=0.98, max_features=100000,
        sublinear_tf=True, dtype=np.float64,
    )
    vectorizer.fit([texts[i] for i in splits["train"]])
    matrix = vectorizer.transform(texts)
    predicted, model, validation, selection = select_linear(
        matrix, y, splits, labels, rows, output, logistic=False,
    )
    joblib.dump({"vectorizer": vectorizer, "classifier": model}, cache / "model.joblib")
    return predicted, validation, selection, [cache / "model.joblib"]


def train_cnn(texts, y, splits, labels, rows, output, cache):
    import torch
    from torch import nn

    torch.set_num_threads(2)
    torch.manual_seed(SEED)
    rng = np.random.default_rng(SEED)
    tokenize = lambda text: re.findall(r"\b\w+\b", text.casefold())
    counts = Counter(token for i in splits["train"] for token in tokenize(texts[i]))
    vocab = {token: i + 2 for i, (token, _) in enumerate(counts.most_common(30000))}
    encoded = np.zeros((len(texts), 256), dtype=np.int64)
    for i, text in enumerate(texts):
        ids = [vocab.get(token, 1) for token in tokenize(text)[:256]]
        encoded[i, :len(ids)] = ids
    target = np.array([labels.index(label) for label in y], dtype=np.int64)

    class CNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(len(vocab) + 2, 64, padding_idx=0)
            self.convs = nn.ModuleList([nn.Conv1d(64, 64, width) for width in (3, 4, 5)])
            self.drop = nn.Dropout(0.3)
            self.fc = nn.Linear(192, len(labels))

        def forward(self, values):
            features = self.emb(values).transpose(1, 2)
            pooled = torch.cat([torch.relu(conv(features)).amax(2) for conv in self.convs], 1)
            return self.fc(self.drop(pooled))

    model = CNN()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    loss_function = nn.CrossEntropyLoss()

    def predict(indices):
        model.eval()
        with torch.inference_mode():
            indices_out = np.concatenate([
                model(torch.from_numpy(encoded[indices[j:j + 64]])).argmax(1).numpy()
                for j in range(0, len(indices), 64)
            ])
        return np.array(labels)[indices_out]

    validation, history = {}, []
    for epoch in range(1, 4):
        model.train()
        order = rng.permutation(splits["train"])
        for j in range(0, len(order), 64):
            batch = order[j:j + 64]
            optimizer.zero_grad()
            loss = loss_function(
                model(torch.from_numpy(encoded[batch])), torch.from_numpy(target[batch])
            )
            loss.backward()
            optimizer.step()
        predicted = predict(splits["valid"])
        filename = f"validation_epoch{epoch}.csv"
        write_predictions(output / filename, rows, splits["valid"], predicted)
        validation[filename] = metrics(y[splits["valid"]], predicted, labels)
        history.append({"epoch": epoch, "valid_macro_f1": validation[filename]["macro_f1"]})
        print(f"CNN epoch {epoch}/3 completed", flush=True)
    torch.save(model.state_dict(), cache / "weights.pt")
    save(cache / "vocab.json", vocab)
    return (
        predict(splits["test"]), validation, {"selected_epoch": 3, "history": history},
        [cache / "weights.pt", cache / "vocab.json"],
    )


def train_minilm(texts, y, splits, labels, rows, output, cache):
    # Set every HF cache location before importing either deep-learning package.
    hf_cache = RUNTIME / "huggingface"
    os.environ["HF_HOME"] = str(hf_cache)
    os.environ["HF_HUB_CACHE"] = str(hf_cache / "hub")
    os.environ["TRANSFORMERS_CACHE"] = str(hf_cache / "hub")
    os.environ["HF_XET_CACHE"] = str(hf_cache / "xet")
    import joblib
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModel, AutoTokenizer

    torch.set_num_threads(2)
    torch.manual_seed(SEED)
    embedding_path = cache / "embeddings.npy"
    metadata_path = cache / "embeddings.json"
    identity = {
        "ids": [row["id"] for row in rows], "encoder": ENCODER, "revision": REVISION,
        "max_tokens": 256, "pooling": "attention-mask mean then L2 normalize",
    }
    if embedding_path.is_file() and metadata_path.is_file():
        metadata = load(metadata_path)
        equal(metadata["identity"], identity, "embedding cache identity")
        equal(digest(embedding_path), metadata["sha256"], "embedding cache hash")
        matrix = np.load(embedding_path, allow_pickle=False)
    else:
        snapshot = snapshot_download(
            ENCODER, revision=REVISION, cache_dir=str(hf_cache / "hub"),
            allow_patterns=[
                "config.json", "model.safetensors", "tokenizer.json",
                "tokenizer_config.json", "special_tokens_map.json", "vocab.txt",
            ],
        )
        tokenizer = AutoTokenizer.from_pretrained(
            snapshot, local_files_only=True, trust_remote_code=False,
        )
        model = AutoModel.from_pretrained(
            snapshot, local_files_only=True, trust_remote_code=False,
        ).cpu().eval()
        model.requires_grad_(False)
        matrix = np.zeros((len(texts), 384), dtype=np.float32)
        with torch.inference_mode():
            for j in range(0, len(texts), 32):
                tokens = tokenizer(
                    texts[j:j + 32], padding=True, truncation=True,
                    max_length=256, return_tensors="pt",
                )
                hidden = model(**tokens).last_hidden_state
                mask = tokens["attention_mask"].unsqueeze(-1)
                pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1)
                matrix[j:j + 32] = torch.nn.functional.normalize(pooled, p=2, dim=1).numpy()
                if j % 1024 == 0:
                    print(f"MiniLM encoded {min(j + 32, len(texts))}/{len(texts)}", flush=True)
        np.save(embedding_path, matrix, allow_pickle=False)
        save(metadata_path, {"identity": identity, "sha256": digest(embedding_path)})
    equal(list(matrix.shape), [len(texts), 384], "embedding dimensions")
    if matrix.dtype != np.float32 or not np.isfinite(matrix).all():
        raise ValueError("Invalid cached embeddings")
    predicted, classifier, validation, selection = select_linear(
        matrix, y, splits, labels, rows, output, logistic=True,
    )
    joblib.dump(classifier, cache / "classifier.joblib")
    return predicted, validation, selection, [
        embedding_path, metadata_path, cache / "classifier.joblib",
    ]


def validation_files(name):
    if name == "cnn":
        return [f"validation_epoch{epoch}.csv" for epoch in range(1, 4)]
    return [f"validation_c{index}.csv" for index in range(len(GRID))]


def train(data_dir, output_dir, models):
    rows, labels, splits, split_ids = cohort(data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ids_path = output_dir / "fair_split_ids.json"
    if ids_path.exists():
        equal(load(ids_path), split_ids, "existing fixed selection IDs")
    else:
        save(ids_path, split_ids)
    texts = [row["text"] for row in rows]
    y = np.array([row["label"] for row in rows])
    results = {}
    trainers = {"tfidf": train_tfidf, "cnn": train_cnn, "minilm": train_minilm}
    for name in models:
        output = output_dir / MODEL_NAMES[name]
        output.mkdir(parents=True, exist_ok=True)
        base = base_config(name, data_dir, rows, labels, splits, split_ids)
        installed = versions(name)
        cache_key = object_digest({"base": base, "versions": installed})
        cache = RUNTIME / MODEL_NAMES[name] / cache_key
        cache.mkdir(parents=True, exist_ok=True)
        config = {
            **base, "versions": installed, "device": "cpu", "threads": 2,
            "status": "running", "cache_key": cache_key,
            "split_ids_file_sha256": digest(ids_path),
        }
        save(output / "run_config.json", config)
        try:
            print(f"Training {MODEL_NAMES[name]}", flush=True)
            with threadpool_limits(limits=2):
                predicted, validation, selection, artifacts = trainers[name](
                    texts, y, splits, labels, rows, output, cache,
                )
            write_predictions(output / "predictions.csv", rows, splits["test"], predicted)
            save(output / "metrics.json", {
                "test": metrics(y[splits["test"]], predicted, labels),
                "validation": validation,
            })
            files = ["predictions.csv", "metrics.json"] + validation_files(name)
            config.update(
                status="completed", selection=selection,
                output_sha256={filename: digest(output / filename) for filename in files},
                private_artifact_sha256={
                    path.relative_to(RUNTIME).as_posix(): digest(path) for path in artifacts
                },
            )
            config["run_config_sha256"] = object_digest(config)
            save(output / "run_config.json", config)
            results[MODEL_NAMES[name]] = {"status": "completed"}
        except Exception as error:
            # Invalidate previous success before returning; no raw-text error dump.
            config.pop("run_config_sha256", None)
            config.update(status="failed", error_type=type(error).__name__)
            save(output / "run_config.json", config)
            results[MODEL_NAMES[name]] = {
                "status": "failed", "error_type": type(error).__name__,
            }
            print(f"{MODEL_NAMES[name]} failed: {type(error).__name__}", file=sys.stderr)
    completed = all(result["status"] == "completed" for result in results.values())
    return {
        "status": "completed" if completed else "incomplete", "models": results,
        "split_counts": SIZES, "verification": "not run",
    }


def verify_model(name, data_dir, output_dir, rows, labels, splits, split_ids):
    output = output_dir / MODEL_NAMES[name]
    config = load(output / "run_config.json")
    equal(config.get("status"), "completed", "completed training status")
    signed = dict(config)
    stored_hash = signed.pop("run_config_sha256")
    equal(object_digest(signed), stored_hash, "run configuration hash")
    base = base_config(name, data_dir, rows, labels, splits, split_ids)
    for key, value in base.items():
        equal(config[key], value, "configuration " + key)
    equal(config["device"], "cpu", "device")
    equal(config["threads"], 2, "threads")
    equal(config["cache_key"], object_digest({
        "base": base, "versions": config["versions"],
    }), "cache key")
    equal(digest(output_dir / "fair_split_ids.json"),
          config["split_ids_file_sha256"], "selection file hash")
    files = ["predictions.csv", "metrics.json"] + validation_files(name)
    equal(set(config["output_sha256"]), set(files), "output manifest")
    for filename in files:
        equal(digest(output / filename), config["output_sha256"][filename], filename)
    stored = load(output / "metrics.json")
    equal(set(stored), {"test", "validation"}, "metric sections")
    equal(set(stored["validation"]), set(validation_files(name)), "validation metric files")
    test = read_predictions(output / "predictions.csv", rows, splits["test"], labels)
    truth = [rows[i]["label"] for i in splits["test"]]
    close(stored["test"], metrics(truth, test, labels), "test")
    scores = []
    for filename in validation_files(name):
        predicted = read_predictions(output / filename, rows, splits["valid"], labels)
        actual = metrics([rows[i]["label"] for i in splits["valid"]], predicted, labels)
        close(stored["validation"][filename], actual, filename)
        scores.append(actual["macro_f1"])
    if name == "cnn":
        expected_selection = {
            "selected_epoch": 3,
            "history": [{"epoch": i + 1, "valid_macro_f1": score}
                        for i, score in enumerate(scores)],
        }
    else:
        expected_selection = {
            "C": GRID[int(np.argmax(scores))],
            "validation_grid": [
                {"C": value, "valid_macro_f1": score} for value, score in zip(GRID, scores)
            ],
        }
    close(config["selection"], expected_selection, "model selection")
    return {
        "status": "passed", "test_predictions": len(test),
        "validation_predictions": len(splits["valid"]) * len(scores),
        "macro_f1": stored["test"]["macro_f1"], "accuracy": stored["test"]["accuracy"],
    }


def verify(data_dir, output_dir, models):
    # Deliberately read-only: no training fallback, mkdir, save or deep imports.
    rows, labels, splits, split_ids = cohort(data_dir)
    equal(load(output_dir / "fair_split_ids.json"), split_ids, "fixed selection IDs")
    results = {}
    for name in models:
        try:
            results[MODEL_NAMES[name]] = verify_model(
                name, data_dir, output_dir, rows, labels, splits, split_ids,
            )
        except (OSError, ValueError, KeyError, TypeError) as error:
            results[MODEL_NAMES[name]] = {
                "status": "failed", "error_type": type(error).__name__,
                "reason": "Missing, incomplete, changed or inconsistent artifacts",
            }
    passed = all(result["status"] == "passed" for result in results.values())
    return {
        "status": "passed" if passed else "failed", "models": results,
        "split_counts": SIZES, "split_names": list(SIZES), "labels": labels,
        "split_ids_sha256": object_digest(split_ids),
        "truncation": {MODEL_NAMES[name]: specification(name)["truncation"] for name in models},
        "scope": (
            "Recomputed every test/validation metric and selection score from CSV "
            "against deterministic IDs and source labels; checked input, source, "
            "configuration and public artifact hashes. Private model hashes are "
            "recorded provenance only; model inference and training are not replayed."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=PROJECT / "data/full",
                        help="Directory containing jobs.csv (default: data/full)")
    parser.add_argument("--output-dir", type=Path, default=PROJECT / "results/comparison",
                        help="Public metadata directory (default: results/comparison)")
    parser.add_argument("--models", nargs="+", choices=tuple(MODEL_NAMES),
                        default=list(MODEL_NAMES), help="Models to train or verify")
    parser.add_argument("--stage", choices=("train", "verify"), default="train",
                        help="Train selected models or independently verify existing CSV outputs")
    args = parser.parse_args()
    models = list(dict.fromkeys(args.models))
    try:
        action = train if args.stage == "train" else verify
        report = action(args.data_dir.resolve(), args.output_dir.resolve(), models)
    except (OSError, ValueError, KeyError, TypeError) as error:
        report = {
            "status": "failed", "error_type": type(error).__name__,
            "reason": "Input data, fixed selection or required artifacts are invalid or missing",
        }
    print(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False))
    return 0 if report["status"] in ("completed", "passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
