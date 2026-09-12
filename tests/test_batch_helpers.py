import json
import tempfile
import unittest
from pathlib import Path

from genui_v2.batch import assistant_json, domain_from_row, load_jsonl, parse_indices


class BatchHelperTests(unittest.TestCase):
    def test_parse_indices_supports_ranges_and_deduplicates(self):
        self.assertEqual(parse_indices("1, 3-5,4", 10), [1, 3, 4, 5])

    def test_parse_indices_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            parse_indices("0,2", 3)

    def test_load_and_extract_training_row(self):
        row = {"messages": [{"role": "user", "content": "领域=DEVICE\n用户=看看电量"},
                             {"role": "assistant", "content": '{"t":"电量","m":[]}'}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.jsonl"
            path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            loaded = load_jsonl(path)
        self.assertEqual(assistant_json(loaded[0])["t"], "电量")
        self.assertEqual(domain_from_row(loaded[0]), "DEVICE")


if __name__ == "__main__":
    unittest.main()
