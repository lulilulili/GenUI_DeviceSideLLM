"""跨骨架 query 冲突消解（P0-3 配套，expand 前必跑）。

问题：反写法为相邻骨架（如"仅降水" vs "降水+天况"）各自生成了相同/近重复的
省略式短句，同一句话对应不同 target_draft = 教模型自相矛盾的毒样本。

消解规则（最小解释原则）：近重复组（归一化后 Jaccard≥0.80）内若答案不同，
只保留语素数最少的骨架成员——用户没说的辅助项不应出现在标签里；
语素数并列且答案仍不同时按 skeleton_id 序保留第一个。

用法：python tools/dedup_queries.py
输入：data/factory/skeletons.jsonl + queries.jsonl
输出：data/factory/queries_clean.jsonl + 冲突消解报告（stdout）
之后：用 queries_clean.jsonl 重跑 gen_training_data.py expand
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTORY = ROOT / "data" / "factory"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _normalize(text):
    return re.sub(r"[\s，。！？,.!?、“”\"'：:；;]", "", text)


def _bigrams(text):
    return frozenset(text[i:i + 2] for i in range(len(text) - 1)) or frozenset([text])


def _jaccard(a, b):
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def main():
    skeletons = {}
    for line in (FACTORY / "skeletons.jsonl").read_text(encoding="utf-8").splitlines():
        if line:
            row = json.loads(line)
            skeletons[row["skeleton_id"]] = row
    members = []  # (norm, grams, skeleton_id, query, answer_key, morpheme_count)
    for line in (FACTORY / "queries.jsonl").read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        row = json.loads(line)
        skeleton = skeletons[row["skeleton_id"]]
        answer = json.dumps(skeleton["target_draft"], ensure_ascii=False, sort_keys=True)
        count = len(skeleton["target_draft"]["m"])
        for query in row["queries"]:
            norm = _normalize(query)
            members.append([norm, _bigrams(norm), row["skeleton_id"], query, answer, count, True])

    # 分桶找近重复组
    buckets = defaultdict(list)
    for index, member in enumerate(members):
        for gram in list(member[1])[:6]:
            buckets[gram].append(index)
    adjacency = defaultdict(set)
    for bucket in buckets.values():
        if len(bucket) > 400:
            continue
        for i in range(len(bucket)):
            for j in range(i + 1, len(bucket)):
                a, b = bucket[i], bucket[j]
                if abs(len(members[a][0]) - len(members[b][0])) > \
                        max(len(members[a][0]), len(members[b][0])) * 0.5:
                    continue
                if _jaccard(members[a][1], members[b][1]) >= 0.80:
                    adjacency[a].add(b)
                    adjacency[b].add(a)

    # 连通分量内消解
    visited, dropped = set(), 0
    for start in list(adjacency):
        if start in visited:
            continue
        component, stack = [], [start]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            stack.extend(adjacency[node] - visited)
        answers = {members[i][4] for i in component}
        if len(answers) <= 1:
            continue
        min_count = min(members[i][5] for i in component)
        keepers = sorted((i for i in component if members[i][5] == min_count),
                         key=lambda i: members[i][2])
        keep_answer = members[keepers[0]][4]
        for i in component:
            if members[i][4] != keep_answer:
                members[i][6] = False
                dropped += 1

    by_skeleton = defaultdict(list)
    for member in members:
        if member[6]:
            by_skeleton[member[2]].append(member[3])
    out = FACTORY / "queries_clean.jsonl"
    with out.open("w", encoding="utf-8") as handle:
        for skeleton_id in sorted(by_skeleton):
            handle.write(json.dumps({"skeleton_id": skeleton_id,
                                     "queries": by_skeleton[skeleton_id]},
                                    ensure_ascii=False) + "\n")
    empty = [sid for sid in skeletons if sid not in by_skeleton]
    print("成员 %d，冲突消解丢弃 %d，骨架保有 %d/%d（清空 %d 个）"
          % (len(members), dropped, len(by_skeleton), len(skeletons), len(empty)))
    if empty:
        print("清空骨架（其 query 全部让位给更小骨架）:", "、".join(empty[:8]),
              "…" if len(empty) > 8 else "")
    print("->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
