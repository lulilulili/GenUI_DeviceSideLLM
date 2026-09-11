"""从实习生 A2UI 数据中提炼适用于本项目冻结集的候选草稿。

只借三样东西，丢弃其余：
- user_prompt 措辞（runtime_context 一律丢弃——本架构没有"可信工具结果"输入）；
- 领域分布与选型对比案例；
- 来源审计（seed id / 域 / 模板）作为 provenance。

产出全部标 status=draft + needsReview，必须逐条人审后才允许并入 frozen_set_v1。

用法：python tools/distill_intern_testset.py
输入：实习生数据整理/02-种子与扩展数据/
输出：evals/frozen/intern_distilled_draft.jsonl
      evals/frozen/intern_distilled_report.json
      evals/frozen/intern_used_seed_ids.txt   ← 将来若借实习生数据做训练，
                                                这些 seed 及其全部变体必须排除
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "实习生数据整理" / "02-种子与扩展数据"
OUT_DIR = ROOT / "evals" / "frozen"
sys.path.insert(0, str(ROOT))

from genui_v2.router import rule_route  # noqa: E402

# 模板化/结构化指令味道的标记：命中即视为"非纯自然语言"，默认降级排除
_TEMPLATED_MARKERS = ("以下信息", "每条记录", "保留", "字段", "标题和", "记录的",
                      "按照", "格式", "以上内容", "如下", "：G", "：D")
_META_MARKERS = ("以下", "记录", "保留")


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _normalize(text: str) -> str:
    return re.sub(r"[\s，。！？,.!?、]", "", text)


def _is_natural(prompt: str) -> bool:
    return not any(marker in prompt for marker in _TEMPLATED_MARKERS)


def collect() -> list[dict]:
    records = []
    for seed in _load_jsonl(DATA / "01-V4种子144" / "seeds-144.jsonl"):
        records.append({"prompt": seed["user_prompt"].strip(),
                        "origin": "seed:" + seed["sample_id"],
                        "seedId": seed["sample_id"],
                        "macroDomain": seed.get("macro_domain"),
                        "internTemplate": seed.get("target_frame", {}).get("templateId")})
    for row in _load_jsonl(DATA / "02-V4扩展5000" / "experiment-288" / "test-manifest-288.jsonl"):
        records.append({"prompt": row["user_prompt"].strip(),
                        "origin": "test288:" + str(row.get("sample_id")),
                        "seedId": row.get("source_seed_id"),
                        "macroDomain": row.get("macro_domain"),
                        "internTemplate": (row.get("target_frame") or {}).get("templateId"),
                        "dialogueStyle": row.get("dialogue_style")})
    for case in _load_jsonl(DATA / "01-V4种子144" / "boundary-cases.jsonl"):
        if case.get("kind") != "selection_contrast" or not case.get("user_prompt"):
            continue
        records.append({"prompt": case["user_prompt"].strip(),
                        "origin": "contrast:" + case["id"], "seedId": None,
                        "macroDomain": "选型对比", "contrastReason": case.get("reason"),
                        "internTemplate": (case.get("target_frame") or {}).get("templateId")})
    return records


def main() -> int:
    raw = collect()
    seen, unique = set(), []
    for record in raw:
        key = _normalize(record["prompt"])
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(record)

    drafts, used_seeds = [], set()
    counter = Counter()
    for index, record in enumerate(unique):
        prompt = record["prompt"]
        natural = _is_natural(prompt)
        domain = rule_route(prompt)
        if record["origin"].startswith("contrast:"):
            bucket = "contrast_candidate"
        elif domain is None:
            bucket = "unsupported_candidate"
        else:
            bucket = "candidate_" + domain
        counter[(bucket, natural)] += 1
        expected = {"reject": domain is None}
        if domain:
            expected["domain"] = domain
        drafts.append({
            "id": "intern-%03d" % (index + 1),
            "bucket": bucket,
            "prompt": prompt,
            "expected": expected,
            "naturalLanguage": natural,
            "provenance": {k: v for k, v in record.items() if k != "prompt"},
            "needsReview": True,
            "status": "draft",
        })
        if record.get("seedId"):
            used_seeds.add(record["seedId"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    draft_path = OUT_DIR / "intern_distilled_draft.jsonl"
    with draft_path.open("w", encoding="utf-8") as handle:
        for draft in drafts:
            handle.write(json.dumps(draft, ensure_ascii=False) + "\n")
    (OUT_DIR / "intern_used_seed_ids.txt").write_text(
        "\n".join(sorted(used_seeds)), encoding="utf-8")

    bucket_stats = {}
    for (bucket, natural), count in sorted(counter.items()):
        entry = bucket_stats.setdefault(bucket, {"natural": 0, "templated": 0})
        entry["natural" if natural else "templated"] += count
    macro = Counter(d["provenance"].get("macroDomain") for d in drafts)
    report = {"totalRaw": len(raw), "unique": len(unique),
              "buckets": bucket_stats, "macroDomains": dict(macro.most_common()),
              "usedSeedIds": len(used_seeds),
              "note": "candidate_* 需人审定桶（sde/dom/paraphrase）并补 morphemes 期望；"
                      "unsupported_candidate 人审确认注册表确实无法覆盖后改 bucket=unsupported；"
                      "templated 措辞默认不用，除非人工改写成口语。"}
    (OUT_DIR / "intern_distilled_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
