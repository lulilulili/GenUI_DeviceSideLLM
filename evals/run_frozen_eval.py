"""冻结集评测 harness：跑 v2 语素管线，输出可对比的结构化报告。

设计上吸收了实习生 A2UI 评测的三个经验：
1. 诊断指标成对出现——"动作幻觉率 vs 动作遗漏率"能一眼定位模型是爱多加
   按钮还是漏动作（他的数据：幻觉 32.9% vs 遗漏 0.2%，3B 系统性多加）；
2. 拒绝类用例的底线是"不假绑"，并区分假绑来源（模型编键被 EXACT/ALIAS
   接住 vs TOKENS 兜底层过于宽松）——修复方向完全不同；
3. 记忆切片：--train-file 提供训练集时，按"该用例期望键组合是否在训练集
   出现过"分组报分。两组分差大 = 分数里有记忆水分（他的教训：195/288 条
   测试答案与示例重复，'答案不同'子集分数低 20pt）。

用法：
  python evals/run_frozen_eval.py --dataset evals/frozen/frozen_set_template.jsonl --provider mock
  python evals/run_frozen_eval.py --dataset evals/frozen/frozen_set_v1.jsonl --model qwen2.5:3b \
      --output evals/results/frozen-qwen3b-baseline.json
"""
import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from genui_intent.config import Settings
from genui_intent.providers import create_provider
from genui_v2.capability import BY_KEY
from genui_v2.pipeline import MockProviderV2, PipelineV2

BUCKETS = ("single_domain_explicit", "domain_only", "paraphrase_longtail",
           "negation_correction", "cross_domain", "unsupported", "multi_action",
           "out_of_field")


def load_dataset(path):
    cases = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            case = json.loads(line)
            for field in ("id", "bucket", "prompt", "expected"):
                if field not in case:
                    raise SystemExit("第%d行缺少字段 %s" % (line_number, field))
            if case["bucket"] not in BUCKETS:
                raise SystemExit("第%d行 bucket 非法: %s" % (line_number, case["bucket"]))
            for morpheme in case["expected"].get("morphemes", []):
                for key in morpheme["keys"]:
                    if key not in BY_KEY:
                        raise SystemExit("%s: 期望键 %s 不在注册表中（先修数据再评测）"
                                         % (case["id"], key))
            for key in case["expected"].get("forbidden_keys", []):
                if key not in BY_KEY:
                    raise SystemExit("%s: forbidden 键 %s 不在注册表中" % (case["id"], key))
            cases.append(case)
    return cases


def score_case(case, result, repaired):
    """返回该用例的逐项评分。produced 取模型草稿+绑定报告（联想补充不算模型的账）。"""
    expected = case["expected"]
    report = result["bindReport"]
    draft_items = result["draft"]["m"]
    produced = []
    for index, row in enumerate(report):
        role = draft_items[index]["r"] if index < len(draft_items) else None
        produced.append({"q": row["q"], "resolution": row["resolution"],
                         "bound_key": row["key"], "role": role})
    score = {"id": case["id"], "bucket": case["bucket"], "prompt": case["prompt"],
             "produced": produced, "repaired": repaired, "error": None}

    if expected.get("reject"):
        false_hard = [p for p in produced if p["resolution"] in ("EXACT", "ALIAS")]
        false_soft = [p for p in produced if p["resolution"] == "TOKENS"]
        score.update({"reject_expected": True,
                      "false_bind_exact_alias": len(false_hard),
                      "false_bind_tokens": len(false_soft),
                      "case_pass": not false_hard and not false_soft})
        return score

    domain_ok = (expected.get("domain") is None
                 or result["domain"] == expected["domain"])
    acceptable = set()
    matched_roles, required_hits, required_total = [], 0, 0
    for morpheme in expected.get("morphemes", []):
        acceptable.update(morpheme["keys"])
        hit = next((p for p in produced if p["bound_key"] in morpheme["keys"]), None)
        if not morpheme.get("optional"):
            required_total += 1
            if hit:
                required_hits += 1
        if hit:
            matched_roles.append(hit["role"] == morpheme["role"])
    precision_hits = sum(1 for p in produced if p["bound_key"] in acceptable)
    forbidden_hits = [p["bound_key"] for p in produced
                      if p["bound_key"] in set(expected.get("forbidden_keys", []))]
    produced_actions = sum(1 for p in produced if p["role"] and "ACTION" in p["role"])
    expected_actions = sum(1 for m in expected.get("morphemes", [])
                           if "ACTION" in m["role"] and not m.get("optional"))
    max_actions = expected.get("max_actions", 99)
    score.update({
        "reject_expected": False, "domain_ok": domain_ok,
        "domain_expected": expected.get("domain"), "domain_actual": result["domain"],
        "required_hits": required_hits, "required_total": required_total,
        "precision_hits": precision_hits, "produced_total": len(produced),
        "role_hits": sum(matched_roles), "role_total": len(matched_roles),
        "exact_binds": sum(1 for p in produced if p["resolution"] == "EXACT"),
        "forbidden_hits": forbidden_hits,
        "action_hallucinated": produced_actions > max_actions,
        "action_omitted": expected_actions > 0 and produced_actions == 0,
        "case_pass": (domain_ok and required_hits == required_total
                      and not forbidden_hits and produced_actions <= max_actions),
    })
    return score


def load_train_keysets(path):
    """从训练集提取每条样本的语素键组合（用于记忆切片）。
    支持 messages 格式（assistant 是草稿 JSON）或直接含 target_draft 的行。"""
    keysets = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            draft = row.get("target_draft")
            if draft is None and "messages" in row:
                assistant = next((m["content"] for m in row["messages"]
                                  if m.get("role") == "assistant"), None)
                if assistant:
                    try:
                        draft = json.loads(assistant)
                    except ValueError:
                        continue
            if isinstance(draft, dict) and isinstance(draft.get("m"), list):
                keys = frozenset(item.get("q", "") for item in draft["m"])
                if keys:
                    keysets.add(keys)
    return keysets


def case_keyset(case):
    return frozenset(m["keys"][0] for m in case["expected"].get("morphemes", []))


def aggregate(rows):
    """把逐用例评分聚合成一组指标；rows 为空时返回 None。"""
    if not rows:
        return None
    normal = [r for r in rows if not r["reject_expected"] and not r["error"]]
    reject = [r for r in rows if r["reject_expected"] and not r["error"]]
    errors = [r for r in rows if r["error"]]
    out = {"cases": len(rows), "errors": len(errors),
           "case_pass_rate": _ratio(sum(r.get("case_pass", False) for r in rows), len(rows)),
           "first_pass_rate": _ratio(sum(not r["repaired"] for r in rows if not r["error"]),
                                     max(1, len(rows) - len(errors)))}
    if normal:
        recall = _ratio(sum(r["required_hits"] for r in normal),
                        sum(r["required_total"] for r in normal))
        precision = _ratio(sum(r["precision_hits"] for r in normal),
                           sum(r["produced_total"] for r in normal))
        f1 = (0.0 if not precision or not recall
              else round(2 * precision * recall / (precision + recall), 4))
        out.update({
            "domain_acc": _ratio(sum(r["domain_ok"] for r in normal), len(normal)),
            "key_recall": recall, "key_precision": precision, "key_f1": f1,
            "role_acc": _ratio(sum(r["role_hits"] for r in normal),
                               sum(r["role_total"] for r in normal)),
            "exact_bind_rate": _ratio(sum(r["exact_binds"] for r in normal),
                                      sum(r["produced_total"] for r in normal)),
            "forbidden_violations": sum(len(r["forbidden_hits"]) for r in normal),
            "action_hallucination_rate": _ratio(sum(r["action_hallucinated"] for r in normal),
                                                len(normal)),
            "action_omission_rate": _ratio(sum(r["action_omitted"] for r in normal),
                                           len(normal)),
        })
    if reject:
        out["reject"] = {
            "cases": len(reject),
            "pass_rate": _ratio(sum(r["case_pass"] for r in reject), len(reject)),
            "false_bind_exact_alias": sum(r["false_bind_exact_alias"] for r in reject),
            "false_bind_tokens": sum(r["false_bind_tokens"] for r in reject),
        }
    return out


def _ratio(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def main():
    parser = argparse.ArgumentParser(description="冻结集评测（v2 语素管线）")
    parser.add_argument("--dataset", type=Path,
                        default=Path("evals/frozen/frozen_set_v1.jsonl"))
    parser.add_argument("--provider", default="ollama", choices=["ollama", "mock"])
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--train-file", type=Path,
                        help="训练集 jsonl；给出后按'期望键组合是否在训练集出现'切片报分")
    parser.add_argument("--output", type=Path, default=Path("evals/results/frozen-latest.json"))
    args = parser.parse_args()

    cases = load_dataset(args.dataset)
    if args.limit:
        cases = cases[: args.limit]
    train_keysets = load_train_keysets(args.train_file) if args.train_file else None

    def make_pipeline(events):
        if args.provider == "mock":
            client = MockProviderV2()
        else:
            client = create_provider(Settings("ollama", args.model,
                                              args.base_url.rstrip("/"), "", args.timeout))
        return PipelineV2(client, on_event=events.append)

    rows, durations = [], []
    print("评测 %d 条 · provider=%s model=%s" % (len(cases), args.provider, args.model), flush=True)
    for position, case in enumerate(cases, 1):
        events = []
        started = time.perf_counter()
        try:
            result = make_pipeline(events).generate(case["prompt"])
            repaired = any(e.get("stage") == "repair" for e in events)
            row = score_case(case, result, repaired)
        except Exception as exc:
            row = {"id": case["id"], "bucket": case["bucket"], "prompt": case["prompt"],
                   "reject_expected": bool(case["expected"].get("reject")),
                   "case_pass": False, "repaired": False, "error": str(exc)}
        row["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
        durations.append(row["elapsed_ms"])
        if train_keysets is not None:
            row["keyset_seen_in_train"] = case_keyset(case) in train_keysets
        rows.append(row)
        print("[%03d/%03d] %s %s %.0fms" % (position, len(cases),
                                            "PASS" if row["case_pass"] else "FAIL",
                                            case["id"], row["elapsed_ms"]), flush=True)

    by_bucket = defaultdict(list)
    for row in rows:
        by_bucket[row["bucket"]].append(row)
    summary = {"dataset": str(args.dataset), "provider": args.provider,
               "model": args.model if args.provider == "ollama" else "mock",
               "overall": aggregate(rows),
               "buckets": {bucket: aggregate(items) for bucket, items in sorted(by_bucket.items())},
               "latency_ms": {"p50": statistics.median(durations),
                              "p95": sorted(durations)[max(0, int(len(durations) * 0.95) - 1)]}}
    manifest_path = Path(__file__).resolve().parent / "prompt-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        summary["prompt_contract"] = {"version": manifest["contractVersion"],
                                      "combined": manifest["combined"]}
    if train_keysets is not None:
        seen = [r for r in rows if r.get("keyset_seen_in_train")]
        unseen = [r for r in rows if not r.get("keyset_seen_in_train")]
        summary["memorization_slices"] = {"seen_keyset": aggregate(seen),
                                          "unseen_keyset": aggregate(unseen)}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    detail_path = args.output.with_suffix(".cases.jsonl")
    with detail_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("\n== 总体 ==")
    for name, value in summary["overall"].items():
        print("%s: %s" % (name, value))
    print("\n== 分桶 case_pass_rate ==")
    for bucket, stats in summary["buckets"].items():
        print("%-24s %s (%d 条)" % (bucket, stats["case_pass_rate"], stats["cases"]))
    if "memorization_slices" in summary:
        slices = summary["memorization_slices"]
        print("\n== 记忆切片 ==")
        for name in ("seen_keyset", "unseen_keyset"):
            stats = slices[name]
            print("%s: %s" % (name, "无用例" if stats is None else
                              "case_pass=%s f1=%s (%d 条)" % (stats["case_pass_rate"],
                                                              stats.get("key_f1"), stats["cases"])))
        print("提示：两组分差大说明分数含记忆水分，冻结集或训练集需要重新隔离。")
    print("\n报告: %s\n逐条: %s" % (args.output, detail_path))


if __name__ == "__main__":
    main()
