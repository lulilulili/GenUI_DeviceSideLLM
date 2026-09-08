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

# 自由布局的几何常识：每种组件的最小/舒适高度（px），格子低于最小值就不硬塞。
_MIN_PX = {"PROGRESS": 70, "METRIC": 50, "STATUS": 34, "TEXT": 34, "SWITCH": 40,
           "SLIDER": 40, "LIST": 58, "IMAGE": 44, "ICON": 32, "BUTTON": 36}
_COMFORT_PX = {"METRIC": 58, "PROGRESS": 74}


def _rows_needed(kind, row_px):
    import math
    return max(2, math.ceil(_MIN_PX.get(kind, 34) / row_px))


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


def _free_slots(morphemes, size, reserved_top=0):
    dims = SIZES[size]
    rows = dims["grid_rows"]
    row_px = (dims["h"] - 2 * dims["padding"]) / rows
    hero = max((m for m in morphemes if m["role"] in ("PRIMARY", "WARNING")),
               key=lambda m: m["priority"], default=None)
    actions = [m for m in morphemes if "ACTION" in m["role"]][:2]
    used = {id(hero)} | {id(m) for m in actions}
    details = [m for m in sorted(morphemes, key=lambda m: -m["priority"]) if id(m) not in used]
    slots, dropped = [], []

    if size == "2x1":
        if hero is not None and details:
            slots.append({"id": "hero", "rect": {"x": 0, "y": 0, "w": 9, "h": 3},
                          "component": hero, "compact": True})
            slots.append({"id": "detail1", "rect": {"x": 0, "y": 3, "w": 9, "h": 3},
                          "component": details[0], "compact": True})
            dropped.extend(details[1:])
        elif hero is not None:
            slots.append({"id": "hero", "rect": {"x": 0, "y": 0, "w": 9, "h": rows},
                          "component": hero})
            dropped.extend(details)
        if actions:
            slots.append({"id": "action1", "rect": {"x": 9, "y": 1, "w": 3, "h": 4},
                          "component": actions[0]})
            dropped.extend(actions[1:])
        return slots, rows, dropped

    import math
    action_rows = max(2, math.ceil(36 / row_px)) if actions else 0
    body_rows = rows - action_rows
    columns = 2 if size == "2x2" else 3
    col_width = 12 // columns
    compact_rows = max(2, math.ceil(34 / row_px))

    def _future_bands(queue):
        count, index = 0, 0
        while index < len(queue):
            if queue[index]["type"] == "LIST":
                index += 1
            else:
                step = 0
                while (index + step < len(queue) and step < columns
                       and queue[index + step]["type"] != "LIST"):
                    step += 1
                index += step
            count += 1
        return count

    def pack(hero_rows):
        packed, lost = [], []
        if hero is not None:
            packed.append({"id": "hero",
                           "rect": {"x": 0, "y": reserved_top, "w": 12, "h": hero_rows},
                           "component": hero})
        cursor, limit, queue, band_index = reserved_top + hero_rows, body_rows, list(details), 0
        while queue:
            if queue[0]["type"] == "LIST":
                band = [queue.pop(0)]
            else:
                band = []
                while queue and len(band) < columns and queue[0]["type"] != "LIST":
                    band.append(queue.pop(0))
            need = max(_rows_needed(m["type"], row_px) for m in band)
            rest = _future_bands(queue)
            # 前瞻预留：本带压缩能让后续带也放下时，优先保内容完整而非单带气派
            if rest and cursor + need + compact_rows * rest > limit \
                    and cursor + compact_rows * (rest + 1) <= limit:
                need = compact_rows
            if cursor + need > limit and cursor + compact_rows <= limit:
                need = compact_rows  # 空间不足时压到紧凑高度，几何提示层会降级组件形态
            if cursor + need > limit:
                lost.extend(band + queue)
                break
            band_index += 1
            for index, item in enumerate(band):
                width = 12 if item["type"] == "LIST" else col_width
                packed.append({"id": "detail%d_%d" % (band_index, index + 1),
                               "rect": {"x": 0 if item["type"] == "LIST" else index * col_width,
                                        "y": cursor, "w": width, "h": need},
                               "component": item})
            cursor += need
        if actions:
            width = 12 // len(actions)
            for index, item in enumerate(actions):
                packed.append({"id": "action%d" % (index + 1),
                               "rect": {"x": index * width, "y": rows - action_rows,
                                        "w": width, "h": action_rows},
                               "component": item})
        return packed, lost

    hero_rows = 0
    if hero is not None:
        avail = body_rows - reserved_top
        base = max(3, round(avail * (0.55 if not details else 0.45)))
        hero_rows = min(avail, max(base, _rows_needed(hero["type"], row_px)))
    slots, dropped = pack(hero_rows)
    if dropped and hero is not None:
        shrunk = max(compact_rows, _rows_needed(hero["type"], row_px))
        if shrunk < hero_rows:
            retry_slots, retry_dropped = pack(shrunk)
            if len(retry_dropped) < len(dropped):
                slots, dropped = retry_slots, retry_dropped
    return slots, rows, dropped


def _free_layout(spec, size):
    import math
    dims = SIZES[size]
    row_px = (dims["h"] - 2 * dims["padding"]) / dims["grid_rows"]
    reserved_top = math.ceil(38 / row_px) if spec.get("title") and size != "2x1" else 0
    slots, rows, dropped = _free_slots(spec["morphemes"], size, reserved_top)
    title_suppressed = False
    if dropped and reserved_top:
        # 内容优先于标题栏：省略标题栏能救回语素时就省略
        retry_slots, _, retry_dropped = _free_slots(spec["morphemes"], size, 0)
        if len(retry_dropped) < len(dropped):
            slots, dropped, title_suppressed = retry_slots, retry_dropped, True
    for slot in slots:
        slot.setdefault("compact", False)
        slot.update({"match": "FREE", "sourceSlot": None})
    rationale = ["无原型达到最低覆盖率；按 主视觉带→细节网格→底部操作条 层级式排布。"]
    if title_suppressed:
        rationale.append("空间不足，省略标题栏以保住内容语素。")
    if dropped:
        rationale.append("空间不足，按几何需求省略：" +
                         "、".join(str(m.get("label") or m["id"]) for m in dropped))
    return {"templateId": "free_" + size, "templateName": "层级式自由布局", "source": "Free composition v2",
            "mode": "FREE", "score": 0, "confidence": 0, "titleSuppressed": title_suppressed,
            "grid": {"columns": 12, "rows": rows, "gap": 1}, "slots": slots,
            "unplaced": [m["id"] for m in dropped], "rationale": rationale}


def _places_all_primaries(spec, assignment):
    """A template that cannot seat the PRIMARY/WARNING content is disqualified —
    a todo card must never drop its todo list to fit a prettier archetype."""
    for component_index, slot_index, _ in assignment:
        if slot_index < 0 and spec["morphemes"][component_index]["role"] in ("PRIMARY", "WARNING"):
            return False
    return True


def _apply_geometry_hints(result, size):
    """Shared geometry pass for BOTH template and free slots: a ring in a short
    slot degrades to a compact metric, cramped metrics/text get compact type
    scale — content adapts to the cell instead of overflowing it."""
    dims = SIZES[size]
    rows = result["grid"]["rows"]
    row_px = (dims["h"] - 2 * dims["padding"]) / rows
    for slot in result["slots"]:
        component = slot.get("component")
        if component is None:
            continue
        px = slot["rect"]["h"] * row_px
        if component["type"] == "PROGRESS" and px < 62:
            slot["renderAs"] = "METRIC"
        effective = slot.get("renderAs") or component["type"]
        if effective == "METRIC" and px < 48:
            slot["compact"] = True
        elif effective in ("STATUS", "TEXT") and px < 32:
            slot["compact"] = True
    return result


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
            # 分级处置：放不下的是用户要求的内容（高优先/主警示）才放弃模板；
            # 只是低优先补充项（联想/变体/SUPPORTING）则按预算省略，保住原型命中。
            by_id = {m["id"]: m for m in spec["morphemes"]}
            important = [uid for uid in unplaced
                         if by_id[uid]["priority"] >= 60
                         or by_id[uid]["role"] in ("PRIMARY", "WARNING")]
            if important:
                result = _free_layout(spec, size)
            else:
                result["rationale"].append(
                    "低优先补充项放不下，已省略：" +
                    "、".join(str(by_id[uid].get("label") or uid) for uid in unplaced))
    result["style"] = _style_block(style_id, domain, size)
    result["alternatives"] = [{"templateId": item[2]["id"], "name": item[2]["name"],
                               "score": item[0], "coverage": round(item[1], 2)} for item in ranked[:3]]
    return _apply_geometry_hints(result, size)


def render_spec(spec, layout):
    return {"version": "0.3", "title": spec.get("title"), "surface": spec["surface"],
            "template": layout["templateId"], "templateName": layout["templateName"],
            "layoutMode": layout["mode"], "grid": layout["grid"], "slots": layout["slots"],
            "style": layout["style"], "titleSuppressed": layout.get("titleSuppressed", False),
            "diagnostics": {"score": layout["score"], "confidence": layout["confidence"],
                            "source": layout.get("source"), "rationale": layout["rationale"],
                            "unplaced": layout["unplaced"], "alternatives": layout["alternatives"]}}
