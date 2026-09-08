"""Layout v2: PDF-archetype matching first, hierarchical free composition second.

Template hit-rate levers (all deterministic, see docs §4):
1. The prompt caps morpheme count per size and requires exactly one PRIMARY and
   at most two actions — the same shape every PDF archetype expects, so drafts
   arrive "template-shaped" instead of being repaired afterwards.
2. Components are derived (derive.py), so FAMILY compatibility with slots holds
   by construction; the scorer's FOOTPRINT relaxation covers near-misses.
3. Information budget runs BEFORE matching, so oversized drafts degrade into
   the archetype capacity instead of forcing a fallback.

Free layout (when no archetype reaches 50% coverage) follows the PDF's visual
grammar instead of a uniform grid:
  hero band (one PRIMARY, >=40% height) -> detail grid (aligned columns,
  8px gutters) -> bottom action bar (<=2 pills). One hierarchy, one accent,
  shared left edge — the three rules that make the reference cards look calm.
"""
from genui_intent.layout_engine import (  # reuse the measured PDF archetypes
    TEMPLATES, _best_assignment, _overlaps, _place_in_whitespace, _select_near_optimal)
from .tokens import SIZES, style_tokens

MIN_TEMPLATE_COVERAGE = 0.5


def _style_block(style_id, domain, size):
    resolved_id, tokens = style_tokens(style_id, domain)
    merged = dict(tokens)
    merged.update({  # compat aliases so the a2ui/dsl renderers keep working
        "cardBg": tokens["bg"], "cardFg": tokens["fg"], "muted": tokens["chip"],
        "radius": SIZES[size]["radius"]})
    return {"preset": resolved_id, "tokens": merged,
            "componentVariants": {"TEXT": "body", "METRIC": "hero-number", "STATUS": "badge",
                                  "PROGRESS": "ring", "BUTTON": "pill", "SWITCH": "compact",
                                  "SLIDER": "track", "LIST": "rows"}}


def _free_slots(morphemes, size):
    rows = SIZES[size]["grid_rows"]
    hero = max((m for m in morphemes if m["role"] in ("PRIMARY", "WARNING")),
               key=lambda m: m["priority"], default=None)
    actions = [m for m in morphemes if "ACTION" in m["role"]][:2]
    used = {id(hero)} | {id(m) for m in actions}
    details = [m for m in sorted(morphemes, key=lambda m: -m["priority"]) if id(m) not in used]
    slots = []

    if size == "2x1":
        if hero is not None and details:
            slots.append({"id": "hero", "rect": {"x": 0, "y": 0, "w": 9, "h": 3}, "component": hero})
            slots.append({"id": "detail1", "rect": {"x": 0, "y": 3, "w": 9, "h": 3}, "component": details[0]})
        elif hero is not None:
            slots.append({"id": "hero", "rect": {"x": 0, "y": 0, "w": 9, "h": rows}, "component": hero})
        if actions:
            slots.append({"id": "action1", "rect": {"x": 9, "y": 1, "w": 3, "h": 4}, "component": actions[0]})
        return slots, rows

    action_rows = 3 if rows >= 12 else 2
    body_rows = rows - (action_rows if actions else 0)
    hero_rows = max(3, round(body_rows * (0.55 if not details else 0.45))) if hero is not None else 0
    if hero is not None:
        slots.append({"id": "hero", "rect": {"x": 0, "y": 0, "w": 12, "h": hero_rows}, "component": hero})
    columns = 2 if size == "2x2" else 3
    grid_top, grid_rows_left = hero_rows, body_rows - hero_rows
    laid, row_cursor, col_cursor = [], 0, 0
    if details and grid_rows_left > 0:
        # LIST items take a full row; small items share a row per column.
        cells = []
        for item in details:
            span = columns if item["type"] == "LIST" else 1
            cells.append((item, span))
        needed_rows = 0
        col = 0
        for _, span in cells:
            if span == columns:
                needed_rows += 1 if col == 0 else 2
                col = 0
            else:
                if col == 0:
                    needed_rows += 1
                col = (col + span) % columns
        needed_rows = max(1, needed_rows)
        row_height = max(2, grid_rows_left // needed_rows)
        for item, span in cells:
            if span == columns and col_cursor:
                row_cursor, col_cursor = row_cursor + 1, 0
            y = grid_top + row_cursor * row_height
            if y + row_height > grid_top + grid_rows_left:
                break
            width = 12 if span == columns else 12 // columns
            x = 0 if span == columns else col_cursor * (12 // columns)
            height = row_height * (2 if span == columns and item["type"] == "LIST"
                                   and grid_rows_left - row_cursor * row_height >= row_height * 2 else 1)
            laid.append({"id": "detail%d" % (len(laid) + 1),
                         "rect": {"x": x, "y": y, "w": width, "h": height}, "component": item})
            if span == columns:
                row_cursor += height // row_height
                col_cursor = 0
            else:
                col_cursor += 1
                if col_cursor >= columns:
                    row_cursor, col_cursor = row_cursor + 1, 0
    slots.extend(laid)
    if actions:
        width = 12 // len(actions)
        for index, item in enumerate(actions):
            slots.append({"id": "action%d" % (index + 1),
                          "rect": {"x": index * width, "y": rows - action_rows, "w": width, "h": action_rows},
                          "component": item})
    return slots, rows


def _free_layout(spec, size):
    slots, rows = _free_slots(spec["morphemes"], size)
    placed_ids = {slot["component"]["id"] for slot in slots}
    unplaced = [m["id"] for m in spec["morphemes"] if m["id"] not in placed_ids]
    for slot in slots:
        slot.update({"match": "FREE", "sourceSlot": None})
    return {"templateId": "free_" + size, "templateName": "层级式自由布局", "source": "Free composition v2",
            "mode": "FREE", "score": 0, "confidence": 0,
            "grid": {"columns": 12, "rows": rows, "gap": 1}, "slots": slots, "unplaced": unplaced,
            "rationale": ["无原型达到最低覆盖率；按 主视觉带→细节网格→底部操作条 层级式排布。"]}


def _places_all_primaries(spec, assignment):
    """A template that cannot seat the PRIMARY/WARNING content is disqualified —
    a todo card must never drop its todo list to fit a prettier archetype."""
    for component_index, slot_index, _ in assignment:
        if slot_index < 0 and spec["morphemes"][component_index]["role"] in ("PRIMARY", "WARNING"):
            return False
    return True


def plan(spec, style_id="auto", domain=None):
    size = spec["surface"]["size"]
    candidates = [template for template in TEMPLATES if template["size"] == size]
    ranked = []
    for template in candidates:
        score, assignment = _best_assignment(spec["morphemes"], template["slots"])
        matched = sum(slot_index >= 0 for _, slot_index, _ in assignment)
        coverage = matched / max(1, len(spec["morphemes"]))
        ranked.append((score + round(coverage * 25), coverage, template, assignment))
    ranked.sort(key=lambda item: (-item[0], item[2]["id"]))
    eligible = [item for item in ranked if _places_all_primaries(spec, item[3])]
    if not eligible or eligible[0][1] < MIN_TEMPLATE_COVERAGE:
        result = _free_layout(spec, size)
    else:
        selected, near = _select_near_optimal(eligible, spec)
        score, coverage, template, assignment = selected
        slots, occupied, unmatched = [], [], []
        for component_index, slot_index, quality in assignment:
            if slot_index < 0:
                unmatched.append(spec["morphemes"][component_index])
                continue
            target = template["slots"][slot_index]
            occupied.append(target["rect"])
            slots.append({"id": target["id"], "rect": target["rect"],
                          "component": spec["morphemes"][component_index],
                          "match": quality, "sourceSlot": target["id"]})
        added, unplaced = [], []
        for component in unmatched:
            rect = _place_in_whitespace(component, template["rows"], occupied)
            if rect:
                occupied.append(rect)
                slots.append({"id": "extra_" + component["id"], "rect": rect, "component": component,
                              "match": "WHITESPACE", "sourceSlot": None})
                added.append(component["id"])
            else:
                unplaced.append(component["id"])
        for target in template["slots"]:
            if (target["placeholder"] and not any(item["sourceSlot"] == target["id"] for item in slots)
                    and not _overlaps(target["rect"], occupied)):
                slots.append({"id": target["id"], "rect": target["rect"], "component": None,
                              "placeholder": target["placeholder"], "match": "PLACEHOLDER",
                              "sourceSlot": target["id"]})
        matched = len(spec["morphemes"]) - len(unmatched)
        result = {"templateId": template["id"], "templateName": template["name"],
                  "source": template["source"], "mode": "TEMPLATE_EXTENDED" if added else "TEMPLATE",
                  "score": score, "confidence": round(coverage, 2),
                  "grid": {"columns": 12, "rows": template["rows"], "gap": 1}, "slots": slots,
                  "unplaced": unplaced,
                  "rationale": ["覆盖 %d/%d 个语素。" % (matched, len(spec["morphemes"])),
                                "模板来源：%s。" % template["source"],
                                "近优候选 %d 个；语义签名稳定选型。" % len(near)]
                  + (["额外语素放入模板留白。"] if added else [])}
        if unplaced:
            result = _free_layout(spec, size)
    result["style"] = _style_block(style_id, domain, size)
    result["alternatives"] = [{"templateId": item[2]["id"], "name": item[2]["name"],
                               "score": item[0], "coverage": round(item[1], 2)} for item in ranked[:3]]
    return result


def render_spec(spec, layout):
    return {"version": "0.3", "title": spec.get("title"), "surface": spec["surface"],
            "template": layout["templateId"], "templateName": layout["templateName"],
            "layoutMode": layout["mode"], "grid": layout["grid"], "slots": layout["slots"],
            "style": layout["style"],
            "diagnostics": {"score": layout["score"], "confidence": layout["confidence"],
                            "source": layout.get("source"), "rationale": layout["rationale"],
                            "unplaced": layout["unplaced"], "alternatives": layout["alternatives"]}}
