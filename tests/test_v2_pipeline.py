"""Smoke tests for the v2 pipeline (no pytest, no network)."""
import unittest

from genui_v2 import PipelineV2, MockProviderV2
from genui_v2.capability import resolve
from genui_v2.derive import derive_component
from genui_v2.protocol import validate_draft, normalize_draft
from genui_v2.elision import plan_label_visibility


class ElisionTests(unittest.TestCase):
    def _spec(self, title, morphemes):
        return {"title": title, "surface": {"size": "2x2"}, "morphemes": morphemes}

    def _m(self, mid, kind, label, role="SECONDARY", unit=None, value_type="STRING"):
        content = {"unit": unit} if unit else {}
        return {"id": mid, "type": kind, "label": label, "role": role,
                "valueType": value_type, "content": content, "presentation": {},
                "semanticKey": "x"}

    def test_ring_label_hidden_when_title_covers(self):
        spec = self._spec("耳机状态", [self._m("m1", "PROGRESS", "耳机电量", "PRIMARY",
                                               value_type="PERCENTAGE")])
        _, decisions = plan_label_visibility(spec)
        self.assertFalse(decisions[0]["show"])
        self.assertEqual(spec["morphemes"][0]["presentation"]["a11yLabel"], "耳机电量")

    def test_siblings_always_labelled(self):
        spec = self._spec("环境状态", [
            self._m("m1", "PROGRESS", "电量", "PRIMARY", value_type="PERCENTAGE"),
            self._m("m2", "PROGRESS", "湿度", value_type="PERCENTAGE")])
        _, decisions = plan_label_visibility(spec)
        self.assertTrue(all(d["show"] for d in decisions))
        self.assertEqual(decisions[0]["reason"], "SIBLING_DISAMBIGUATION")

    def test_strong_unit_metric_hidden(self):
        spec = self._spec("北京天气", [self._m("m1", "METRIC", "温度", "PRIMARY",
                                               unit="°", value_type="NUMBER")])
        _, decisions = plan_label_visibility(spec)
        self.assertFalse(decisions[0]["show"])
        self.assertEqual(decisions[0]["reason"], "VALUE_SELF_EVIDENT")

    def test_ambiguous_status_keeps_label(self):
        spec = self._spec("北京天气", [self._m("m1", "STATUS", "空气质量", "SECONDARY",
                                               value_type="ENUM")])
        _, decisions = plan_label_visibility(spec)
        self.assertTrue(decisions[0]["show"])

    def test_switch_keeps_label_unless_title_subsumes(self):
        spec = self._spec("耳机状态", [self._m("m1", "SWITCH", "蓝牙", "PRIMARY_ACTION",
                                               value_type="BOOLEAN")])
        _, decisions = plan_label_visibility(spec)
        self.assertTrue(decisions[0]["show"])
        spec2 = self._spec("蓝牙", [self._m("m1", "SWITCH", "蓝牙", "PRIMARY_ACTION",
                                            value_type="BOOLEAN")])
        _, decisions2 = plan_label_visibility(spec2)
        self.assertFalse(decisions2[0]["show"])


class DeriveTests(unittest.TestCase):
    def _m(self, role, value_type, key="x", label=""):
        return {"role": role, "valueType": value_type, "semanticKey": key, "label": label}

    def test_action_shapes(self):
        self.assertEqual(derive_component(self._m("PRIMARY_ACTION", "BOOLEAN")), "SWITCH")
        self.assertEqual(derive_component(self._m("PRIMARY_ACTION", "PERCENTAGE")), "SLIDER")
        self.assertEqual(derive_component(self._m("PRIMARY_ACTION", "STRING")), "BUTTON")

    def test_info_shapes(self):
        self.assertEqual(derive_component(self._m("PRIMARY", "PERCENTAGE")), "PROGRESS")
        self.assertEqual(derive_component(self._m("PRIMARY", "NUMBER")), "METRIC")
        self.assertEqual(derive_component(self._m("SECONDARY", "ENUM")), "STATUS")
        self.assertEqual(derive_component(self._m("SECONDARY", "LIST")), "LIST")


class CapabilityTests(unittest.TestCase):
    def test_exact_alias_token(self):
        self.assertEqual(resolve("phone.battery.level")[1], "EXACT")
        self.assertEqual(resolve("battery.level", "手机电量")[0]["key"], "phone.battery.level")
        entry, how = resolve("wifi.switch", "Wi-Fi")
        self.assertEqual(entry["key"], "wifi.power")
        self.assertIn(how, ("ALIAS", "TOKENS"))

    def test_miss(self):
        self.assertEqual(resolve("quantum.flux", "反物质")[1], "MISS")


class DraftValidationTests(unittest.TestCase):
    def test_normalize_promotes_missing_primary(self):
        draft = {"t": "x", "m": [{"l": "a", "q": "k", "f": "NUMBER", "r": "SECONDARY"}]}
        self.assertEqual(validate_draft(draft, "2x2"), [])
        fixed, corrections = normalize_draft(draft)
        self.assertEqual(fixed["m"][0]["r"], "PRIMARY")
        self.assertEqual(corrections[0]["reason"], "NO_PRIMARY")

    def test_normalize_demotes_extra_primary(self):
        draft = {"t": "x", "m": [
            {"l": "待办", "q": "task.list", "f": "LIST", "r": "PRIMARY"},
            {"l": "日程", "q": "calendar.next_event", "f": "STRING", "r": "PRIMARY"}]}
        fixed, corrections = normalize_draft(draft)
        roles = [item["r"] for item in fixed["m"]]
        self.assertEqual(roles, ["PRIMARY", "SECONDARY"])
        self.assertEqual(corrections[0]["reason"], "MULTI_PRIMARY")


class PipelineTests(unittest.TestCase):
    def test_end_to_end_mock(self):
        events = []
        result = PipelineV2(MockProviderV2(), on_event=events.append).generate(
            "显示耳机电量、连接状态和蓝牙开关", card_size="2x2")
        spec = result["morphemeSpec"]
        self.assertEqual(spec["surface"]["size"], "2x2")
        types = {item["id"]: item["type"] for item in spec["morphemes"]}
        self.assertEqual(types["m1"], "PROGRESS")
        self.assertEqual(types["m3"], "SWITCH")
        bindings = {row["q"]: row["resolution"] for row in result["bindReport"]}
        self.assertEqual(bindings["headphones.battery.level"], "EXACT")
        self.assertIn(result["layout"]["mode"], ("TEMPLATE", "TEMPLATE_EXTENDED", "FREE"))
        html = result["protocolOutputs"]["html_css"]["files"]["card.html"]
        self.assertIn("gv2-card", html)
        self.assertIn("data-size=\"2x2\"", html)
        ndjson = result["protocolOutputs"]["a2ui"]["ndjson"]
        self.assertIn("createSurface", ndjson)
        self.assertTrue(any(event["stage"] == "capability_bind" for event in events))

    def test_auto_size(self):
        result = PipelineV2(MockProviderV2()).generate("耳机状态", card_size="AUTO")
        self.assertIn(result["morphemeSpec"]["surface"]["size"], ("2x1", "2x2"))


if __name__ == "__main__":
    unittest.main()
