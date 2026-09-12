"""Build a reproducible GD morpheme SFT dataset from the frozen registry."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from genui_v2 import protocol
from genui_v2.capability import PROVIDERS

ROOT = Path(__file__).resolve().parents[1]


def _label(entry: dict) -> str:
    aliases = [alias for alias in entry.get("aliases", []) if not alias.isascii() and len(alias) >= 2]
    return min(aliases, key=len) if aliases else entry["key"].split(".")[-1]


def _draft(entry: dict, role: str = "PRIMARY") -> dict:
    return {"l": _label(entry), "q": entry["key"], "f": entry["valueType"], "r": role}


def enumerate_skeletons() -> list[dict]:
    skeletons = []
    for provider in PROVIDERS:
        info = [entry for entry in provider["entries"] if entry.get("path")
                and entry["valueType"] != "BOOLEAN" and not entry.get("generator")]
        actions = [entry for entry in provider["entries"] if entry["valueType"] == "BOOLEAN" and entry.get("action")]
        for primary in info:
            siblings = [entry for entry in info if entry["key"] != primary["key"]]
            combinations = [()] + [(entry,) for entry in siblings[:3]]
            combinations += [(siblings[0], siblings[1])] if len(siblings) >= 2 else []
            for index, supporting in enumerate(combinations[:6]):
                morphemes = [_draft(primary)]
                for support_index, entry in enumerate(supporting):
                    morphemes.append(_draft(entry, "SECONDARY" if support_index == 0 else "SUPPORTING"))
                if actions and index % 2 == 1:
                    morphemes.append(_draft(actions[0], "PRIMARY_ACTION"))
                skeletons.append({"skeleton_id": f"sk-{primary['key'].replace('.', '-')}-{index + 1:03d}",
                                  "domain": provider["domain"], "target_draft": {"t": _label(primary), "m": morphemes}})
        for action in actions:
            skeletons.append({"skeleton_id": f"sk-{action['key'].replace('.', '-')}-act",
                              "domain": provider["domain"],
                              "target_draft": {"t": _label(action), "m": [_draft(action, "PRIMARY_ACTION")]}})
    return skeletons


def _queries(skeleton: dict, count: int) -> list[str]:
    draft = skeleton["target_draft"]
    labels = [item["l"] for item in draft["m"]]
    actions = [item for item in draft["m"] if "ACTION" in item["r"]]
    shown = "、".join(labels)
    suffix = "，点一下可操作" if actions else ""
    templates = [
        f"帮我看看{shown}{suffix}。", f"我想在卡片上看到{shown}{suffix}。",
        f"做一张{shown}卡片{suffix}。", f"桌面显示{shown}就行{suffix}。",
        f"请把{shown}整理成一张小卡片{suffix}。", f"我需要一个能查看{shown}的卡片{suffix}。",
        f"给我来个{shown}信息卡{suffix}。", f"麻烦展示一下{shown}{suffix}。",
        f"能不能快速显示{shown}{suffix}？", f"只保留{shown}，做成卡片。",
        f"我想随时知道{shown}{suffix}。", f"请生成桌面小组件，内容是{shown}{suffix}。",
        f"不用复杂布局，显示{shown}{suffix}即可。", f"帮我把{shown}放到桌面。",
        f"看一下{shown}，做成简洁卡片。", f"卡片里展示{shown}{suffix}。",
        f"现在给我{shown}的摘要{suffix}。", f"想快速了解{shown}{suffix}。",
        f"做个方便查看{shown}的服务卡。", f"请在桌面安排{shown}{suffix}。",
        f"我只想看{shown}{suffix}。", f"帮我准备{shown}的卡片。",
        f"给我一个{shown}概览{suffix}。", f"卡片显示：{shown}{suffix}。",
        f"请做个{shown}小工具{suffix}。", f"我需要{shown}的简短信息。",
        f"帮我在手机上查看{shown}{suffix}。", f"桌面放一个{shown}入口{suffix}。",
        f"可以把{shown}做成小卡片吗{suffix}？", f"请生成一个只包含{shown}的卡片。",
        f"想看{shown}，不用展示其他内容。", f"做一张简洁的{shown}卡片。",
        f"给我展示{shown}的当前状态{suffix}。", f"帮我快速查看{shown}。",
        f"在卡片中放入{shown}{suffix}。", f"我想要{shown}的桌面卡片。",
    ]
    return templates[:count]


def _row(skeleton: dict, query: str) -> dict:
    system, user = protocol.build_messages(query, "AUTO", skeleton["domain"],
                                            tuple(item["q"] for item in skeleton["target_draft"]["m"]))
    return {"task": "morpheme", "skeleton_id": skeleton["skeleton_id"],
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user},
                         {"role": "assistant", "content": json.dumps(skeleton["target_draft"], ensure_ascii=False, separators=(",", ":"))}]}


def build_dataset(output_dir: Path, variants_per_skeleton: int = 36) -> dict:
    skeletons = enumerate_skeletons()
    rows = []
    audits = []
    for skeleton in skeletons:
        for index, query in enumerate(_queries(skeleton, variants_per_skeleton)):
            rows.append(_row(skeleton, query))
            audits.append({"line": len(rows), "skeleton_id": skeleton["skeleton_id"], "query": query,
                           "domain": skeleton["domain"], "variant": index, "contract": "morpheme-v2"})
    output_dir.mkdir(parents=True, exist_ok=True)
    splits = {"train": [], "dev": [], "test": []}
    for row in rows:
        digest = int(hashlib.md5(row["skeleton_id"].encode()).hexdigest()[:2], 16) % 10
        split = "test" if digest == 0 else "dev" if digest == 1 else "train"
        splits[split].append(row)
    for name, values in splits.items():
        (output_dir / f"gd_{name}.jsonl").write_text(
            "".join(json.dumps(value, ensure_ascii=False) + "\n" for value in values), encoding="utf-8")
    (output_dir / "gd_all.audit.jsonl").write_text(
        "".join(json.dumps(value, ensure_ascii=False) + "\n" for value in audits), encoding="utf-8")
    counts = Counter(row["task"] for row in rows)
    card = {"dataset": "gd-morpheme-3b-sft-v1", "source": "GenUI v2 capability registry",
            "contract": "morpheme-v2", "model_output": "t + m[l,q,f,r] only",
            "counts": {"total": len(rows), **dict(counts)},
            "split": {name: len(values) for name, values in splits.items()},
            "skeletons": len(skeletons),
            "intern_asset_policy": "intern V4 Frame data is evaluation/reference only; not mixed into morpheme SFT",
            "limitations": ["deterministic paraphrases need human review", "registry coverage defines answer space"]}
    (output_dir / "gd_dataset_card.json").write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
    return card


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "datasets" / "gd-morpheme-3b-v1")
    parser.add_argument("--variants-per-skeleton", type=int, default=36)
    args = parser.parse_args()
    print(json.dumps(build_dataset(args.output, args.variants_per_skeleton), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
