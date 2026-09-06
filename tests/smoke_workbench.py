"""Manual HTTP integration smoke; local Ollama must be running."""
import json
import re
import urllib.request

root = "http://127.0.0.1:8765"
html = urllib.request.urlopen(root).read().decode()
token = re.search(r'name="request-token" content="([^"]+)', html).group(1)
body = json.dumps(dict(provider="ollama", model="qwen2.5:3b",
    base_url="http://127.0.0.1:11434", prompt="看看客厅灯现在开着没有", timeout=180)).encode()
request = urllib.request.Request(root + "/api/run", body,
    {"Content-Type": "application/json", "X-Workbench-Token": token})
events = []
with urllib.request.urlopen(request, timeout=240) as response:
    for line in response:
        event = json.loads(line)
        events.append(event)
        print(json.dumps({k: v for k, v in event.items()
            if k in ("stage", "status", "elapsedMs", "usage", "type", "ok", "error")}), flush=True)
assert events[-1] == {"type": "done", "ok": True}
assert any(e.get("usage", {}).get("outputTokens") for e in events if e.get("usage"))
