"""训练集 × 冻结集泄漏检查：三个层级，一个都不能少。

实习生 A2UI 数据的教训：他的 train/test 做到了"消息级零重叠"，但事后审计
发现目标答案哈希交集 196 条、上下文哈希交集 195 条——文本不同、事实相同，
评测照样带记忆水分。所以本工具查三层：

  L1 文本级   规范化后的 prompt 完全相同（硬失败）
  L2 近重复   字符 3-gram Jaccard ≥ 阈值（默认 0.6，硬失败并列出最像的对）
  L3 事实级   训练样本目标草稿的语素键组合 == 冻结用例期望键组合（默认警告；
              --strict-keyset 时硬失败。键组合撞车不一定是抄题，但比例高
              说明冻结集没考到训练分布之外）

用法：
  python tools/check_leakage.py --train data/factory/sft_train.jsonl \
      --frozen evals/frozen/frozen_set_v1.jsonl
组装训练集后、每次训练前各跑一次；退出码非 0 表示不许继续。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def normalize(text):
    return "".join(ch for ch in (text or "").lower() if ch.isalnum())


def trigrams(text):
    return {text[i:i + 3] for i in range(len(text) - 2)} if len(text) >= 3 else {text}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_train(path):
    """每行提取 (prompt文本, 目标草稿键组合)。兼容 messages 格式与 target_draft 格式。"""
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            prompt, draft = row.get("prompt") or row.get("user_prompt"), row.get("target_draft")
            if "messages" in row:
                for message in row["messages"]:
                    if message.get("role") == "user" and prompt is None:
                        prompt = message.get("content")
                    if message.get("role") == "assistant" and draft is None:
                        try:
                            draft = json.loads(message["content"])
                        except (ValueError, TypeError):
                            pass
            keyset = None
            if isinstance(draft, dict) and isinstance(draft.get("m"), list):
                keyset = frozenset(item.get("q", "") for item in draft["m"])
            rows.append({"line": line_number, "prompt": prompt or "",
                         "norm": normalize(prompt), "keyset": keyset})
    return rows


def load_frozen(path):
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            case = json.loads(line)
            keyset = frozenset(m["keys"][0] for m in case["expected"].get("morphemes", []))
            rows.append({"id": case["id"], "prompt": case["prompt"],
                         "norm": normalize(case["prompt"]),
                         "trigrams": trigrams(normalize(case["prompt"])),
                         "keyset": keyset or None})
    return rows


def main():
    parser = argparse.ArgumentParser(description="训练集×冻结集泄漏检查")
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--near-dup-threshold", type=float, default=0.6)
    parser.add_argument("--strict-keyset", action="store_true",
                        help="事实级撞车也算硬失败（组装最终训练集时建议开启）")
    parser.add_argument("--top", type=int, default=10, help="展示最像的前 N 对")
    args = parser.parse_args()

    train, frozen = load_train(args.train), load_frozen(args.frozen)
    print("训练 %d 条 × 冻结 %d 条" % (len(train), len(frozen)))

    train_norms = {}
    for row in train:
        train_norms.setdefault(row["norm"], []).append(row["line"])
    exact = [(case["id"], train_norms[case["norm"]])
             for case in frozen if case["norm"] and case["norm"] in train_norms]

    near = []
    for case in frozen:
        for row in train:
            if not row["norm"] or row["norm"] == case["norm"]:
                continue
            score = jaccard(case["trigrams"], trigrams(row["norm"]))
            if score >= args.near_dup_threshold:
                near.append((round(score, 3), case["id"], row["line"], row["prompt"][:50]))
    near.sort(reverse=True)

    train_keysets = {}
    for row in train:
        if row["keyset"]:
            train_keysets.setdefault(row["keyset"], []).append(row["line"])
    keyset_hits = [(case["id"], sorted(train_keysets[case["keyset"]])[:5])
                   for case in frozen if case["keyset"] and case["keyset"] in train_keysets]

    print("\nL1 文本级完全重复: %d" % len(exact))
    for case_id, lines in exact[: args.top]:
        print("  %s == 训练行 %s" % (case_id, lines[:5]))
    print("L2 近重复(Jaccard≥%.2f): %d" % (args.near_dup_threshold, len(near)))
    for score, case_id, line, preview in near[: args.top]:
        print("  %.3f %s ~ 训练行 %d: %s" % (score, case_id, line, preview))
    print("L3 事实级键组合撞车: %d / %d 条冻结用例"
          % (len(keyset_hits), sum(1 for c in frozen if c["keyset"])))
    for case_id, lines in keyset_hits[: args.top]:
        print("  %s 键组合与训练行 %s 相同" % (case_id, lines))

    failed = bool(exact or near) or (args.strict_keyset and keyset_hits)
    if failed:
        raise SystemExit("\n泄漏检查未通过：把命中的训练样本删除或改写场景后重跑。")
    if keyset_hits:
        print("\n通过（含 %d 条事实级撞车警告——冻结集应有相当比例考训练分布之外的键组合；"
              "组装最终训练集时用 --strict-keyset 复查）。" % len(keyset_hits))
    else:
        print("\n泄漏检查通过。")


if __name__ == "__main__":
    main()
