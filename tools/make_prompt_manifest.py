"""冻结提示词契约：生成/校验 evals/prompt-manifest.json。

为什么需要它（借鉴实习生 A2UI 工作的做法——他的 meta-prompt.txt 带 SHA256，
每条数据带 contract_version，评测报告绑定提示词哈希）：

  训练数据和评测结果都依附于"当时的提示词+schema+注册表键名"。任何一样悄悄
  变了，旧数据/旧分数就作废却无人察觉。本工具把所有会影响模型行为的文本
  逐一取 SHA256 存档；训练前 --write 一次，之后每次评测/造数据前 --check，
  漂移即报错，逼着你显式升版本。

用法：
  python tools/make_prompt_manifest.py --write   # 冻结当前契约（升版本时用）
  python tools/make_prompt_manifest.py --check   # 校验代码与清单一致（日常用）
"""
import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from genui_v2 import protocol
from genui_v2.capability import DOMAINS, keys_for_domain

MANIFEST_PATH = Path(__file__).resolve().parents[1] / "evals" / "prompt-manifest.json"


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect():
    """一切会改变模型所见输入或合法输出空间的文本，都在这里登记。"""
    artifacts = {
        "system_prompt": protocol.SYSTEM_PROMPT,
        "fewshot": protocol.FEWSHOT,
        "router_system": "你是领域路由器。只输出一个枚举：" + "|".join(DOMAINS + ["UNKNOWN"]),
        # 用固定输入渲染一次 build_messages，锁住候选注入的拼装格式本身
        "message_template_sample": "\n".join(protocol.build_messages(
            "示例请求", "2x2", "DEVICE", ("a.b", "c.d"))),
    }
    for size in protocol.SIZE_LIMITS:
        artifacts["schema_" + size] = json.dumps(protocol.schema(size),
                                                 ensure_ascii=False, sort_keys=True)
    for domain in DOMAINS:
        artifacts["registry_keys_" + domain] = ",".join(keys_for_domain(domain))
    return artifacts


def build_manifest():
    artifacts = collect()
    hashes = {name: _sha(text) for name, text in sorted(artifacts.items())}
    combined = _sha(json.dumps(hashes, sort_keys=True))
    return {"contractVersion": "morpheme-v2-" + date.today().isoformat(),
            "combined": combined, "artifacts": hashes,
            "note": "训练数据与评测报告必须引用 combined 哈希；代码改动后先 --check 发现漂移，确认后 --write 升版本。"}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    current = build_manifest()
    if args.write:
        MANIFEST_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
        print("已写入", MANIFEST_PATH)
        print("contractVersion:", current["contractVersion"])
        print("combined:", current["combined"])
        return
    if not MANIFEST_PATH.exists():
        raise SystemExit("清单不存在，先运行 --write 冻结一次")
    frozen = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    drifted = [name for name, digest in current["artifacts"].items()
               if frozen["artifacts"].get(name) != digest]
    missing = [name for name in frozen["artifacts"] if name not in current["artifacts"]]
    if not drifted and not missing:
        print("契约一致：", frozen["contractVersion"], frozen["combined"][:16])
        return
    for name in drifted:
        print("漂移:", name)
    for name in missing:
        print("清单有但代码已无:", name)
    raise SystemExit("提示词契约已漂移。若是有意修改，请重新 --write 并在数据卡/报告中升版本；"
                     "旧训练数据与旧评测分数不可再与新契约混用。")


if __name__ == "__main__":
    main()
