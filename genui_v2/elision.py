"""Deterministic label elision: hide a morpheme's own label when it is
redundant with other channels on the card.

The reference PDF never labels "26°" as 温度 (the unit + title carry it) but
always labels 空气质量:优 (the bare value is unreadable). The distinction is
computable — a label may be hidden only when ALL of:

  1. uniqueness   — no sibling of the same component kind on the card
                    (two rings MUST both keep labels; hard rule, checked first);
  2. self-evidence— the value explains itself: strong units (° / °C / 时长 /
                    DATETIME), a progress ring's built-in %, or a list whose
                    rows are self-describing;
  3. context      — the card title covers the label's domain words, so the
                    reader already knows what the value belongs to.

Component-shape overrides:
  BUTTON  -> label is already the pill text, never render a separate label;
  SWITCH  -> a switch without a label is a mystery toggle; hide only when the
             title literally equals/contains the label;
  STATUS/TEXT -> hide only on strict substring coverage by the title
             (gram overlap like 连接状态~耳机状态 is NOT enough — the value
             might not read alone);
  WARNING -> always keep.

A visually hidden label is preserved as the accessibility label — elision is
a visual decision, not an information deletion.
"""
from collections import Counter

STRONG_UNITS = {"°", "°C"}
MEDIUM_UNITS = {"%", "步", "kcal", "km", "时", "分"}


def _grams(text):
    text = text or ""
    return {text[i:i + 2] for i in range(len(text) - 1) if text[i:i + 2].strip()}


def _title_covers(title, label):
    """Loose domain coverage: any 2-char gram of the label appears in the title."""
    if not title or not label:
        return False
    return any(gram in title for gram in _grams(label))


def _title_subsumes(title, label):
    """Strict coverage: label literally inside the title (or vice versa)."""
    return bool(title) and bool(label) and (label in title or title in label)


def plan_label_visibility(spec):
    items = spec["morphemes"]
    title = spec.get("title") or ""
    kind_counts = Counter(item["type"] for item in items)
    decisions = []
    for item in items:
        kind, label = item["type"], item.get("label") or ""
        content = item.get("content", {})
        unit = str(content.get("unit") or "")
        show, reason = True, "DEFAULT_SHOW"
        if kind == "BUTTON":
            show, reason = False, "BUTTON_EMBEDS_LABEL"
        elif item["role"] == "WARNING":
            show, reason = True, "WARNING_ALWAYS"
        elif kind_counts[kind] > 1:
            show, reason = True, "SIBLING_DISAMBIGUATION"
        elif kind in ("METRIC", "PROGRESS"):
            strong = unit in STRONG_UNITS or item["valueType"] in ("DURATION", "DATETIME")
            medium = kind == "PROGRESS" or unit in MEDIUM_UNITS
            if strong and title:
                show, reason = False, "VALUE_SELF_EVIDENT"
            elif medium and _title_covers(title, label):
                show, reason = False, "TITLE_CONTEXT_COVERS"
        elif kind == "LIST" and _title_covers(title, label):
            show, reason = False, "TITLE_CONTEXT_COVERS"
        elif kind in ("STATUS", "TEXT") and _title_subsumes(title, label):
            show, reason = False, "TITLE_SUBSUMES_LABEL"
        elif kind in ("SWITCH", "SLIDER") and _title_subsumes(title, label):
            show, reason = False, "TITLE_SUBSUMES_LABEL"
        presentation = item.setdefault("presentation", {})
        presentation["showLabel"] = show
        if not show:
            presentation["a11yLabel"] = label
        decisions.append({"id": item["id"], "label": label, "show": show, "reason": reason})
    return spec, decisions
