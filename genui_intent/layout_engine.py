"""Deterministic, template-driven GenUI layout engine.

Templates use a normalized 12-column grid.  They describe spatial tendencies,
not hard component identities: compatible components with similar footprints
may replace one another.  Unmatched items use remaining whitespace before the
engine falls back to a free layout.
"""
from functools import lru_cache
from hashlib import blake2b


FAMILY = {
    "TEXT": "TEXT", "STATUS": "TEXT", "METRIC": "METRIC",
    "PROGRESS": "METRIC", "BUTTON": "ACTION", "SWITCH": "ACTION",
    "SLIDER": "ACTION", "LIST": "COLLECTION", "IMAGE": "MEDIA", "ICON": "MEDIA",
}
FOOTPRINT = {
    "TEXT": "S", "STATUS": "S", "METRIC": "S", "BUTTON": "S", "SWITCH": "S",
    "PROGRESS": "M", "SLIDER": "M", "LIST": "L", "IMAGE": "L", "ICON": "S",
}
DEFAULT_SPAN = {"S": (4, 2), "M": (5, 4), "L": (6, 6)}
DIVERSITY_SCORE_BAND = 18


def slot(slot_id, x, y, w, h, accepts, preferred=(), roles=(), required=False,
         prominence=1.0, placeholder=None):
    return {"id": slot_id, "rect": {"x": x, "y": y, "w": w, "h": h},
            "accepts": list(accepts), "preferred": list(preferred), "roles": list(roles),
            "required": required, "prominence": prominence, "placeholder": placeholder}


TEMPLATES = [
    # PDF page 1, first-row 2x1 archetypes.
    {"id": "2x1_title_action", "name": "标题 + 右侧动作", "size": "2x1", "rows": 6, "source": "PDF P1-R1-01", "slots": [
        slot("main", 0, 0, 9, 6, ("TEXT", "METRIC"), ("TEXT", "STATUS"), ("PRIMARY",), True, 1.2),
        slot("action", 9, 1, 3, 4, ("ACTION", "MEDIA"), ("BUTTON", "SWITCH", "ICON"), ("PRIMARY_ACTION", "SECONDARY_ACTION"), False, .9, "ICON") ]},
    {"id": "2x1_title_support_action", "name": "主副信息 + 动作", "size": "2x1", "rows": 6, "source": "PDF P1-R1-02", "slots": [
        slot("primary", 0, 0, 9, 3, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.2),
        slot("secondary", 0, 3, 9, 3, ("TEXT", "METRIC"), (), ("SECONDARY", "SUPPORTING"), False, .7),
        slot("action", 9, 1, 3, 4, ("ACTION", "MEDIA"), (), ("PRIMARY_ACTION", "SECONDARY_ACTION"), False, .9, "ICON") ]},
    {"id": "2x1_metric_action", "name": "焦点数字 + 图标", "size": "2x1", "rows": 6, "source": "PDF P1-R1-03", "slots": [
        slot("metric", 0, 0, 9, 6, ("METRIC",), ("METRIC", "PROGRESS"), ("PRIMARY",), True, 1.5),
        slot("action", 9, 1, 3, 4, ("ACTION", "MEDIA"), (), ("PRIMARY_ACTION",), False, .9, "ICON") ]},
    {"id": "2x1_status_metric", "name": "状态 + 数值 + 图标", "size": "2x1", "rows": 6, "source": "PDF P1-R1-04", "slots": [
        slot("status", 0, 0, 8, 2, ("TEXT",), ("STATUS",), ("SECONDARY",), False, .7),
        slot("metric", 0, 2, 8, 4, ("METRIC",), (), ("PRIMARY",), True, 1.4),
        slot("action", 9, 1, 3, 4, ("ACTION", "MEDIA"), (), ("PRIMARY_ACTION",), False, .9, "ICON") ]},

    # PDF page 2, first-row 2x2 archetypes.
    {"id": "2x2_corner_pair", "name": "对角主副信息", "size": "2x2", "rows": 12, "source": "PDF P2-R1-01", "slots": [
        slot("primary", 0, 0, 9, 5, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.3), slot("top_action", 9, 0, 3, 3, ("ACTION", "MEDIA"), (), (), False, .6, "ICON"),
        slot("secondary", 0, 8, 9, 4, ("TEXT", "METRIC"), (), ("SECONDARY", "SUPPORTING"), False, .7), slot("bottom_action", 9, 9, 3, 3, ("ACTION", "MEDIA"), (), (), False, .6, "ICON") ]},
    {"id": "2x2_text_stack", "name": "标题 + 正文", "size": "2x2", "rows": 12, "source": "PDF P2-R1-02", "slots": [
        slot("title", 0, 0, 9, 3, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.1), slot("icon", 9, 0, 3, 3, ("MEDIA", "ACTION"), (), (), False, .5, "ICON"),
        slot("body", 0, 4, 12, 8, ("TEXT", "COLLECTION"), ("TEXT", "LIST"), ("SECONDARY", "SUPPORTING"), True, .9) ]},
    {"id": "2x2_media_focus", "name": "标题 + 大图占位", "size": "2x2", "rows": 12, "source": "PDF P2-R1-03", "slots": [
        slot("title", 0, 0, 9, 3, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.0), slot("icon", 9, 0, 3, 3, ("MEDIA", "ACTION"), (), (), False, .5, "ICON"),
        slot("media", 0, 4, 9, 8, ("MEDIA", "COLLECTION", "TEXT"), (), (), False, 1.0, "IMAGE"), slot("action", 9, 8, 3, 4, ("ACTION",), (), (), False, .7) ]},
    {"id": "2x2_action_footer", "name": "内容 + 底部按钮", "size": "2x2", "rows": 12, "source": "PDF P2-R1-04", "slots": [
        slot("primary", 0, 0, 12, 4, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.1), slot("secondary", 0, 4, 12, 3, ("TEXT", "METRIC"), (), ("SECONDARY",), False, .7),
        slot("action", 0, 8, 12, 4, ("ACTION",), ("BUTTON",), ("PRIMARY_ACTION",), True, 1.0) ]},
    {"id": "2x2_list", "name": "标题 + 紧凑列表", "size": "2x2", "rows": 12, "source": "PDF P2-R1-05", "slots": [
        slot("title", 0, 0, 9, 3, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.0), slot("icon", 9, 0, 3, 3, ("MEDIA", "ACTION"), (), (), False, .5, "ICON"),
        slot("list", 0, 3, 12, 9, ("COLLECTION", "TEXT"), ("LIST",), (), True, 1.1) ]},
    {"id": "2x2_gauge_action", "name": "环形指标 + 操作", "size": "2x2", "rows": 12, "source": "PDF P2-R1-06", "slots": [
        slot("gauge", 0, 0, 7, 7, ("METRIC",), ("PROGRESS",), ("PRIMARY",), True, 1.5), slot("status", 7, 0, 5, 7, ("TEXT", "METRIC"), (), ("SECONDARY",), False, .7),
        slot("action", 0, 8, 12, 4, ("ACTION",), (), ("PRIMARY_ACTION",), False, 1.0) ]},
    {"id": "2x2_metric_details", "name": "大数字 + 详情", "size": "2x2", "rows": 12, "source": "PDF P2-R1-07", "slots": [
        slot("metric", 0, 0, 8, 6, ("METRIC",), (), ("PRIMARY",), True, 1.5), slot("badge", 9, 0, 3, 3, ("MEDIA", "ACTION", "TEXT"), (), (), False, .5, "ICON"),
        slot("details", 0, 7, 12, 5, ("TEXT", "COLLECTION", "METRIC"), (), ("SECONDARY", "SUPPORTING"), False, .8) ]},
    {"id": "2x2_shortcuts", "name": "四宫格操作", "size": "2x2", "rows": 12, "source": "PDF P2-R1-09", "slots": [
        slot("a1", 0, 0, 6, 6, ("ACTION", "TEXT"), (), ("PRIMARY_ACTION",), True, 1.0), slot("a2", 6, 0, 6, 6, ("ACTION", "TEXT"), (), (), False, .9),
        slot("a3", 0, 6, 6, 6, ("ACTION", "TEXT"), (), (), False, .9), slot("a4", 6, 6, 6, 6, ("ACTION", "TEXT"), (), (), False, .9) ]},
    {"id": "2x2_dual_rows", "name": "标题 + 双行内容", "size": "2x2", "rows": 12, "source": "PDF P2-R1-11", "slots": [
        slot("title", 0, 0, 9, 3, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.0), slot("icon", 9, 0, 3, 3, ("MEDIA", "ACTION"), (), (), False, .5, "ICON"),
        slot("row1", 0, 4, 12, 3, ("TEXT", "METRIC", "ACTION"), (), (), False, .8), slot("row2", 0, 8, 12, 3, ("TEXT", "METRIC", "ACTION"), (), (), False, .8) ]},

    # PDF page 3, first-row 3x2 wide archetypes.
    {"id": "3x2_service_strip", "name": "服务标题 + 快捷操作带", "size": "3x2", "rows": 8, "source": "PDF P3-R1-01", "slots": [
        slot("title", 0, 0, 8, 3, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.1), slot("action", 9, 0, 3, 3, ("ACTION",), (), (), False, .7),
        slot("shortcut1", 0, 4, 3, 4, ("ACTION", "TEXT"), (), (), False, .7), slot("shortcut2", 3, 4, 3, 4, ("ACTION", "TEXT"), (), (), False, .7), slot("shortcut3", 6, 4, 3, 4, ("ACTION", "TEXT"), (), (), False, .7), slot("shortcut4", 9, 4, 3, 4, ("ACTION", "TEXT"), (), (), False, .7) ]},
    {"id": "3x2_search_shortcuts", "name": "搜索 + 四项快捷入口", "size": "3x2", "rows": 8, "source": "PDF P3-R1-02", "slots": [
        slot("search", 0, 0, 12, 3, ("TEXT", "ACTION"), (), ("PRIMARY",), True, 1.0), slot("s1", 0, 4, 3, 4, ("ACTION",), (), (), False, .7), slot("s2", 3, 4, 3, 4, ("ACTION",), (), (), False, .7), slot("s3", 6, 4, 3, 4, ("ACTION",), (), (), False, .7), slot("s4", 9, 4, 3, 4, ("ACTION",), (), (), False, .7) ]},
    {"id": "3x2_content_actions", "name": "主内容 + 操作组", "size": "3x2", "rows": 8, "source": "PDF P3-R1-03", "slots": [
        slot("title", 0, 0, 9, 2, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.1), slot("action", 9, 0, 3, 2, ("ACTION",), (), (), False, .7), slot("body", 0, 2, 8, 6, ("TEXT", "COLLECTION"), (), (), False, .9), slot("side1", 8, 3, 2, 3, ("ACTION", "MEDIA"), (), (), False, .6, "ICON"), slot("side2", 10, 3, 2, 3, ("ACTION", "MEDIA"), (), (), False, .6, "ICON") ]},
    {"id": "3x2_media_shortcuts", "name": "媒体标题 + 快捷操作", "size": "3x2", "rows": 8, "source": "PDF P3-R1-04", "slots": [
        slot("media", 0, 0, 3, 4, ("MEDIA",), (), (), False, 1.0, "IMAGE"), slot("title", 3, 0, 6, 4, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.1), slot("controls", 9, 0, 3, 4, ("ACTION",), (), (), False, .8), slot("s1", 0, 4, 3, 4, ("ACTION", "TEXT"), (), (), False, .6), slot("s2", 3, 4, 3, 4, ("ACTION", "TEXT"), (), (), False, .6), slot("s3", 6, 4, 3, 4, ("ACTION", "TEXT"), (), (), False, .6), slot("s4", 9, 4, 3, 4, ("ACTION", "TEXT"), (), (), False, .6) ]},
    {"id": "3x2_metric_chart", "name": "指标 + 横向图表", "size": "3x2", "rows": 8, "source": "PDF P3-R1-05", "slots": [
        slot("metric", 0, 0, 5, 3, ("METRIC",), (), ("PRIMARY",), True, 1.4), slot("support", 5, 0, 7, 3, ("TEXT", "METRIC"), (), (), False, .7), slot("chart", 0, 3, 12, 5, ("COLLECTION", "METRIC", "MEDIA"), (), (), False, 1.0, "CHART") ]},
    {"id": "3x2_list_rows", "name": "标题 + 横向列表", "size": "3x2", "rows": 8, "source": "PDF P3-R1-06", "slots": [
        slot("title", 0, 0, 12, 2, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.0), slot("list", 0, 2, 12, 6, ("COLLECTION", "TEXT"), ("LIST",), (), True, 1.2) ]},
    {"id": "3x2_media_story", "name": "左侧媒体 + 右侧叙事", "size": "3x2", "rows": 8, "source": "PDF P3-R1-07", "slots": [
        slot("media", 0, 0, 5, 8, ("MEDIA",), (), (), False, 1.2, "IMAGE"), slot("title", 5, 0, 6, 3, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.1), slot("icon", 11, 0, 1, 2, ("MEDIA", "ACTION"), (), (), False, .4, "ICON"), slot("body", 5, 3, 7, 3, ("TEXT", "COLLECTION"), (), (), False, .8), slot("action", 10, 6, 2, 2, ("ACTION",), (), (), False, .6) ]},

    # PDF page 4 large-square archetypes, adapted to this demo's 3x3 size.
    {"id": "3x3_editorial", "name": "大留白正文", "size": "3x3", "rows": 12, "source": "PDF P4-R1-01", "slots": [
        slot("title", 0, 0, 12, 3, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.1), slot("body", 0, 6, 12, 6, ("TEXT", "COLLECTION"), (), ("SECONDARY", "SUPPORTING"), True, .9) ]},
    {"id": "3x3_media_list", "name": "媒体头图 + 列表", "size": "3x3", "rows": 12, "source": "PDF P4-R1-02", "slots": [
        slot("media", 0, 0, 5, 5, ("MEDIA",), (), (), False, 1.0, "IMAGE"), slot("title", 5, 0, 7, 5, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.1),
        slot("list", 0, 5, 12, 7, ("COLLECTION", "TEXT"), ("LIST",), (), True, 1.2) ]},
    {"id": "3x3_chart_focus", "name": "指标 + 大图表", "size": "3x3", "rows": 12, "source": "PDF P4-R1-03", "slots": [
        slot("metric", 0, 0, 7, 4, ("METRIC",), (), ("PRIMARY",), True, 1.5), slot("support", 7, 0, 5, 4, ("TEXT", "METRIC"), (), ("SECONDARY",), False, .7),
        slot("chart", 0, 4, 12, 8, ("MEDIA", "COLLECTION", "METRIC"), (), (), False, 1.0, "CHART") ]},
    {"id": "3x3_list_stack", "name": "标题 + 多行列表", "size": "3x3", "rows": 12, "source": "PDF P4-R1-04", "slots": [
        slot("title", 0, 0, 12, 2, ("TEXT", "METRIC"), (), ("PRIMARY",), True, 1.0), slot("list", 0, 2, 12, 10, ("COLLECTION", "TEXT"), ("LIST",), (), True, 1.2) ]},
    {"id": "3x3_dashboard", "name": "焦点指标 + 信息网格", "size": "3x3", "rows": 12, "source": "PDF P4 weather/calendar examples", "slots": [
        slot("hero", 0, 0, 6, 5, ("METRIC", "TEXT"), (), ("PRIMARY",), True, 1.5), slot("status", 6, 0, 6, 5, ("TEXT", "METRIC"), (), ("SECONDARY",), False, .8),
        slot("detail1", 0, 5, 4, 3, ("METRIC", "TEXT", "ACTION"), (), (), False, .7), slot("detail2", 4, 5, 4, 3, ("METRIC", "TEXT", "ACTION"), (), (), False, .7), slot("detail3", 8, 5, 4, 3, ("METRIC", "TEXT", "ACTION"), (), (), False, .7),
        slot("footer", 0, 9, 12, 3, ("COLLECTION", "TEXT", "ACTION", "METRIC"), (), (), False, .8) ]},
]


STYLE_PRESETS = {
    "neutral": {"label": "中性服务", "cardBg": "#f8fbff", "cardFg": "#18283b", "accent": "#1767e8", "muted": "#edf3fa", "radius": 20, "font": "system"},
    "vivid": {"label": "鲜明渐变", "cardBg": "#1767e8", "cardFg": "#ffffff", "accent": "#65e2c2", "muted": "#ffffff1f", "radius": 22, "font": "system"},
    "soft": {"label": "柔和信息", "cardBg": "#f3f0ff", "cardFg": "#28223c", "accent": "#7b58d6", "muted": "#ffffffa8", "radius": 24, "font": "system"},
    "editorial": {"label": "编辑阅读", "cardBg": "#fff7dc", "cardFg": "#302a1d", "accent": "#ee6b38", "muted": "#fffdf5", "radius": 14, "font": "serif"},
}


def _pair_score(component, target):
    kind, family = component["type"], FAMILY.get(component["type"], "TEXT")
    if kind in target["preferred"]:
        score, quality = 46, "EXACT"
    elif family in target["accepts"]:
        score, quality = 30, "FAMILY"
    else:
        slot_footprints = {FOOTPRINT.get(t, "S") for t in target["preferred"] if t in FOOTPRINT}
        if slot_footprints and FOOTPRINT.get(kind, "S") in slot_footprints:
            score, quality = 12, "FOOTPRINT"
        else:
            return -1000, "INCOMPATIBLE"
    if component["role"] in target["roles"]:
        score += 16
    if component["role"] == "PRIMARY" and target["prominence"] >= 1.2:
        score += 12
    score += round(component.get("priority", 50) / 20 * target["prominence"])
    return score, quality


def _best_assignment(components, slots):
    ordered = sorted(range(len(components)), key=lambda i: (-components[i].get("priority", 0), i))

    @lru_cache(None)
    def visit(position, used_mask):
        if position == len(ordered):
            penalty = sum(18 for i, s in enumerate(slots) if s["required"] and not used_mask & (1 << i))
            return -penalty, ()
        component_index = ordered[position]
        component = components[component_index]
        best_score, best_pairs = -round(component.get("priority", 50) / 5), ((component_index, -1, "UNMATCHED"),)
        tail_score, tail_pairs = visit(position + 1, used_mask)
        best_score += tail_score
        best_pairs += tail_pairs
        for slot_index, target in enumerate(slots):
            if used_mask & (1 << slot_index):
                continue
            score, quality = _pair_score(component, target)
            if score < 0:
                continue
            tail_score, tail_pairs = visit(position + 1, used_mask | (1 << slot_index))
            if score + tail_score > best_score:
                best_score = score + tail_score
                best_pairs = ((component_index, slot_index, quality),) + tail_pairs
        return best_score, best_pairs

    return visit(0, 0)


def _overlaps(rect, occupied):
    return any(not (rect["x"] + rect["w"] <= r["x"] or r["x"] + r["w"] <= rect["x"] or
                       rect["y"] + rect["h"] <= r["y"] or r["y"] + r["h"] <= rect["y"]) for r in occupied)


def _place_in_whitespace(component, rows, occupied):
    w, h = DEFAULT_SPAN[FOOTPRINT.get(component["type"], "S")]
    for y in range(0, rows - h + 1):
        for x in range(0, 12 - w + 1):
            rect = {"x": x, "y": y, "w": w, "h": h}
            if not _overlaps(rect, occupied):
                return rect
    return None


def _free_layout(spec, size):
    columns = 2 if size in ("2x1", "2x2") else 3
    cell_w, slots = 12 // columns, []
    for index, component in enumerate(sorted(spec["morphemes"], key=lambda x: -x["priority"])):
        x, y = (index % columns) * cell_w, (index // columns) * 3
        slots.append({"id": "free_" + str(index + 1), "rect": {"x": x, "y": y, "w": cell_w, "h": 3},
                      "component": component, "match": "FREE", "sourceSlot": None})
    rows = max(6, ((len(slots) + columns - 1) // columns) * 3)
    return {"templateId": "free_" + size, "templateName": "自由布局", "source": "Fallback",
            "mode": "FREE", "score": 0, "confidence": 0, "grid": {"columns": 12, "rows": rows, "gap": 1},
            "slots": slots, "unplaced": [], "rationale": ["没有设计模板达到最低匹配覆盖率，使用确定性自由网格。"]}


def _select_near_optimal(ranked, spec):
    """Spread semantically different inputs across equally good layouts without randomness."""
    top_score, top_coverage = ranked[0][0], ranked[0][1]
    eligible = [item for item in ranked
                if item[0] >= top_score - DIVERSITY_SCORE_BAND and item[1] == top_coverage]
    if len(eligible) == 1:
        return eligible[0], eligible
    signature = "|".join([str(spec.get("title") or ""),
                          *[item.get("semanticKey", "") for item in spec["morphemes"]]])
    selected = max(eligible, key=lambda item: blake2b(
        (signature + "|" + item[2]["id"]).encode("utf-8"), digest_size=8).digest())
    return selected, eligible


def plan(spec, style_id="neutral"):
    size = spec["surface"].get("size", "AUTO")
    if size == "AUTO":
        size = "2x1" if len(spec["morphemes"]) <= 2 else "2x2" if len(spec["morphemes"]) <= 5 else "3x3"
        spec["surface"]["size"] = size
    candidates = [template for template in TEMPLATES if template["size"] == size]
    ranked = []
    for template in candidates:
        score, assignment = _best_assignment(spec["morphemes"], template["slots"])
        matched = sum(slot_index >= 0 for _, slot_index, _ in assignment)
        coverage = matched / max(1, len(spec["morphemes"]))
        ranked.append((score + round(coverage * 25), coverage, template, assignment))
    ranked.sort(key=lambda item: (-item[0], item[2]["id"]))
    if not ranked or ranked[0][1] < .5:
        result = _free_layout(spec, size)
    else:
        selected, diversity_candidates = _select_near_optimal(ranked, spec)
        score, coverage, template, assignment = selected
        slots, occupied, unmatched = [], [], []
        for component_index, slot_index, quality in assignment:
            if slot_index < 0:
                unmatched.append(spec["morphemes"][component_index])
                continue
            target = template["slots"][slot_index]
            occupied.append(target["rect"])
            slots.append({"id": target["id"], "rect": target["rect"], "component": spec["morphemes"][component_index],
                          "match": quality, "sourceSlot": target["id"]})
        added, unplaced = [], []
        for component in unmatched:
            rect = _place_in_whitespace(component, template["rows"], occupied)
            if rect:
                occupied.append(rect)
                item = {"id": "extra_" + component["id"], "rect": rect, "component": component,
                        "match": "WHITESPACE", "sourceSlot": None}
                slots.append(item); added.append(component["id"])
            else:
                unplaced.append(component["id"])
        for target in template["slots"]:
            if (target["placeholder"] and not any(item["sourceSlot"] == target["id"] for item in slots)
                    and not _overlaps(target["rect"], occupied)):
                slots.append({"id": target["id"], "rect": target["rect"], "component": None,
                              "placeholder": target["placeholder"], "match": "PLACEHOLDER", "sourceSlot": target["id"]})
        mode = "TEMPLATE_EXTENDED" if added else "TEMPLATE"
        result = {"templateId": template["id"], "templateName": template["name"], "source": template["source"],
                  "mode": mode, "score": score, "confidence": round(coverage, 2),
                  "grid": {"columns": 12, "rows": template["rows"], "gap": 1}, "slots": slots,
                  "unplaced": unplaced, "rationale": [f"覆盖 {matched}/{len(spec['morphemes'])} 个语素。", f"模板来源：{template['source']}。",
                  f"近优候选 {len(diversity_candidates)} 个；使用语义签名稳定选型。"] + (["额外语素已放入模板留白。"] if added else [])}
        if unplaced and coverage < .75:
            result = _free_layout(spec, size)
    style = STYLE_PRESETS.get(style_id, STYLE_PRESETS["neutral"])
    result["style"] = {"preset": style_id if style_id in STYLE_PRESETS else "neutral", "tokens": style,
                       "componentVariants": {"TEXT": "body", "METRIC": "hero-number", "STATUS": "badge",
                                             "PROGRESS": "ring", "BUTTON": "pill", "SWITCH": "compact",
                                             "SLIDER": "track", "LIST": "rows"}}
    result["selectionPolicy"] = {"name": "NEAR_OPTIMAL_SEMANTIC_HASH", "scoreBand": DIVERSITY_SCORE_BAND,
                                 "deterministic": True}
    result["alternatives"] = [{"templateId": item[2]["id"], "name": item[2]["name"], "score": item[0], "coverage": round(item[1], 2)} for item in ranked[:3]]
    return result


def render_spec(spec, layout):
    return {"version": "0.2", "title": spec.get("title"), "surface": spec["surface"],
            "template": layout["templateId"], "templateName": layout["templateName"],
            "layoutMode": layout["mode"], "grid": layout["grid"], "slots": layout["slots"],
            "style": layout["style"], "diagnostics": {"score": layout["score"], "confidence": layout["confidence"],
            "source": layout["source"], "rationale": layout["rationale"], "unplaced": layout["unplaced"],
            "alternatives": layout["alternatives"]}}
