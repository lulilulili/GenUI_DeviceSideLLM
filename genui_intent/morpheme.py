"""Compact model-facing MorphemeDraft and deterministic expansion."""
import copy
from html import escape


MORPHEME_SYSTEM_PROMPT = """你是GenUI语素规划器。只输出符合Schema的单行JSON，不解释。
把用户明确需要的内容逐项转成UI语素，不输出HTML、CSS、坐标或真实API，不添加用户未要求的内容。
PROGRESS=比例/进度；METRIC=突出数值；STATUS=只读状态；SWITCH=用户可切换的开关；SLIDER=连续调节；BUTTON=触发动作；LIST=多条同类内容；TEXT=文字。
数量/计数=METRIC+NUMBER；状态=STATUS+ENUM；添加/删除/打开/拨打等瞬时动作=BUTTON；只有可保持开关状态的能力才用SWITCH；多条同类实体=LIST+LIST。
PRIMARY=核心信息，PRIMARY_ACTION=主要操作。标题和标签使用用户的语言；q写简短英文语义key。f是数据类型：气温/数值=NUMBER，湿度/电量/比例=PERCENTAGE，天气/连接状态=ENUM，开关=BOOLEAN。不同数据不得合并在同一语素，空间不足时省略低优先级数据。"""
MORPHEME_SYSTEM_PROMPT += '\n例：显示手机电量、网络状态和Wi-Fi开关=>{"s":"CARD","z":"AUTO","d":"AUTO","t":"手机状态","m":[{"k":"PROGRESS","r":"PRIMARY","l":"手机电量","q":"phone.battery","f":"PERCENTAGE"},{"k":"STATUS","r":"SECONDARY","l":"网络状态","q":"network.status","f":"ENUM"},{"k":"SWITCH","r":"PRIMARY_ACTION","l":"Wi-Fi","q":"wifi.power","f":"BOOLEAN"}]}'

TYPES = ["TEXT", "METRIC", "STATUS", "PROGRESS", "SWITCH", "SLIDER", "BUTTON", "LIST"]
ROLES = ["PRIMARY", "SECONDARY", "SUPPORTING", "PRIMARY_ACTION", "SECONDARY_ACTION", "WARNING"]
FORMATS = ["STRING", "NUMBER", "BOOLEAN", "PERCENTAGE", "DURATION", "DATETIME", "ENUM", "LIST", "UNKNOWN"]


SIZE_LIMITS = {"AUTO": 8, "2x1": 3, "2x2": 6, "3x2": 8, "3x3": 8}
SIZE_BUDGETS = {"AUTO": 12, "2x1": 3, "2x2": 8, "3x2": 11, "3x3": 14}
COMPONENT_COST = {"TEXT": 1, "METRIC": 1, "STATUS": 1, "PROGRESS": 2, "SWITCH": 1, "SLIDER": 2, "BUTTON": 1, "LIST": 4}


def morpheme_schema(card_size="AUTO"):
    nullable_string = {"type": ["string", "null"]}
    return {
        "type": "object", "additionalProperties": False,
        "required": ["s", "z", "d", "t", "m"],
        "properties": {
            "s": {"enum": ["CARD", "PAGE"]},
            "z": {"enum": [card_size] if card_size != "AUTO" else ["AUTO", "2x1", "2x2", "3x2", "3x3"]},
            "d": {"enum": ["AUTO", "COMPACT", "COMFORTABLE", "DETAILED"]},
            "t": nullable_string,
            "m": {"type": "array", "minItems": 1, "maxItems": SIZE_LIMITS[card_size], "items": {"$ref": "#/$defs/morpheme"}},
        },
        "$defs": {"morpheme": {
            "type": "object", "additionalProperties": False,
            "required": ["k", "r", "l", "q", "f"],
            "properties": {
                "k": {"enum": TYPES}, "r": {"enum": ROLES},
                "l": nullable_string, "q": {"type": "string"}, "f": {"enum": FORMATS},
            },
        }},
    }


def build_morpheme_prompt(text, card_size="AUTO"):
    limits = {"AUTO": "按需求保留核心信息", "2x1": "预算3，最多3个轻量语素", "2x2": "预算8，最多6项", "3x2": "预算11，最多8项", "3x3": "预算14，最多8项完整信息"}
    return f"卡片={card_size}；信息预算={limits[card_size]}\n用户={text}"


SEMANTIC_REVIEW_SYSTEM_PROMPT = """你是GenUI语义审校器。只输出符合Schema的单行JSON，不解释。
依据原用户需求审查Draft：删除用户未要求或无法推断的内容；不新增需求；修正组件和数据类型。
数量=METRIC+NUMBER；比例=PROGRESS+PERCENTAGE；状态=STATUS+ENUM；瞬时动作=BUTTON+UNKNOWN；持久开关=SWITCH+BOOLEAN；多条同类实体=LIST+LIST。保留卡片尺寸。"""


def build_semantic_review_prompt(user_text, draft):
    import json
    return "用户=" + user_text + "\nDraft=" + json.dumps(draft, ensure_ascii=False, separators=(",", ":"))


DEFAULT_PRIORITY = {
    "WARNING": 100, "PRIMARY": 90, "PRIMARY_ACTION": 85,
    "SECONDARY": 60, "SECONDARY_ACTION": 50, "SUPPORTING": 30,
}


def validate_draft(draft, card_size="AUTO"):
    errors = []
    if not isinstance(draft, dict):
        return ["根节点必须是object"]
    for key in ("s", "z", "d", "t", "m"):
        if key not in draft:
            errors.append("缺少字段 " + key)
    if draft.get("s") not in ("CARD", "PAGE"):
        errors.append("s 不在枚举中")
    allowed_sizes = (card_size,) if card_size != "AUTO" else ("AUTO", "2x1", "2x2", "3x2", "3x3")
    if draft.get("z") not in allowed_sizes:
        errors.append("z 与请求尺寸不一致")
    if draft.get("d") not in ("AUTO", "COMPACT", "COMFORTABLE", "DETAILED"):
        errors.append("d 不在枚举中")
    items = draft.get("m")
    if not isinstance(items, list) or not 1 <= len(items) <= SIZE_LIMITS[card_size]:
        errors.append(f"m 必须包含1到{SIZE_LIMITS[card_size]}项")
        return errors
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"m[{index}] 必须是object")
            continue
        missing = [key for key in ("k", "r", "l", "q", "f") if key not in item]
        if missing:
            errors.append(f"m[{index}] 缺少 " + ",".join(missing))
        if item.get("k") not in TYPES:
            errors.append(f"m[{index}].k 不在枚举中")
        if item.get("r") not in ROLES:
            errors.append(f"m[{index}].r 不在枚举中")
        if item.get("f") not in FORMATS:
            errors.append(f"m[{index}].f 不在枚举中")
    return errors


def expand_draft(draft):
    morphemes = []
    for index, item in enumerate(draft["m"]):
        kind, role = item["k"], item["r"]
        morphemes.append({
            "id": f"m{index + 1}", "type": kind, "role": role,
            "priority": DEFAULT_PRIORITY[role], "label": item["l"],
            "semanticKey": item["q"], "valueType": item["f"],
            "actionKey": item["q"] + ".set" if kind in ("SWITCH", "SLIDER") else item["q"] + ".trigger" if kind == "BUTTON" else None,
            "content": {},
            "presentation": {"emphasis": "HIGH" if role in ("PRIMARY", "WARNING") else "NORMAL"},
        })
    return {
        "version": "0.1", "scene": "generated_ui",
        "surface": {"type": draft["s"], "size": draft["z"], "density": draft["d"]},
        "title": draft["t"], "morphemes": morphemes,
    }


def reconcile_types(spec):
    """Correct high-confidence type/component mismatches without domain-specific routing."""
    corrections = []
    expanded = []
    for item in spec["morphemes"]:
        keys = [part.strip() for part in item["semanticKey"].split(",") if part.strip()]
        if len(keys) == 1:
            expanded.append(item)
            continue
        label_map = {"temperature": "气温", "humidity": "湿度", "battery": "电量", "condition": "天气"}
        for index, key in enumerate(keys, 1):
            child = copy.deepcopy(item)
            child["id"] = item["id"] + "_" + str(index)
            child["semanticKey"] = key
            child["label"] = next((label for token, label in label_map.items() if token in key.lower()), item["label"])
            expanded.append(child)
        corrections.append({"id": item["id"], "reason": "SPLIT_COMPOSITE_SEMANTIC_KEY", "into": [item["id"] + "_" + str(i) for i in range(1, len(keys) + 1)]})
    spec["morphemes"] = expanded
    for item in spec["morphemes"]:
        text = (item["semanticKey"] + " " + (item["label"] or "")).lower()
        wanted_type, wanted_component = item["valueType"], item["type"]
        action_words = ("add", "create", "delete", "remove", "open", "call", "dial", "send", "play", "pause", "resume", "retry", "refresh", "reserve", "book", "添加", "新建", "删除", "移除", "打开", "拨打", "发送", "播放", "暂停", "继续", "重试", "刷新", "预订", "预约")
        toggle_words = ("switch", "toggle", "enable", "disable", "power", "开关", "启用", "停用", "开启", "关闭")
        count_words = ("count", "total", "quantity", "number", "capacity", "数量", "总数", "计数", "次数", "人数", "容量")
        status_words = ("status", "state", "condition", "online", "offline", "状态", "在线", "离线")
        list_words = ("list", "items", "列表", "清单", "多条")
        if any(word in text for word in toggle_words) and item["role"] in ("PRIMARY_ACTION", "SECONDARY_ACTION"):
            wanted_type, wanted_component = "BOOLEAN", "SWITCH"
        elif any(word in text for word in action_words) and not any(word in text for word in toggle_words):
            wanted_type, wanted_component = "UNKNOWN", "BUTTON"
        elif any(word in text for word in count_words):
            wanted_type, wanted_component = "NUMBER", "METRIC"
        elif any(word in text for word in ("temperature", "气温", "温度")):
            wanted_type, wanted_component = "NUMBER", "METRIC"
        elif any(word in text for word in ("humidity", "湿度", "battery", "电量", "percent", "比例")):
            wanted_type, wanted_component = "PERCENTAGE", "PROGRESS"
        elif any(word in text for word in status_words + ("天气", "connection", "连接状态")):
            wanted_type, wanted_component = "ENUM", "STATUS"
        elif any(word in text for word in list_words) or item["valueType"] == "LIST":
            wanted_type, wanted_component = "LIST", "LIST"
        elif item["type"] == "PROGRESS" and item["valueType"] not in ("PERCENTAGE", "NUMBER", "DURATION"):
            wanted_component = "STATUS" if item["valueType"] == "ENUM" else "TEXT"
        elif item["type"] == "STATUS" and item["valueType"] in ("NUMBER", "PERCENTAGE", "DURATION"):
            wanted_component = "METRIC"
        elif item["type"] == "SWITCH" and item["valueType"] != "BOOLEAN":
            wanted_type, wanted_component = "UNKNOWN", "BUTTON"
        elif item["type"] == "BUTTON":
            wanted_type = "UNKNOWN"
        if (wanted_type, wanted_component) != (item["valueType"], item["type"]):
            corrections.append({"id": item["id"], "from": {"type": item["type"], "valueType": item["valueType"]}, "to": {"type": wanted_component, "valueType": wanted_type}})
            item["type"], item["valueType"] = wanted_component, wanted_type
            item["actionKey"] = (item["semanticKey"] + ".set" if wanted_component in ("SWITCH", "SLIDER") else
                                 item["semanticKey"] + ".trigger" if wanted_component == "BUTTON" else None)
    return spec, corrections


def apply_information_budget(spec, card_size="AUTO"):
    substitutions = []
    if card_size == "2x1":
        for item in spec["morphemes"]:
            if item["type"] == "PROGRESS" and item["role"] != "PRIMARY":
                substitutions.append({"id": item["id"], "from": "PROGRESS", "to": "METRIC", "reason": "COMPACT_SURFACE"})
                item["type"] = "METRIC"
                item["presentation"]["variant"] = "COMPACT"
    budget, used, kept, dropped = SIZE_BUDGETS[card_size], 0, [], []
    ordered = sorted(enumerate(spec["morphemes"]), key=lambda pair: (-pair[1]["priority"], pair[0]))
    for _, item in ordered:
        cost = COMPONENT_COST[item["type"]]
        if used + cost <= budget or not kept:
            kept.append(item)
            used += cost
        else:
            dropped.append({"id": item["id"], "label": item["label"], "cost": cost, "reason": "CARD_BUDGET"})
    keep_ids = {item["id"] for item in kept}
    spec["morphemes"] = [item for item in spec["morphemes"] if item["id"] in keep_ids]
    spec["surface"]["size"] = card_size
    return spec, {"size": card_size, "capacity": budget, "used": used, "substitutions": substitutions, "dropped": dropped}


def fill_mock_data(spec):
    """Demo-only adapter. Production replaces this with application data bindings."""
    for item in spec["morphemes"]:
        kind, key, value_type = item["type"], item["semanticKey"].lower(), item["valueType"]
        if kind == "PROGRESS":
            value = 68 if "battery" in key or "humidity" in key else 72
            item["content"] = {"value": value, "min": 0, "max": 100, "unit": "%", "showValue": True}
        elif kind == "METRIC":
            value, unit = (24, "°C") if "temperature" in key else (68, "%") if value_type == "PERCENTAGE" else (42, "")
            item["content"] = {"value": value, "unit": unit, "trend": "STABLE"}
        elif kind == "STATUS":
            item["content"] = {"text": "晴" if "weather" in key or "condition" in key else "已连接" if "connect" in key else "状态正常", "state": "SUCCESS"}
        elif kind == "SWITCH":
            item["content"] = {"checked": True, "disabled": False}
        elif kind == "SLIDER":
            item["content"] = {"value": 60, "min": 0, "max": 100, "step": 1, "unit": "%"}
        elif kind == "BUTTON":
            item["content"] = {"text": item["label"] or "执行", "variant": "PRIMARY", "disabled": False}
        elif kind == "LIST":
            item["content"] = {"items": [
                {"id": "item_1", "title": "第一项", "state": "ACTIVE"},
                {"id": "item_2", "title": "第二项", "state": "DEFAULT"},
                {"id": "item_3", "title": "第三项", "state": "DEFAULT"},
            ]}
        else:
            item["content"] = {"text": item["label"] or "内容将在此呈现", "maxLines": 3}
    return spec


def plan_layout(spec):
    items = spec["morphemes"]
    controls = sum(item["type"] in ("SWITCH", "SLIDER", "BUTTON") for item in items)
    if len(items) == 1:
        template = "FOCUS"
    elif len(items) >= 5:
        template = "DASHBOARD_GRID"
    elif controls:
        template = "CONTENT_ACTIONS"
    else:
        template = "SUMMARY_STACK"
    ordered = sorted(items, key=lambda item: -item["priority"])
    return {
        "template": template,
        "surface": spec["surface"],
        "regions": [
            {"id": "primary", "items": [item["id"] for item in ordered if item["role"] in ("PRIMARY", "WARNING")]},
            {"id": "details", "items": [item["id"] for item in ordered if item["role"] in ("SECONDARY", "SUPPORTING")]},
            {"id": "actions", "items": [item["id"] for item in ordered if "ACTION" in item["role"]]},
        ],
    }


def build_render_spec(spec, layout):
    index = {item["id"]: item for item in spec["morphemes"]}
    return {
        "version": "0.1", "title": spec["title"], "template": layout["template"],
        "surface": layout["surface"],
        "regions": [{"id": region["id"], "components": [index[item] for item in region["items"]]}
                    for region in layout["regions"] if region["items"]],
    }


def generate_html(render_spec):
    """Generate inspectable framework-neutral HTML; browser preview renders the same spec."""
    size = escape(render_spec.get("surface", {}).get("size", "AUTO"))
    parts = [f'<article class="genui-card" data-template="{escape(render_spec["template"])}" data-size="{size}">']
    if render_spec.get("title"):
        parts.append("<h2>" + escape(render_spec["title"]) + "</h2>")
    for region in render_spec["regions"]:
        parts.append(f'<section data-region="{escape(region["id"])}">')
        for item in region["components"]:
            label = escape(item.get("label") or "")
            parts.append(f'<div data-morpheme="{escape(item["type"])}" data-id="{escape(item["id"])}"><span>{label}</span></div>')
        parts.append("</section>")
    parts.append("</article>")
    return "".join(parts)
