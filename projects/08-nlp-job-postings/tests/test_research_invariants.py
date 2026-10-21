"""Regression checks for leakage, exact spans and falsifiable result verification."""
import copy
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
from classification import bootstrap, trie_pattern, metrics
from analyze_skills import paired_interval
from model_comparison import read_predictions, close
from skill_extraction import (
    spans, lexical, build_lexicon, filter_training_overlap,
    require_equal, validate_spans, validate_predictions, prediction_row,
)


class ResearchInvariants(unittest.TestCase):
    def test_exact_boundaries_and_orphan_i(self):
        self.assertEqual(spans(["I", "I", "O", "B", "B", "I"]), [(0, 2), (3, 4), (4, 6)])

    def test_overlapping_and_out_of_bounds_spans_rejected(self):
        for value in ([[0, 2], [1, 3]], [[0, 4]], [[1, 1]], [[True, 2]]):
            with self.assertRaises(ValueError):
                validate_spans(value, 3)

    def test_skill_and_knowledge_channels_stay_separate(self):
        row = {"tokens": ["write", "Python"], "tags_skill": ["B", "O"], "tags_knowledge": ["O", "B"]}
        skill, _ = build_lexicon([row], "skill")
        knowledge, _ = build_lexicon([row], "knowledge")
        self.assertEqual(skill, {("write",)})
        self.assertEqual(knowledge, {("python",)})

    def test_train_overlap_filter_does_not_remove_other_sentences(self):
        data = {"train": [{"tokens": ["same"]}],
                "dev": [{"tokens": ["same"]}, {"tokens": ["different"]}],
                "test": [{"tokens": ["same"]}, {"tokens": ["different"]}]}
        result = filter_training_overlap(data)
        self.assertEqual(result["dev"], [{"tokens": ["different"]}])
        self.assertEqual(result["test"], [{"tokens": ["different"]}])

    def test_longest_nonoverlapping_word_matches(self):
        pattern = trie_pattern(["data", "data science", "python"])
        self.assertEqual([m.group() for m in pattern.finditer("data science database python")], ["data science", "python"])

    def test_paired_bootstrap_identical_predictions_is_zero(self):
        result = bootstrap(["a", "b", "a"], ["a", "a", "a"], ["a", "a", "a"],
                           np.array(["firm1", "firm1", "firm2"]), ["a", "b"], 50)
        self.assertEqual(result["ci95"], [0.0, 0.0])
        self.assertEqual(result["clusters"], 2)

    def test_bootstrap_uses_fixed_categories(self):
        result = bootstrap(["a", "a"], ["a", "a"], ["a", "a"], np.array(["x", "y"]), ["a", "b"], 20)
        self.assertEqual(result["delta_macro_f1"], 0.0)
        self.assertEqual(metrics(["a"], ["a"], ["a", "b"])["macro_f1"], 0.5)

    def test_prediction_truth_tampering_rejected(self):
        record = {"sentence_id": "test:1", "source": "tech", "idx": 1, "tokens": ["Python"],
                  "tags_skill": ["O"], "tags_knowledge": ["B"]}
        row = prediction_row(record, "knowledge", "train_lexicon", [(0, 1)])
        row["gold"] = []
        with self.assertRaises(ValueError):
            validate_predictions([row], [record], "knowledge", "train_lexicon")

    def test_persisted_metric_tampering_rejected(self):
        for incorrect in (0.8, float("nan"), True):
            with self.assertRaises(ValueError):
                require_equal(0.7, incorrect)

    def test_job_cluster_pairing_rejects_reordered_ids(self):
        row = {"sentence_id": "test:1", "source": "tech", "job_idx": 1, "channel": "skill",
               "tokens_sha256": "x", "token_count": 1, "gold": [[0, 1]], "prediction": [[0, 1]]}
        other = copy.deepcopy(row)
        other["sentence_id"] = "test:2"
        with self.assertRaises(ValueError):
            paired_interval([row], [other], 10)

    def test_comparison_checks_labels_and_employers_against_cohort(self):
        record = {"id": "p1", "group": "employer1", "label": "a"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "predictions.csv"
            for changed in ({"true": "b"}, {"group": "employer2"}, {"predicted": "unknown"}):
                prediction = {"id": "p1", "group": "employer1", "true": "a", "predicted": "a", **changed}
                with path.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=["id", "group", "true", "predicted"])
                    writer.writeheader()
                    writer.writerow(prediction)
                with self.assertRaises(ValueError):
                    read_predictions(path, [record], [0], ["a", "b"])

    def test_comparison_checks_every_confusion_cell(self):
        expected = {"macro_f1": 0.75, "confusion_matrix": [[2, 1], [0, 1]]}
        changed = copy.deepcopy(expected)
        changed["confusion_matrix"][0][0] = 3
        with self.assertRaises(ValueError):
            close(changed, expected, "test")


if __name__ == "__main__":
    unittest.main()
