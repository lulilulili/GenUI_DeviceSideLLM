"""Compare one-pass and optional LLM semantic review against local Ollama."""
import json
import re
import time
import urllib.request

BASE = "http://127.0.0.1:8765"
CASES = [
    ("contacts", "生成一张常用联系人服务卡片，按照2x2尺寸组织信息，重点突出常用联系人的核心内容，并提供必要的状态、数据或操作。"),
    ("meeting", "生成会议室卡片，显示当前占用状态、容纳人数，并提供预订按钮。"),
    ("download", "生成下载任务卡片，显示文件名和下载进度，并提供暂停按钮。"),
    ("lighting", "生成灯光控制卡片，显示当前开关状态，提供开关和亮度滑杆。"),
]


def run(prompt, review):
    page = urllib.request.urlopen(BASE + "/").read().decode("utf-8")
    token = re.search(r'request-token" content="([^"]+)', page).group(1)
    payload = {"prompt": prompt, "provider": "ollama", "base_url": "http://127.0.0.1:11434",
               "model": "qwen2.5:3b", "flow": "morpheme", "card_size": "2x2",
               "render_protocol": "dsl", "style_id": "neutral", "timeout": 180,
               "semantic_review": review}
    request = urllib.request.Request(BASE + "/api/run", json.dumps(payload).encode(),
                                     {"Content-Type": "application/json", "X-Workbench-Token": token})
    started = time.perf_counter()
    events = [json.loads(line) for line in urllib.request.urlopen(request, timeout=190).read().decode().splitlines()]
    result = next(e["output"] for e in events if e.get("stage") == "result")
    calls = [e for e in events if e.get("stage", "").startswith("model_call") and e.get("status") == "completed"]
    usage = {key: sum((e.get("usage") or {}).get(key, 0) for e in calls) for key in ("inputTokens", "outputTokens")}
    compact = [{key: item[key] for key in ("type", "role", "label", "semanticKey", "valueType")}
               for item in result["morphemeSpec"]["morphemes"]]
    return {"elapsedSeconds": round(time.perf_counter() - started, 2), "usage": usage, "morphemes": compact}


if __name__ == "__main__":
    results = []
    for case_id, prompt in CASES:
        for review in (False, True):
            outcome = run(prompt, review)
            results.append({"case": case_id, "review": review, **outcome})
            print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    print(json.dumps(results, ensure_ascii=False, indent=2))
