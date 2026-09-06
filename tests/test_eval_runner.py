import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

from run_ollama_eval import check_case, load_cases


class EvalRunnerTests(unittest.TestCase):
    def test_dataset_ids_are_unique_and_required_fields_exist(self):
        cases = load_cases(ROOT / "evals" / "intent_cases.jsonl", set(), set())
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(cases), 60)
        for case in cases:
            self.assertTrue(case["prompt"].strip())
            self.assertIn("domain", case["expected"])
            self.assertIn(case["expected"]["domain"], {"SMART_HOME", "WEATHER", "DEVICE", "CONTENT", "TASK"})

    def test_partial_semantic_matcher(self):
        actual = {
            "domain": "DEVICE", "intentType": "QUERY", "goalType": "OBTAIN_INFORMATION",
            "tasks": [{
                "entity": {"entityCategoryKey": "battery", "entityMention": "手机", "referenceType": "EXPLICIT"},
                "operation": {"operationType": "GET", "propertyKey": "level"},
                "parameters": [], "contexts": [], "dependsOn": []
            }],
            "resolution": {"status": "RESOLVED", "missingFields": []}
        }
        expected = {"domain": "DEVICE", "tasks": [{"entityCategoryKey": "battery", "operationType": "GET", "propertyKey": "level"}]}
        checks, passed, total = check_case(actual, expected)
        self.assertEqual(passed, total)
        self.assertTrue(all(item["passed"] for item in checks))

    def test_filter_by_tag_and_id(self):
        path = ROOT / "evals" / "intent_cases.jsonl"
        tagged = load_cases(path, {"adversarial"}, set())
        selected = load_cases(path, set(), {"sh_relative_01"})
        self.assertTrue(tagged)
        self.assertTrue(all("adversarial" in case["tags"] for case in tagged))
        self.assertEqual([case["id"] for case in selected], ["sh_relative_01"])


if __name__ == "__main__":
    unittest.main()

