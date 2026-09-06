import unittest

from genui_intent.layout_engine import STYLE_PRESETS, TEMPLATES, plan, render_spec
from genui_intent.renderers import render


def spec(size, components):
    return {"title": "测试卡片", "surface": {"type": "CARD", "size": size},
            "morphemes": [{"id": f"m{i + 1}", "type": kind, "role": role,
                            "priority": 90 - i * 5, "label": kind, "content": {}}
                           for i, (kind, role) in enumerate(components)]}


class LayoutEngineTests(unittest.TestCase):
    def test_catalog_covers_supported_sizes(self):
        self.assertEqual({item["size"] for item in TEMPLATES}, {"2x1", "2x2", "3x2", "3x3"})
        self.assertGreaterEqual(len(TEMPLATES), 25)

    def test_pdf_wide_shortcuts_pattern(self):
        layout = plan(spec("3x2", [("TEXT", "PRIMARY"), ("BUTTON", "PRIMARY_ACTION"),
                                        ("BUTTON", "SECONDARY_ACTION"), ("BUTTON", "SECONDARY_ACTION"),
                                        ("BUTTON", "SECONDARY_ACTION")]))
        self.assertIn(layout["templateId"], {"3x2_service_strip", "3x2_search_shortcuts"})
        self.assertFalse(layout["unplaced"])

    def test_pdf_gauge_pattern(self):
        layout = plan(spec("2x2", [("PROGRESS", "PRIMARY"), ("STATUS", "SECONDARY"),
                                        ("BUTTON", "PRIMARY_ACTION")]))
        self.assertEqual(layout["templateId"], "2x2_gauge_action")
        self.assertEqual(layout["confidence"], 1)

    def test_pdf_list_pattern(self):
        layout = plan(spec("2x2", [("LIST", "PRIMARY"), ("TEXT", "SECONDARY")]))
        self.assertEqual(layout["templateId"], "2x2_list")
        self.assertFalse(layout["unplaced"])

    def test_pdf_shortcut_pattern(self):
        layout = plan(spec("2x2", [("BUTTON", "PRIMARY_ACTION")] * 4))
        self.assertEqual(layout["templateId"], "2x2_shortcuts")
        self.assertEqual(len([x for x in layout["slots"] if x.get("component")]), 4)

    def test_component_family_substitution(self):
        layout = plan(spec("2x1", [("METRIC", "PRIMARY"), ("SWITCH", "PRIMARY_ACTION")]))
        self.assertNotEqual(layout["mode"], "FREE")
        self.assertTrue(any(x["component"] and x["component"]["type"] == "SWITCH"
                            for x in layout["slots"]))

    def test_near_optimal_selection_is_stable_and_distributed(self):
        selected = []
        for title, key in (("跑步", "sport.running.distance"), ("骑行", "sport.cycling.distance"),
                           ("步数", "health.steps"), ("心率", "health.heartRate"),
                           ("训练", "fitness.workout.duration"), ("热量", "fitness.calories")):
            source = spec("2x1", [("METRIC", "PRIMARY"), ("STATUS", "SECONDARY")])
            source["title"] = title
            for item in source["morphemes"]:
                item["semanticKey"] = key + "." + item["type"].lower()
            first, second = plan(source), plan(source)
            self.assertEqual(first["templateId"], second["templateId"])
            self.assertEqual(first["selectionPolicy"]["name"], "NEAR_OPTIMAL_SEMANTIC_HASH")
            selected.append(first["templateId"])
        self.assertGreater(len(set(selected)), 1)

    def test_no_paradigm_uses_free_layout(self):
        layout = plan(spec("2x1", [("LIST", "PRIMARY")] * 3))
        self.assertEqual(layout["mode"], "FREE")
        self.assertEqual(len(layout["slots"]), 3)

    def test_slots_do_not_overlap(self):
        layout = plan(spec("3x3", [("METRIC", "PRIMARY"), ("STATUS", "SECONDARY"),
                                        ("METRIC", "SUPPORTING"), ("BUTTON", "PRIMARY_ACTION")]))
        rects = [x["rect"] for x in layout["slots"]]
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                overlap = not (a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"] or
                               a["y"] + a["h"] <= b["y"] or b["y"] + b["h"] <= a["y"])
                self.assertFalse(overlap)

    def test_render_protocols_share_render_spec(self):
        source = spec("2x2", [("METRIC", "PRIMARY"), ("TEXT", "SECONDARY")])
        rs = render_spec(source, plan(source, "soft"))
        html, a2ui, dsl = render(rs, "html_css"), render(rs, "a2ui"), render(rs, "dsl")
        self.assertIn("card.html", html["files"])
        self.assertEqual(a2ui["protocol"], "a2ui")
        self.assertEqual(a2ui["version"], "v0.9")
        self.assertIn("createSurface", a2ui["messages"][0])
        self.assertTrue(all(len(message["updateComponents"]["components"]) == 1
                            for message in a2ui["messages"][1:]))
        self.assertEqual(dsl["protocol"], "dsl")
        self.assertTrue(dsl["lines"][0].startswith('{"@generated-card"'))
        self.assertIn('"Grid"', dsl["code"])
        self.assertEqual(rs["style"]["tokens"], STYLE_PRESETS["soft"])

    def test_invalid_protocol_is_explicit(self):
        with self.assertRaises(ValueError):
            render({}, "unknown")


if __name__ == "__main__":
    unittest.main()
