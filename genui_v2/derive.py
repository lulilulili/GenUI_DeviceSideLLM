"""Deterministic component derivation: (role, valueType, key words) -> component.

v1 asked the model to pick the component (k) and then reconcile_types() fixed it
with keyword rules — two owners for one decision. v2 has exactly one owner:
this table. The model can no longer "pick SWITCH for a momentary action"
because it never picks components at all.

Derivation order (first hit wins):
1. ACTION roles:  BOOLEAN -> SWITCH (stateful), PERCENTAGE/NUMBER -> SLIDER
                  (continuous), otherwise BUTTON (momentary).
2. LIST valueType (or list-ish words)          -> LIST
3. PERCENTAGE                                  -> PROGRESS (ring/bar affordance)
4. NUMBER / DURATION                           -> METRIC  (big figure)
5. ENUM                                        -> STATUS  (state chip)
6. everything else                             -> TEXT
"""

LIST_WORDS = ("list", "items", "列表", "清单", "多条", "daily", "forecast")


def derive_component(item):
    role, value_type = item["role"], item["valueType"]
    text = (item["semanticKey"] + " " + (item["label"] or "")).lower()
    if "ACTION" in role:
        if value_type == "BOOLEAN":
            component = "SWITCH"
        elif value_type in ("PERCENTAGE", "NUMBER"):
            component = "SLIDER"
        else:
            component = "BUTTON"
    elif value_type == "LIST" or any(word in text for word in LIST_WORDS):
        component = "LIST"
    elif value_type == "PERCENTAGE":
        component = "PROGRESS"
    elif value_type in ("NUMBER", "DURATION"):
        component = "METRIC"
    elif value_type == "ENUM":
        component = "STATUS"
    else:
        component = "TEXT"
    return component


def apply(spec):
    """Annotate every morpheme with its derived component and action key."""
    decisions = []
    for item in spec["morphemes"]:
        component = derive_component(item)
        item["type"] = component
        action = (item.get("binding") or {}).get("action")
        if component in ("SWITCH", "SLIDER"):
            item["actionKey"] = action or {"call": "setCapability", "args": {"key": item["semanticKey"]}}
        elif component == "BUTTON":
            item["actionKey"] = action or {"call": "triggerCapability", "args": {"key": item["semanticKey"]}}
        else:
            item["actionKey"] = None
        decisions.append({"id": item["id"], "component": component,
                          "from": {"role": item["role"], "valueType": item["valueType"]}})
    return spec, decisions
