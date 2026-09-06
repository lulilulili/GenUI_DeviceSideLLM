import unittest

from genui_intent.pipeline import IntentPipeline
from genui_intent.providers import MockProvider
from genui_intent.router import rule_route
from genui_intent.validation import validate


class PipelineTests(unittest.TestCase):
    def test_rule_router(self):
        self.assertEqual(rule_route("今天会下雨吗"), "WEATHER")
        self.assertEqual(rule_route("把台灯调暗一点"), "SMART_HOME")
        self.assertIsNone(rule_route("你好"))

    def test_mock_pipeline_is_valid(self):
        result = IntentPipeline(MockProvider()).generate("我马上要考试了，请帮我加油打气")
        self.assertEqual(validate(result, "CONTENT"), [])
        self.assertEqual(result["tasks"][0]["entity"]["entityCategoryKey"], "encouragement_message")

    def test_dynamic_candidate_is_rejected(self):
        result = IntentPipeline(MockProvider()).generate("请鼓励我")
        result["tasks"][0]["entity"]["entityCategoryKey"] = "invented"
        self.assertTrue(any("领域候选" in error for error in validate(result, "CONTENT")))


if __name__ == "__main__":
    unittest.main()

