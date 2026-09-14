"""GD 训练集四层健康检查（P0-3，与 CC 侧 training/dataset_health.py 同构）。

L1 精确重复 / L2 近重复+跨答案冲突 / L3 对冻结集（复用 check_leakage 已覆盖，
此处补近重复口径）/ L4 答案集中度。

用法：python tools/dataset_health.py
输出：data/factory/sft_train_v1.health.json
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEAR_DUP_THRESHOLD = 0.80
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _normalize(text):
    return re.sub(r"[\s，。！？,.!?、“”\"'：:；;]", "", text)


def _bigrams(text):
    return frozenset(text[i:i + 2] for i in range(len(text) - 1)) or frozenset([text])


def _jaccard(a, b):
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def near_dup_pairs(items):
    buckets = defaultdict(list)
    for index, (norm, grams, _) in enumerate(items):
        for gram in list(grams)[:6]:
            buckets[gram].append(index)
    candidates = set()
    for bucket in buckets.values():
        if len(bucket) > 400:
            continue
        for i in range(len(bucket)):
            for j in range(i + 1, len(bucket)):
                candidates.add((bucket[i], bucket[j]))
    pairs = []
    for i, j in candidates:
        if abs(len(items[i][0]) - len(items[j][0])) > max(len(items[i][0]), len(items[j][0])) * 0.5:
            continue
        score = _jaccard(items[i][1], items[j][1])
        if score >= NEAR_DUP_THRESHOLD:
            pairs.append((i, j, round(score, 3)))
    return pairs


def main():
    fix = "--fix" in sys.argv
    sft_path = ROOT / "data" / "factory" / "sft_train_v1.jsonl"
    audit_path = ROOT / "data" / "factory" / "sft_train_v1.audit.jsonl"
    sft = [json.loads(line) for line in
           sft_path.read_text(encoding="utf-8").splitlines() if line]
    audit = [json.loads(line) for line in
             audit_path.read_text(encoding="utf-8").splitlines() if line]
    assert len(sft) == len(audit)
    items = []
    for row, meta in zip(sft, audit):
        norm = _normalize(meta["prompt_text"])
        items.append((norm, _bigrams(norm), row["messages"][2]["content"]))

    exact = Counter(norm for norm, _, _ in items)
    pairs = near_dup_pairs(items)
    conflicts = [(i, j, s) for i, j, s in pairs if items[i][2] != items[j][2]]

    if fix and conflicts:
        # 终修：冲突连通分量内按"最小解释原则"保留语素最少的答案侧，其余删除
        adjacency = defaultdict(set)
        for i, j, _ in conflicts:
            adjacency[i].add(j)
            adjacency[j].add(i)
        drop, visited = set(), set()
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
            def morphemes(index):
                return len(json.loads(items[index][2])["m"])
            keep_answer = items[min(component, key=morphemes)][2]
            drop.update(i for i in component if items[i][2] != keep_answer)
        keep_indexes = [i for i in range(len(sft)) if i not in drop]
        with sft_path.open("w", encoding="utf-8") as handle:
            for i in keep_indexes:
                handle.write(json.dumps(sft[i], ensure_ascii=False) + "\n")
        with audit_path.open("w", encoding="utf-8") as handle:
            for i in keep_indexes:
                handle.write(json.dumps(audit[i], ensure_ascii=False) + "\n")
        print("终修：删除冲突样本 %d 条，剩余 %d；请重跑本工具复核" % (len(drop), len(keep_indexes)))
        return 0

    frozen_path = ROOT / "evals" / "frozen" / "frozen_set_v1.jsonl"
    frozen_near = frozen_exact = None
    if frozen_path.exists():
        frozen = [json.loads(line) for line in
                  frozen_path.read_text(encoding="utf-8").splitlines() if line]
        frozen_items = [(_normalize(f["prompt"]), _bigrams(_normalize(f["prompt"])))
                        for f in frozen]
        frozen_norms = {f[0] for f in frozen_items}
        frozen_exact = sum(1 for norm, _, _ in items if norm in frozen_norms)
        frozen_near = 0
        for norm, grams, _ in items:
            if any(_jaccard(grams, f_grams) >= 0.60 for _, f_grams in frozen_items):
                frozen_near += 1

    answers = Counter(ans for _, _, ans in items)
    report = {
        "dataset": "sft_train_v1",
        "samples": len(items),
        "L1_exact_dup_groups": sum(1 for v in exact.values() if v > 1),
        "L2_near_dup_pairs": len(pairs),
        "L2_near_dup_rate": round(len(pairs) / max(1, len(items)), 4),
        "L2_note": "风格轴×2 为刻意增广，近重复率含其贡献；危险的是跨答案冲突",
        "L2_cross_answer_conflicts": len(conflicts),
        "L2_conflict_examples": [
            {"a": audit[i]["prompt_text"][:40], "b": audit[j]["prompt_text"][:40], "jaccard": s}
            for i, j, s in conflicts[:5]],
        "L3_frozen_exact": frozen_exact,
        "L3_frozen_near060": frozen_near,
        "L4_distinct_answers": len(answers),
        "L4_top_answer_share": round(max(answers.values()) / len(items), 4),
    }
    out = ROOT / "data" / "factory" / "sft_train_v1.health.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "L2_conflict_examples"},
                     ensure_ascii=False, indent=1))
    for example in report["L2_conflict_examples"]:
        print(" 冲突例:", example["a"], "||", example["b"], example["jaccard"])
    verdict = (report["L2_cross_answer_conflicts"] == 0
               and not report["L3_frozen_exact"])
    print("健康判定:", "PASS" if verdict else "存在待处理项")
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())
