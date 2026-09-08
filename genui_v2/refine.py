"""Flow refinement between binding and layout.

Three deterministic mechanisms answering the flow-completeness questions:

1. MISS policy   — a morpheme whose semantic key resolved to nothing is handled
   by role: unbound ACTIONs are dropped (a dead button is worse than absence),
   unbound SUPPORTING is dropped (filler that cannot be filled), unbound
   PRIMARY/SECONDARY stays as flagged static text (the user asked for it).
   Before dropping, bind() already retried resolution across all domains.

2. Enrichment    — registry-guided richness (联想诱导), done by CODE not by the
   model: if the card is under its information budget after the user-requested
   morphemes, sibling entries of the SAME provider are appended as SUPPORTING
   morphemes (priority 25, below every user-requested role) in manifest order.
   Values come from the registry, so enrichment can never fabricate; the budget
   stage trims enriched items first when space runs out. Controls (BOOLEAN /
   action-only entries) are never auto-added — an unrequested toggle is a
   mis-tap hazard, not richness.

3. Coalescing    — homogeneous overflow (e.g. 10 BUTTONs vs a 2-action
   archetype) collapses into a container morpheme instead of being trimmed:
   buttons beyond the per-size cap become one horizontally scrollable chip row
   (LIST variant "chips"); METRIC/STATUS beyond cap keep the top item and fold
   the rest into list rows. The container matches COLLECTION slots, so
   archetypes stay reachable and every item survives inside simple interaction.
"""
from .capability import PROVIDERS, _content_from_entry
from .derive import derive_component
from .protocol import COMPONENT_COST, ROLE_PRIORITY, SIZE_BUDGETS, resolve_auto_size

ENRICH_PRIORITY = 25          # below SUPPORTING(30): user-requested content always wins
ENRICH_MAX_ITEMS = 3
ACTION_CAP = {"2x1": 1, "2x2": 2, "3x2": 4, "3x3": 4}
INFO_CAP = {"2x1": 2, "2x2": 3, "3x2": 4, "3x3": 5}


def apply_miss_policy(spec):
    kept, notes = [], []
    for item in spec["morphemes"]:
        resolution = (item.get("binding") or {}).get("resolution")
        if resolution == "MISS" and "ACTION" in item["role"]:
            notes.append("删除无绑定动作「%s」（无可执行方法，死按钮比空白更糟）" % (item.get("label") or item["semanticKey"]))
            continue
        if resolution == "MISS" and item["role"] == "SUPPORTING":
            notes.append("删除无绑定辅助信息「%s」（填充物填不上就不占位）" % (item.get("label") or item["semanticKey"]))
            continue
        kept.append(item)
    if kept:
        spec["morphemes"] = kept
    else:
        notes.append("全部语素均无绑定，保留原始内容作静态卡")
    return spec, notes


def _enrich_label(entry):
    aliases = [alias for alias in entry.get("aliases", []) if not alias.isascii()]
    if aliases:
        return max(aliases, key=len)
    return entry["key"].split(".")[-1]


def enrich(spec, domain=None):
    size = spec["surface"]["size"]
    if size == "AUTO":
        size = resolve_auto_size(spec)
        spec["surface"]["size"] = size
    room = SIZE_BUDGETS[size] - sum(COMPONENT_COST.get(m.get("type", "TEXT"), 1)
                                    for m in spec["morphemes"])
    if room <= 0:
        return spec, []
    used_keys = {(m.get("binding") or {}).get("key") for m in spec["morphemes"]}
    provider_order = list(dict.fromkeys(
        (m.get("binding") or {}).get("providerId")
        for m in sorted(spec["morphemes"], key=lambda m: -m["priority"])))
    added, notes = [], []
    for provider_id in provider_order:
        provider = next((p for p in PROVIDERS if p["providerId"] == provider_id), None)
        if provider is None:
            continue
        for entry in provider["entries"]:
            if len(added) >= ENRICH_MAX_ITEMS or room <= 0:
                break
            if (entry["key"] in used_keys or entry.get("generator") or not entry.get("path")
                    or entry["valueType"] in ("BOOLEAN", "UNKNOWN")):
                continue
            item = {"id": "e%d" % (len(added) + 1), "role": "SUPPORTING",
                    "priority": ENRICH_PRIORITY, "label": _enrich_label(entry),
                    "semanticKey": entry["key"], "valueType": entry["valueType"],
                    "content": _content_from_entry(entry),
                    "binding": {"resolution": "ENRICHED", "key": entry["key"],
                                "providerId": provider_id, "path": entry.get("path"),
                                "permission": entry.get("permission"),
                                "freshness": entry.get("freshness", "PULL"), "generator": False},
                    "presentation": {"enriched": True}}
            item["type"] = derive_component(item)
            item["actionKey"] = None
            cost = COMPONENT_COST.get(item["type"], 1)
            if cost > room:
                continue
            room -= cost
            used_keys.add(entry["key"])
            added.append(item)
            notes.append("注册表联想补充「%s」（%s，SUPPORTING，预算不足时最先让位）"
                         % (item["label"], entry["key"]))
    spec["morphemes"].extend(added)
    return spec, notes


def coalesce(spec):
    size = spec["surface"]["size"]
    notes = []
    buttons = [m for m in spec["morphemes"] if m["type"] == "BUTTON"]
    cap = ACTION_CAP.get(size, 2)
    if len(buttons) > cap:
        ordered = sorted(buttons, key=lambda m: -m["priority"])
        group = {"id": "g_actions", "type": "LIST",
                 "role": max((m["role"] for m in ordered),
                             key=lambda role: ROLE_PRIORITY.get(role, 0)),
                 "priority": max(m["priority"] for m in ordered),
                 "label": "快捷操作", "semanticKey": "group.actions", "valueType": "LIST",
                 "content": {"items": [{"title": m.get("label") or "操作",
                                        "action": m.get("actionKey")} for m in ordered]},
                 "binding": {"resolution": "GROUP"},
                 "presentation": {"variant": "chips"}, "actionKey": None}
        spec["morphemes"] = [m for m in spec["morphemes"] if m["type"] != "BUTTON"] + [group]
        notes.append("%d 个按钮超出 %s 容量(%d)，聚合为横滑操作条（每项保留各自动作）"
                     % (len(buttons), size, cap))
    info_cap = INFO_CAP.get(size, 3)
    for kind in ("METRIC", "STATUS"):
        items = [m for m in spec["morphemes"] if m["type"] == kind]
        if len(items) <= info_cap:
            continue
        ordered = sorted(items, key=lambda m: -m["priority"])
        keep, fold = ordered[0], ordered[1:]
        rows = [{"title": "%s %s" % (m.get("label") or "",
                                     m.get("content", {}).get("value",
                                                              m.get("content", {}).get("text", "")))}
                for m in fold]
        group = {"id": "g_%s" % kind.lower(), "type": "LIST",
                 "role": "SECONDARY", "priority": max(m["priority"] for m in fold),
                 "label": keep.get("label") or kind, "semanticKey": "group." + kind.lower(),
                 "valueType": "LIST", "content": {"items": rows},
                 "binding": {"resolution": "GROUP"}, "presentation": {}, "actionKey": None}
        fold_ids = {m["id"] for m in fold}
        spec["morphemes"] = [m for m in spec["morphemes"] if m["id"] not in fold_ids] + [group]
        notes.append("%d 个 %s 超出容量(%d)，保留最高优 1 个，其余折叠为列表行"
                     % (len(items), kind, info_cap))
    return spec, notes
