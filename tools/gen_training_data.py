"""数据工厂：从能力注册表反向生成训练数据（两阶段）。

思路对比（为什么是"反向"）：
  实习生 A2UI 的做法是 144 条人工种子 → 确定性改写扩增 5000 条，65% 只改
  说法不改事实，他自己承认只测"表达泛化"。本项目的注册表本身就枚举了全部
  合法输出空间，所以反过来：先确定性枚举"合法答案"（骨架），再让大模型给
  每个答案写多样的"问题"（query 反写），场景覆盖率由枚举保证，不靠运气。
  从他那里借来的是：正交扩增轴（对话风格）、逐行审计清单（audit manifest，
  审计字段绝不进模型输入）、契约版本号绑定。

阶段 1  enumerate  枚举注册表合法语素组合 → 骨架文件（含给云端大模型的
                   query 反写指令，人工把生成的 query 审核后填回）
阶段 2  expand     读入 {skeleton_id, queries:[...]} → 应用对话风格扩增
                   → 产出 SFT messages jsonl + 并行审计清单

用法：
  python tools/gen_training_data.py enumerate --output data/factory/skeletons.jsonl
  python tools/gen_training_data.py expand --skeletons data/factory/skeletons.jsonl \
      --queries data/factory/queries.jsonl --output data/factory/sft_raw.jsonl

产出后必跑：python tools/check_leakage.py --train data/factory/sft_raw.jsonl \
                --frozen evals/frozen/frozen_set_v1.jsonl
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from genui_v2 import protocol
from genui_v2.capability import PROVIDERS, keys_for_domain

MAX_SUPPORTING = 2          # 每个骨架最多带 2 个辅助语素
MAX_PER_PRIMARY = 6         # 每个主语素最多派生 6 个骨架，防组合爆炸
QUERIES_PER_SKELETON = 12   # 期望云端大模型为每个骨架反写的 query 数

# 对话风格轴（借鉴实习生的 8 风格扩增；确定性变换，只动表达不动语义）
STYLES = {
    "source": lambda q: q,
    "polite": lambda q: "麻烦帮我" + q + "，谢谢",
    "spoken": lambda q: "哎，" + q + "呗",
    "confirming": lambda q: q + "，可以吗？",
    "contextual": lambda q: "我马上要出门，" + q,
    "direct": lambda q: q if q.startswith(("给我", "帮我", "显示")) else "给我" + q,
}


def _label(entry):
    aliases = [alias for alias in entry.get("aliases", []) if not alias.isascii() and len(alias) >= 2]
    return min(aliases, key=len) if aliases else entry["key"].split(".")[-1]


def _morpheme(entry, role):
    return {"l": _label(entry), "q": entry["key"], "f": entry["valueType"], "r": role}


def enumerate_skeletons():
    """枚举 (主语素 × 辅助子集 × 可选动作) 的合法组合。"""
    skeletons = []
    for provider in PROVIDERS:
        entries = provider["entries"]
        info = [e for e in entries if e.get("path") and e["valueType"] not in ("BOOLEAN",)
                and not e.get("generator")]
        toggles = [e for e in entries if e["valueType"] == "BOOLEAN" and e.get("action")]
        for primary in info:
            siblings = [e for e in info if e["key"] != primary["key"]]
            combos = [()]
            combos += [(s,) for s in siblings[:MAX_SUPPORTING + 1]]
            combos += list(itertools.combinations(siblings[:MAX_SUPPORTING + 1], 2))
            count = 0
            for supporting in combos:
                for action in [None] + toggles[:1]:
                    if count >= MAX_PER_PRIMARY:
                        break
                    morphemes = [_morpheme(primary, "PRIMARY")]
                    morphemes += [_morpheme(s, "SECONDARY" if i == 0 else "SUPPORTING")
                                  for i, s in enumerate(supporting)]
                    if action is not None:
                        morphemes.append(_morpheme(action, "PRIMARY_ACTION"))
                    skeletons.append({
                        "skeleton_id": "sk-%s-%03d" % (primary["key"].replace(".", "-"),
                                                       count + 1),
                        "domain": provider["domain"], "provider": provider["providerId"],
                        "target_draft": {"t": _label(primary), "m": morphemes},
                    })
                    count += 1
        # 纯操作卡：开关做主角色
        for toggle in toggles:
            skeletons.append({
                "skeleton_id": "sk-%s-act" % toggle["key"].replace(".", "-"),
                "domain": provider["domain"], "provider": provider["providerId"],
                "target_draft": {"t": _label(toggle),
                                 "m": [_morpheme(toggle, "PRIMARY_ACTION")]},
            })
    return skeletons


def writing_prompt(skeleton):
    """给云端大模型的 query 反写指令（生成结果需人工抽审后进 queries.jsonl）。"""
    draft = skeleton["target_draft"]
    wants = "、".join("%s(%s)" % (m["l"], "操作" if "ACTION" in m["r"] else "查看")
                      for m in draft["m"])
    return ("为一张手机服务卡片写 %d 条不同的中文用户请求。用户想要：%s。"
            "要求：口语化占一半；包含 2 条省略式短句、2 条带错别字、1 条 30 字以上长句、"
            "1 条间接表达（不出现字段名但意图明确）；不要出现的功能不要提；"
            '只输出 JSON：{"skeleton_id":"%s","queries":["...",...]}'
            % (QUERIES_PER_SKELETON, wants, skeleton["skeleton_id"]))


def run_enumerate(args):
    skeletons = enumerate_skeletons()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for skeleton in skeletons:
            skeleton["query_writing_prompt"] = writing_prompt(skeleton)
            handle.write(json.dumps(skeleton, ensure_ascii=False) + "\n")
    domains = {}
    for skeleton in skeletons:
        domains[skeleton["domain"]] = domains.get(skeleton["domain"], 0) + 1
    print("骨架 %d 个 → %s" % (len(skeletons), args.output))
    for domain, count in sorted(domains.items()):
        print("  %-12s %d" % (domain, count))
    print("下一步：把每行的 query_writing_prompt 发给云端大模型，"
          "结果人工抽审后存为 queries.jsonl（每行 {skeleton_id, queries:[...]}），再跑 expand。")


def run_expand(args):
    skeletons = {}
    with args.skeletons.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                skeletons[row["skeleton_id"]] = row
    contract = None
    manifest_path = Path(__file__).resolve().parents[1] / "evals" / "prompt-manifest.json"
    if manifest_path.exists():
        info = json.loads(manifest_path.read_text(encoding="utf-8"))
        contract = {"version": info["contractVersion"], "combined": info["combined"]}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    audit_path = args.output.with_name(args.output.stem + ".audit.jsonl")
    style_names = list(STYLES)
    written = 0
    with args.output.open("w", encoding="utf-8") as sft, \
            audit_path.open("w", encoding="utf-8") as audit:
        with args.queries.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                skeleton = skeletons.get(row["skeleton_id"])
                if skeleton is None:
                    raise SystemExit("queries 引用了不存在的骨架: %s" % row["skeleton_id"])
                draft = skeleton["target_draft"]
                answer = json.dumps(draft, ensure_ascii=False, separators=(",", ":"))
                for query_index, query in enumerate(row["queries"]):
                    # 确定性选风格：原样 + 按 (query序号) 轮转再取 N-1 个变体
                    chosen = ["source"] + [style_names[1:][(query_index + offset)
                                                           % (len(style_names) - 1)]
                                           for offset in range(args.styles_per_query - 1)]
                    for style in dict.fromkeys(chosen):
                        text = STYLES[style](query)
                        # 训练样本必须复刻生产提示词（含候选键注入），否则训了也白训
                        system, user = protocol.build_messages(
                            text, "AUTO", skeleton["domain"],
                            keys_for_domain(skeleton["domain"]))
                        sft.write(json.dumps({"messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                            {"role": "assistant", "content": answer}]},
                            ensure_ascii=False) + "\n")
                        written += 1
                        audit.write(json.dumps({
                            "line": written, "skeleton_id": skeleton["skeleton_id"],
                            "domain": skeleton["domain"], "style": style,
                            "query_index": query_index, "prompt_text": text,
                            "contract": contract}, ensure_ascii=False) + "\n")
    print("SFT 样本 %d 条 → %s" % (written, args.output))
    print("审计清单 → %s（审计字段绝不进模型输入）" % audit_path)
    print("必跑：python tools/check_leakage.py --train %s --frozen evals/frozen/frozen_set_v1.jsonl"
          % args.output)


def main():
    parser = argparse.ArgumentParser(description="注册表反向数据工厂")
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("enumerate", help="枚举合法骨架")
    cmd.add_argument("--output", type=Path, default=Path("data/factory/skeletons.jsonl"))
    cmd.set_defaults(func=run_enumerate)
    cmd = sub.add_parser("expand", help="query×风格 扩增为 SFT 样本")
    cmd.add_argument("--skeletons", type=Path, default=Path("data/factory/skeletons.jsonl"))
    cmd.add_argument("--queries", type=Path, required=True)
    cmd.add_argument("--output", type=Path, default=Path("data/factory/sft_raw.jsonl"))
    cmd.add_argument("--styles-per-query", type=int, default=2,
                     help="每条 query 产出的风格变体数（含原样），默认 2")
    cmd.set_defaults(func=run_expand)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
