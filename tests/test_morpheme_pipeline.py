import unittest

from genui_intent.morpheme import (apply_information_budget, expand_draft, plan_layout,
                                   reconcile_types, validate_draft)
from genui_intent.morpheme_pipeline import MorphemePipeline
from genui_intent.providers import MockProvider


class MorphemePipelineTests(unittest.TestCase):
    def setUp(self):
        self.draft = {"s": "CARD", "z": "AUTO", "d": "COMPACT", "t": "状态", "m": [
            {"k": "PROGRESS", "r": "PRIMARY", "l": "电量", "q": "battery.level", "f": "PERCENTAGE"},
            {"k": "SWITCH", "r": "PRIMARY_ACTION", "l": "蓝牙", "q": "bluetooth.power", "f": "BOOLEAN"},
        ]}

    def test_draft_validation_and_expansion(self):
        self.assertEqual(validate_draft(self.draft), [])
        spec = expand_draft(self.draft)
        self.assertEqual(spec["morphemes"][0]["priority"], 90)
        self.assertEqual(spec["morphemes"][1]["actionKey"], "bluetooth.power.set")
        self.assertEqual(plan_layout(spec)["template"], "CONTENT_ACTIONS")

    def test_semantic_type_reconciliation(self):
        draft = {"s": "CARD", "z": "AUTO", "d": "AUTO", "t": "天气", "m": [
            {"k": "TEXT", "r": "SECONDARY", "l": "气温", "q": "weather.temperature", "f": "STRING"},
            {"k": "TEXT", "r": "SECONDARY", "l": "湿度", "q": "weather.humidity", "f": "STRING"},
        ]}
        spec, corrections = reconcile_types(expand_draft(draft))
        self.assertEqual([(x["type"], x["valueType"]) for x in spec["morphemes"]],
                         [("METRIC", "NUMBER"), ("PROGRESS", "PERCENTAGE")])
        self.assertEqual(len(corrections), 2)

    def test_generic_count_status_and_action_constraints(self):
        draft = {"s": "CARD", "z": "2x2", "d": "AUTO", "t": "联系人", "m": [
            {"k": "PROGRESS", "r": "PRIMARY", "l": "在线状态", "q": "contacts.onlineStatus", "f": "ENUM"},
            {"k": "STATUS", "r": "SECONDARY", "l": "联系人数量", "q": "contacts.count", "f": "PERCENTAGE"},
            {"k": "SWITCH", "r": "PRIMARY_ACTION", "l": "添加联系人", "q": "contacts.add", "f": "BOOLEAN"},
        ]}
        spec, corrections = reconcile_types(expand_draft(draft))
        self.assertEqual([(x["type"], x["valueType"]) for x in spec["morphemes"]], [
            ("STATUS", "ENUM"), ("METRIC", "NUMBER"), ("BUTTON", "UNKNOWN")])
        self.assertEqual(len(corrections), 3)

    def test_capacity_pause_and_toggle_constraints(self):
        draft = {"s": "CARD", "z": "2x2", "d": "AUTO", "t": "控制", "m": [
            {"k": "TEXT", "r": "PRIMARY", "l": "容纳人数", "q": "room.capacity", "f": "NUMBER"},
            {"k": "SWITCH", "r": "PRIMARY_ACTION", "l": "暂停下载", "q": "download.pause", "f": "BOOLEAN"},
            {"k": "BUTTON", "r": "SECONDARY_ACTION", "l": "灯光开关", "q": "light.toggle", "f": "UNKNOWN"},
        ]}
        spec, _ = reconcile_types(expand_draft(draft))
        self.assertEqual([(x["type"], x["valueType"]) for x in spec["morphemes"]], [
            ("METRIC", "NUMBER"), ("BUTTON", "UNKNOWN"), ("SWITCH", "BOOLEAN")])
        self.assertTrue(spec["morphemes"][1]["actionKey"].endswith(".trigger"))
        self.assertTrue(spec["morphemes"][2]["actionKey"].endswith(".set"))

    def test_card_budget_drops_lower_priority_items(self):
        spec = expand_draft(self.draft)
        spec, budget = apply_information_budget(spec, "2x1")
        self.assertLessEqual(budget["used"], budget["capacity"])
        self.assertEqual(spec["surface"]["size"], "2x1")

    def test_composite_key_is_split_and_compacted_for_2x1(self):
        draft = {"s": "CARD", "z": "2x1", "d": "AUTO", "t": "天气", "m": [
            {"k": "TEXT", "r": "PRIMARY", "l": "天气", "q": "weather.condition", "f": "ENUM"},
            {"k": "TEXT", "r": "SECONDARY", "l": "气温和湿度", "q": "weather.temperature,weather.humidity", "f": "NUMBER"},
        ]}
        spec, corrections = reconcile_types(expand_draft(draft))
        self.assertEqual(len(spec["morphemes"]), 3)
        spec, budget = apply_information_budget(spec, "2x1")
        self.assertEqual(len(spec["morphemes"]), 3)
        self.assertEqual(spec["morphemes"][2]["type"], "METRIC")
        self.assertTrue(budget["substitutions"])

    def test_mock_pipeline_reaches_render_spec(self):
        events = []
        result = MorphemePipeline(MockProvider(), events.append).generate("生成耳机卡片")
        self.assertEqual(result["renderSpec"]["template"], "2x2_gauge_action")
        self.assertEqual(result["rendered"]["protocol"], "html_css")
        self.assertEqual(set(result["protocolOutputs"]), {"dsl", "a2ui", "html_css"})
        self.assertTrue(result["protocolOutputs"]["dsl"]["code"].startswith('{"@generated-card"'))
        self.assertIn('"createSurface"', result["protocolOutputs"]["a2ui"]["ndjson"])
        self.assertIn('data-morpheme="PROGRESS"', result["code"])
        self.assertIn('data-size="2x2"', result["code"])
        completed = {e["stage"] for e in events if e["status"] == "completed"}
        self.assertTrue({"morpheme_expand", "mock_data", "layout", "render_spec", "codegen", "result"} <= completed)


if __name__ == "__main__":
    unittest.main()
