"""Business variant layer (借鉴 CreateMyCard provider.json 的 primaryData 设计).

"主数据不同即不同模板"：同一业务按用户强调的主焦点声明多个变体，每个变体
给出 primary（主焦点语义键）与 secondary（该焦点下的推荐辅助字段）。当卡片
的 PRIMARY 语素绑定到某变体的 primary 键时，用变体的 curated 辅助字段补齐
卡片（替代泛化的注册表联想），实现"问湿度则湿度上大数字位"的主焦点切换。

解耦保证：
- 本模块只在 PipelineV2 features["variants"] 开启时被调用；关闭即完全退出链路。
- 只增语素不删语素、不改用户请求的任何字段；新增项 priority=35，压在用户
  SECONDARY(60) 之下、泛化联想(25) 之上，预算裁剪时先于用户内容让位。
- 变体命中时泛化联想（enrich）让位——变体就是策划过的联想。
"""
from .capability import BY_KEY, _content_from_entry

VARIANT_PRIORITY = 35

# 声明式变体族：与提示词、模型完全无关，可独立增删。
VARIANTS = {
    "WEATHER": [
        {"id": "weather.focus.temperature", "primary": "weather.temperature",
         "secondary": ["weather.condition", "weather.city", "weather.air_quality"],
         "description": "温度为主焦点"},
        {"id": "weather.focus.humidity", "primary": "weather.humidity",
         "secondary": ["weather.temperature", "weather.condition", "weather.air_quality"],
         "description": "湿度为主焦点"},
        {"id": "weather.focus.rain", "primary": "weather.precipitation.probability",
         "secondary": ["weather.condition", "weather.temperature"],
         "description": "降水概率为主焦点"},
        {"id": "weather.focus.air", "primary": "weather.air_quality",
         "secondary": ["weather.condition", "weather.temperature"],
         "description": "空气质量为主焦点"},
    ],
    "DEVICE": [
        {"id": "battery.focus.level", "primary": "phone.battery.level",
         "secondary": ["phone.battery.charging", "phone.battery.remain_time"],
         "description": "手机电量为主焦点"},
        {"id": "battery.focus.headphones", "primary": "headphones.battery.level",
         "secondary": ["headphones.connection.status"],
         "description": "耳机电量为主焦点"},
    ],
    "TASK": [
        {"id": "task.focus.list", "primary": "task.list",
         "secondary": ["calendar.next_event"],
         "description": "待办清单为主焦点"},
    ],
}


def apply_variant(spec, domain):
    """PRIMARY 语素的绑定键命中变体 primary 时，补齐该变体的 curated 辅助字段。

    Returns (spec, variant_id | None, notes).
    """
    primary = next((m for m in spec["morphemes"]
                    if m["role"] in ("PRIMARY", "WARNING")
                    and (m.get("binding") or {}).get("key")), None)
    if primary is None:
        return spec, None, []
    primary_key = primary["binding"]["key"]
    variant = next((v for v in VARIANTS.get(domain or "", [])
                    if v["primary"] == primary_key), None)
    if variant is None:
        return spec, None, []
    present_keys = {(m.get("binding") or {}).get("key") for m in spec["morphemes"]}
    notes = ["命中业务变体「%s」（%s）" % (variant["description"], variant["id"])]
    added = 0
    for key in variant["secondary"]:
        entry = BY_KEY.get(key)
        if entry is None or key in present_keys:
            continue
        added += 1
        spec["morphemes"].append({
            "id": "v%d" % added, "role": "SUPPORTING", "priority": VARIANT_PRIORITY,
            "label": _variant_label(entry), "semanticKey": key,
            "valueType": entry["valueType"], "content": _content_from_entry(entry),
            "binding": {"resolution": "VARIANT", "key": key,
                        "providerId": entry["providerId"], "path": entry.get("path"),
                        "permission": entry.get("permission"),
                        "freshness": entry.get("freshness", "PULL"), "generator": False},
            "presentation": {"variant": None, "fromVariant": variant["id"]},
            "actionKey": None})
        present_keys.add(key)
        notes.append("变体补充辅助字段「%s」（%s）" % (_variant_label(entry), key))
    spec["businessVariant"] = variant["id"]
    return spec, variant["id"], notes


def _variant_label(entry):
    aliases = [alias for alias in entry.get("aliases", []) if not alias.isascii()]
    return max(aliases, key=len) if aliases else entry["key"].split(".")[-1]
