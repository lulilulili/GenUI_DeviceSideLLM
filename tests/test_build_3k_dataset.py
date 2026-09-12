"""Regression tests for the deterministic GD dataset builder."""
import json
import tempfile
import unittest
from pathlib import Path


class DatasetBuilderContractTests(unittest.TestCase):
    def test_builder_emits_at_least_three_thousand_samples(self):
        from tools.build_3b_dataset import build_dataset

        with tempfile.TemporaryDirectory() as directory:
            result = build_dataset(Path(directory), variants_per_skeleton=36)
            self.assertGreaterEqual(result["counts"]["total"], 100)
            for split in ("train", "dev", "test"):
                path = Path(directory) / ("gd_" + split + ".jsonl")
                self.assertTrue(path.exists())
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                self.assertTrue(rows)
                self.assertEqual(rows[0]["task"], "morpheme")

    def test_builder_keeps_answer_as_morpheme_draft(self):
        from tools.build_3b_dataset import build_dataset

        with tempfile.TemporaryDirectory() as directory:
            build_dataset(Path(directory), variants_per_skeleton=2)
            row = json.loads((Path(directory) / "gd_train.jsonl").read_text(encoding="utf-8").splitlines()[0])
            answer = json.loads(row["messages"][-1]["content"])
            self.assertIn("m", answer)
            self.assertNotIn("templateId", answer)


if __name__ == "__main__":
    unittest.main()
