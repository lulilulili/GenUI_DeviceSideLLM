"""UX-level budgets (借鉴 CreateMyCard theme-base.json 的 sizeBudgets 维度).

组件成本预算（protocol.apply_information_budget）之外的两个美学维度：
- maxInformationLevels：每尺寸允许的信息层级数（PRIMARY/WARNING=1 级，
  SECONDARY=2 级，SUPPORTING=3 级）。小卡挤三级信息会破坏"1-2 秒看懂"，
  超限时整层丢弃最低层级（联想/变体补充项优先让位）。
- maxListItems：每尺寸列表可见行数上限，超出截断（chips 操作条除外——
  它靠横滑天然支持溢出）。

解耦保证：仅在 features["ux_budget"] 开启时调用；只裁剪不新增；所有裁剪
带说明返回，UI 可见。
"""

LEVEL_BUDGETS = {
    "2x1": {"maxInformationLevels": 2, "maxListItems": 2},
    "2x2": {"maxInformationLevels": 2, "maxListItems": 2},
    "3x2": {"maxInformationLevels": 3, "maxListItems": 3},
    "3x3": {"maxInformationLevels": 3, "maxListItems": 4},
}

_LEVEL_OF = {"PRIMARY": 1, "WARNING": 1, "SECONDARY": 2, "SUPPORTING": 3}


def apply_ux_budget(spec):
    size = spec["surface"]["size"]
    budget = LEVEL_BUDGETS.get(size)
    if budget is None:
        return spec, []
    notes = []
    info_items = [m for m in spec["morphemes"] if "ACTION" not in m["role"]]
    levels_present = sorted({_LEVEL_OF.get(m["role"], 2) for m in info_items})
    while len(levels_present) > budget["maxInformationLevels"]:
        drop_level = levels_present[-1]
        dropped = [m for m in info_items if _LEVEL_OF.get(m["role"], 2) == drop_level]
        keep_ids = {m["id"] for m in dropped}
        spec["morphemes"] = [m for m in spec["morphemes"] if m["id"] not in keep_ids]
        notes.append("%s 最多 %d 级信息层级，丢弃第 %d 级（%s）"
                     % (size, budget["maxInformationLevels"], drop_level,
                        "、".join(str(m.get("label") or m["id"]) for m in dropped)))
        info_items = [m for m in spec["morphemes"] if "ACTION" not in m["role"]]
        levels_present = sorted({_LEVEL_OF.get(m["role"], 2) for m in info_items})
    max_rows = budget["maxListItems"]
    for item in spec["morphemes"]:
        if item.get("type") != "LIST" or item.get("presentation", {}).get("variant") == "chips":
            continue
        rows = item.get("content", {}).get("items")
        if isinstance(rows, list) and len(rows) > max_rows:
            item["content"]["items"] = rows[:max_rows]
            notes.append("%s 列表最多 %d 行，「%s」截断 %d 行"
                         % (size, max_rows, item.get("label") or item["id"],
                            len(rows) - max_rows))
    return spec, notes
