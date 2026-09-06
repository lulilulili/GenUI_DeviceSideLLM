import json
import unittest
from genui_intent.events import Trace
from genui_intent.pipeline import IntentPipeline
from genui_intent.providers import MockProvider, OpenAICompatibleProvider, OllamaProvider
from genui_intent.config import Settings

class WorkbenchTests(unittest.TestCase):
    def test_stage_snapshots_and_order(self):
        events = []
        result = IntentPipeline(MockProvider(), events.append).generate("请鼓励我")
        self.assertEqual(events[-1]["output"], result)
        self.assertEqual([e["sequence"] for e in events], list(range(1, len(events)+1)))
        model = [e for e in events if e["stage"] == "model_call_1"]
        self.assertEqual([e["status"] for e in model], ["running", "completed"])
        self.assertIsNone(model[-1]["usage"])
        self.assertIn("system", model[0]["input"])

    def test_failure_is_observable(self):
        events = []
        with self.assertRaises(ValueError):
            IntentPipeline(MockProvider(), events.append).generate("")
        self.assertEqual(events[-1]["status"], "failed")

    def test_compatible_schema_and_usage(self):
        p = OpenAICompatibleProvider(Settings(provider="openai_compatible"))
        payloads = []
        def post(url, payload):
            payloads.append(payload)
            return {"choices": [{"message": {"content": "{}"}}],
                    "usage": {"prompt_tokens": 11, "completion_tokens": 3}}
        p._post = post
        p.complete("system", "user", schema={"type": "object"})
        self.assertEqual(payloads[-1]["response_format"]["type"], "json_schema")
        self.assertEqual(p.last_usage["inputTokens"], 11)
        p.complete("system", "user", max_tokens=12)
        self.assertNotIn("response_format", payloads[-1])

    def test_ollama_usage(self):
        p = OllamaProvider(Settings())
        p._post = lambda *args: {"message": {"content": "{}"}, "prompt_eval_count": 20,
                                "eval_count": 5, "eval_duration": 1000000}
        p.complete("system", "user")
        self.assertEqual(p.last_usage["outputTokens"], 5)
        self.assertEqual(p.last_usage["decodeMs"], 1)

if __name__ == "__main__":
    unittest.main()
