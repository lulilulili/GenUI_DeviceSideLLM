"""MorphemeDraft v2: the model speaks semantics; code owns every UI decision.

v1 asked the model for {s,z,d,t,m[{k,r,l,q,f}]} — surface, size, density and the
component type k. v2 removes every field code can derive:

- s/z/d dropped: surface and size are request inputs, density comes from budget.
- k (component) dropped: derive.py maps (role, valueType, action-ness) to a
  component deterministically, which removes the whole "model picked SWITCH for
  a momentary action" error class and shortens both prompt and output.

The model now emits only: {"t": title, "m": [{"l","q","f","r"}]}.
Field rationale (see docs/V2-全端侧方案设计.md §5 for the full write-up):
  l  label   — user-language display words; the only free-text the model owns.
  q  key     — short english semantic key; the join point to the capability
               registry (aliases + token match), never executed directly.
  f  format  — value shape (NUMBER/PERCENTAGE/ENUM/BOOLEAN/...), drives both
               component derivation and data validation.
  r  role    — information hierarchy (PRIMARY/SECONDARY/.../PRIMARY_ACTION),
               drives priority, template slot matching and degradation order.
"""

FORMATS = ["STRING", "NUMBER", "BOOLEAN", "PERCENTAGE", "DURATION", "DATETIME", "ENUM", "LIST", "UNKNOWN"]
ROLES = ["PRIMARY", "SECONDARY", "SUPPORTING", "PRIMARY_ACTION", "SECONDARY_ACTION", "WARNING"]

# Per-size morpheme caps: stated in the prompt AND enforced by schema/budget, so
# the model never composes more than the card can hold (main template-miss cause).
SIZE_LIMITS = {"AUTO": 8, "2x1": 3, "2x2": 6, "3x2": 8, "3x3": 8}
SIZE_BUDGETS = {"AUTO": 12, "2x1": 3, "2x2": 8, "3x2": 11, "3x3": 14}
COMPONENT_COST = {"TEXT": 1, "METRIC": 1, "STATUS": 1, "PROGRESS": 2, "SWITCH": 1,
                  "SLIDER": 2, "BUTTON": 1, "LIST": 4}
ROLE_PRIORITY = {"WARNING": 100, "PRIMARY": 90, "PRIMARY_ACTION": 85,
                 "SECONDARY": 60, "SECONDARY_ACTION": 50, "SUPPORTING": 30}

SYSTEM_PROMPT = (
    "你是GenUI语素规划器。只输出一个单行JSON，不解释。\n"
    '格式：{"t":"卡片标题或null","m":[{"l":"标签","q":"english.semantic.key","f":"数据类型","r":"角色"}]}\n'
    "只抽取用户明确要求展示或操作的信息，每条一个语素；不编造数据、不合并不同数据、不添加未要求内容。\n"
    "f∈STRING|NUMBER|BOOLEAN|PERCENTAGE|DURATION|DATETIME|ENUM|LIST：数值=NUMBER；比例/电量/湿度=PERCENTAGE；"
    "状态=ENUM；开关=BOOLEAN；多条同类=LIST。\n"
    "r∈PRIMARY|SECONDARY|SUPPORTING|PRIMARY_ACTION|SECONDARY_ACTION|WARNING：核心信息恰好1个PRIMARY；"
    "可点击/可切换的操作用*_ACTION，最多2个；其余为SECONDARY或SUPPORTING。\n"
    "l用用户语言的简短词；q写简短英文语义键（如 phone.battery.level）。"
)

FEWSHOT = (
    "例：显示手机电量、网络状态和Wi-Fi开关=>"
    '{"t":"手机状态","m":['
    '{"l":"手机电量","q":"phone.battery.level","f":"PERCENTAGE","r":"PRIMARY"},'
    '{"l":"网络状态","q":"network.status","f":"ENUM","r":"SECONDARY"},'
    '{"l":"Wi-Fi","q":"wifi.power","f":"BOOLEAN","r":"PRIMARY_ACTION"}]}'
)

_SIZE_HINTS = {"AUTO": "按需求保留核心信息，最多8条", "2x1": "横条卡，最多3条：1个PRIMARY+至多1辅+至多1操作",
               "2x2": "方卡，最多6条", "3x2": "宽卡，最多8条", "3x3": "大卡，最多8条"}


def build_messages(text, card_size="AUTO", domain_hint=None, candidate_keys=()):
    """Small fixed prefix + dynamic tail keeps the KV cache reusable on device."""
    lines = [FEWSHOT, "卡片=" + card_size + "；" + _SIZE_HINTS[card_size]]
    if domain_hint:
        lines.append("领域=" + domain_hint)
    if candidate_keys:
        lines.append("已知语义键(可直接使用，也可自拟)=" + ",".join(sorted(candidate_keys)[:24]))
    lines.append("用户=" + text)
    return SYSTEM_PROMPT, "\n".join(lines)


def schema(card_size="AUTO"):
    return {
        "type": "object", "additionalProperties": False, "required": ["t", "m"],
        "properties": {
            "t": {"type": ["string", "null"]},
            "m": {"type": "array", "minItems": 1, "maxItems": SIZE_LIMITS[card_size],
                  "items": {"type": "object", "additionalProperties": False,
                            "required": ["l", "q", "f", "r"],
                            "properties": {"l": {"type": ["string", "null"]},
                                           "q": {"type": "string"},
                                           "f": {"enum": FORMATS},
                                           "r": {"enum": ROLES}}}},
        },
    }


def validate_draft(draft, card_size="AUTO"):
    errors = []
    if not isinstance(draft, dict):
        return ["根节点必须是object"]
    for key in ("t", "m"):
        if key not in draft:
            errors.append("缺少字段 " + key)
    items = draft.get("m")
    if not isinstance(items, list) or not 1 <= len(items) <= SIZE_LIMITS.get(card_size, 8):
        errors.append("m 必须包含1到%d项" % SIZE_LIMITS.get(card_size, 8))
        return errors
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append("m[%d] 必须是object" % index)
            continue
        for key in ("l", "q", "f", "r"):
            if key not in item:
                errors.append("m[%d] 缺少 %s" % (index, key))
        if item.get("f") not in FORMATS:
            errors.append("m[%d].f 不在枚举中" % index)
        if item.get("r") not in ROLES:
            errors.append("m[%d].r 不在枚举中" % index)
        if not isinstance(item.get("q"), str) or not item.get("q").strip():
            errors.append("m[%d].q 必须是非空字符串" % index)
    return errors


def normalize_draft(draft):
    """Deterministically repair role-count violations instead of failing.

    "恰好1个PRIMARY/最多2个ACTION" stays in the prompt as guidance, but a draft
    that violates it is fixable by code — burning an LLM retry (or the whole
    run) on it would be waste. Extra PRIMARYs demote to SECONDARY, extra
    actions demote to SUPPORTING, a missing PRIMARY promotes the best info
    item. Corrections are reported so the UI can show what happened.
    """
    items = draft["m"]
    corrections = []
    action_indexes = [i for i, item in enumerate(items) if "ACTION" in str(item.get("r", ""))]
    for index in action_indexes[2:]:
        corrections.append({"index": index, "label": items[index].get("l"),
                            "from": items[index]["r"], "to": "SUPPORTING", "reason": "ACTION_LIMIT"})
        items[index]["r"] = "SUPPORTING"
    primary_indexes = [i for i, item in enumerate(items) if item.get("r") == "PRIMARY"]
    if len(primary_indexes) > 1:
        for index in primary_indexes[1:]:
            corrections.append({"index": index, "label": items[index].get("l"),
                                "from": "PRIMARY", "to": "SECONDARY", "reason": "MULTI_PRIMARY"})
            items[index]["r"] = "SECONDARY"
    elif not primary_indexes:
        candidate = next((i for i, item in enumerate(items) if item.get("r") == "SECONDARY"),
                         next((i for i, item in enumerate(items)
                               if "ACTION" not in str(item.get("r", ""))), 0))
        corrections.append({"index": candidate, "label": items[candidate].get("l"),
                            "from": items[candidate]["r"], "to": "PRIMARY", "reason": "NO_PRIMARY"})
        items[candidate]["r"] = "PRIMARY"
    return draft, corrections


def expand_draft(draft, card_size="AUTO"):
    """Deterministic expansion; component type is intentionally absent here —
    derive.py adds it after capability binding."""
    morphemes = []
    for index, item in enumerate(draft["m"]):
        role = item["r"]
        morphemes.append({
            "id": "m%d" % (index + 1), "role": role,
            "priority": ROLE_PRIORITY[role],
            "label": item["l"], "semanticKey": item["q"].strip(),
            "valueType": item["f"], "content": {},
            "presentation": {"emphasis": "HIGH" if role in ("PRIMARY", "WARNING") else "NORMAL"},
        })
    return {"version": "0.3", "scene": "generated_ui",
            "surface": {"type": "CARD", "size": card_size, "density": "AUTO"},
            "title": draft.get("t"), "morphemes": morphemes}


def resolve_auto_size(spec):
    """Cost-based AUTO sizing (runs after component derivation, so LIST/PROGRESS
    weigh more and a todo-list card never squeezes into a 2x1 bar)."""
    cost = sum(COMPONENT_COST.get(item.get("type", "TEXT"), 1) for item in spec["morphemes"])
    if cost <= SIZE_BUDGETS["2x1"] and not any(item.get("type") == "LIST" for item in spec["morphemes"]):
        return "2x1"
    if cost <= SIZE_BUDGETS["2x2"]:
        return "2x2"
    if cost <= SIZE_BUDGETS["3x2"]:
        return "3x2"
    return "3x3"


def apply_information_budget(spec, card_size):
    """Priority-ordered keep list under the per-size cost budget (degradation)."""
    budget, used, kept, dropped = SIZE_BUDGETS[card_size], 0, [], []
    ordered = sorted(enumerate(spec["morphemes"]), key=lambda pair: (-pair[1]["priority"], pair[0]))
    for _, item in ordered:
        cost = COMPONENT_COST.get(item.get("type", "TEXT"), 1)
        if used + cost <= budget or not kept:
            kept.append(item)
            used += cost
        else:
            dropped.append({"id": item["id"], "label": item["label"], "cost": cost, "reason": "CARD_BUDGET"})
    keep_ids = {item["id"] for item in kept}
    spec["morphemes"] = [item for item in spec["morphemes"] if item["id"] in keep_ids]
    spec["surface"]["size"] = card_size
    return spec, {"size": card_size, "capacity": budget, "used": used, "dropped": dropped}
