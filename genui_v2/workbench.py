"""GenUI v2 workbench. Run: python -m genui_v2.workbench  ->  http://127.0.0.1:8766"""
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from genui_intent.config import Settings
from genui_intent.providers import create_provider
from genui_intent.layout_engine import TEMPLATES
from . import protocol
from .capability import PROVIDERS
from .elision import plan_label_visibility
from .layout import plan as plan_layout, render_spec as build_render_spec
from .refine import coalesce
from .render import render_all
from .pipeline import PipelineV2, MockProviderV2
from .tokens import SIZES, STYLES

_LAB_TYPES = {"TEXT", "METRIC", "STATUS", "PROGRESS", "SWITCH", "SLIDER",
              "BUTTON", "LIST", "IMAGE", "ICON"}
_LAB_DEFAULT_VT = {"TEXT": "STRING", "METRIC": "NUMBER", "STATUS": "ENUM",
                   "PROGRESS": "PERCENTAGE", "SWITCH": "BOOLEAN", "SLIDER": "PERCENTAGE",
                   "BUTTON": "UNKNOWN", "LIST": "LIST", "IMAGE": "UNKNOWN", "ICON": "UNKNOWN"}


def _lab_content(kind, label, value):
    """Deterministic preview content for builder morphemes (no capability bind)."""
    if kind == "METRIC":
        return {"value": value if value not in (None, "") else 99, "unit": ""}
    if kind == "PROGRESS":
        try:
            return {"value": float(value), "min": 0, "max": 100, "unit": "%", "showValue": True}
        except (TypeError, ValueError):
            return {"value": 68, "min": 0, "max": 100, "unit": "%", "showValue": True}
    if kind == "STATUS":
        return {"text": value or "状态正常", "state": "SUCCESS"}
    if kind == "SWITCH":
        return {"checked": True, "disabled": False}
    if kind == "SLIDER":
        return {"value": 60, "min": 0, "max": 100, "step": 1, "unit": "%"}
    if kind == "BUTTON":
        return {"text": value or label or "执行", "variant": "PRIMARY", "disabled": False}
    if kind == "LIST":
        return {"items": [{"title": "列表内容 1"}, {"title": "列表内容 2"}, {"title": "列表内容 3"}]}
    if kind in ("IMAGE", "ICON"):
        return {}
    return {"text": value or label or "示例内容", "maxLines": 3}


def run_layout_test(body):
    """/api/layout-test: deterministic morphemes -> elision -> layout -> render."""
    size = body.get("size")
    if size not in ("2x1", "2x2", "3x2", "3x3"):
        raise ValueError("size 必须为 2x1/2x2/3x2/3x3")
    raw = body.get("morphemes")
    if not isinstance(raw, list) or not 0 < len(raw) <= 20:
        raise ValueError("morphemes 必须为 1-20 项")
    morphemes = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict) or item.get("type") not in _LAB_TYPES:
            raise ValueError("morphemes[%d].type 非法" % index)
        kind = item["type"]
        role = item.get("role") or ("PRIMARY" if index == 0 else
                                    "PRIMARY_ACTION" if kind in ("BUTTON", "SWITCH", "SLIDER")
                                    else "SECONDARY")
        if role not in protocol.ROLE_PRIORITY:
            raise ValueError("morphemes[%d].role 非法" % index)
        label = str(item.get("label") or kind)[:40]
        value_type = item.get("valueType") or _LAB_DEFAULT_VT[kind]
        content = item.get("content") if isinstance(item.get("content"), dict) else \
            _lab_content(kind, label, item.get("value"))
        priority = item.get("priority")
        morphemes.append({
            "id": "t%d" % (index + 1), "type": kind, "role": role,
            "priority": max(0, min(100, int(priority))) if isinstance(priority, (int, float))
            else protocol.ROLE_PRIORITY[role],
            "label": label, "semanticKey": str(item.get("q") or "lab." + kind.lower()),
            "valueType": value_type, "content": content, "presentation": {}})
    spec = {"version": "0.3", "scene": "layout_lab", "title": str(body.get("title") or "")[:40] or None,
            "surface": {"type": "CARD", "size": size, "density": "AUTO"}, "morphemes": morphemes}
    spec, coalesce_notes = coalesce(spec)
    spec, label_decisions = plan_label_visibility(spec)
    layout = plan_layout(spec, body.get("style_id", "light"), None)
    rendered_spec = build_render_spec(spec, layout)
    outputs = render_all(rendered_spec)
    return {"morphemeSpec": spec, "labelDecisions": label_decisions,
            "coalesceNotes": coalesce_notes, "layout": layout,
            "renderSpec": rendered_spec, "outputs": outputs,
            "code": outputs["html_css"]["standalone"]}

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web_v2"
LEGACY_ASSETS = ROOT / "web" / "assets"
TOKEN = secrets.token_urlsafe(32)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, content, mime):
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            content = (WEB / "index.html").read_text(encoding="utf-8")
            self._send(content.replace("__REQUEST_TOKEN__", TOKEN).encode("utf-8"),
                       "text/html; charset=utf-8")
            return
        if path == "/api/templates":
            payload = {"sizes": SIZES, "templates": TEMPLATES}
            self._send(json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")
            return
        if path == "/api/registry":
            self._send(json.dumps(PROVIDERS, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")
            return
        if path == "/api/meta":
            payload = {"systemPrompt": protocol.SYSTEM_PROMPT, "fewshot": protocol.FEWSHOT,
                       "sizeLimits": protocol.SIZE_LIMITS, "sizeBudgets": protocol.SIZE_BUDGETS,
                       "componentCost": protocol.COMPONENT_COST,
                       "rolePriority": protocol.ROLE_PRIORITY,
                       "styles": {key: value["label"] for key, value in STYLES.items()},
                       "schemaExample": protocol.schema("2x2")}
            self._send(json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")
            return
        if path.startswith("/assets/") and path.endswith(".jpg") and "/.." not in path:
            target = LEGACY_ASSETS / path[len("/assets/"):]
            if target.is_file() and target.resolve().is_relative_to(LEGACY_ASSETS.resolve()):
                self._send(target.read_bytes(), "image/jpeg")
                return
        self.send_error(404)

    def do_POST(self):
        if self.path not in ("/api/run", "/api/layout-test"):
            self.send_error(404)
            return
        if self.headers.get("X-Workbench-Token") != TOKEN:
            self.send_error(403)
            return
        if self.path == "/api/layout-test":
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size < 100000:
                    raise ValueError("请求大小无效")
                body = json.loads(self.rfile.read(size))
                result = run_layout_test(body)
            except Exception as exc:
                self.send_error(400, str(exc).encode("ascii", "replace").decode())
                return
            self._send(json.dumps(result, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size < 100000:
                raise ValueError("请求大小无效")
            body = json.loads(self.rfile.read(size))
            prompt = body.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("请输入提示词")
            provider_name = body.get("provider", "ollama")
            if provider_name == "mock":
                client = MockProviderV2()
            else:
                base = str(body.get("base_url", "")).rstrip("/")
                url = urlparse(base)
                if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
                    raise ValueError("API 地址应为不含凭据的 HTTP(S) 地址")
                if url.scheme == "http" and url.hostname not in ("localhost", "127.0.0.1", "::1"):
                    raise ValueError("外部 API 请使用 HTTPS")
                settings = Settings(provider_name, body.get("model", ""), base, body.get("api_key", ""),
                                    max(5, min(600, float(body.get("timeout", 180)))),
                                    body.get("response_mode", "json_schema"))
                client = create_provider(settings)
            card_size = body.get("card_size", "AUTO")
            style_id = body.get("style_id", "auto")
            features = body.get("features") if isinstance(body.get("features"), dict) else None
        except Exception as exc:
            self.send_error(400, str(exc).encode("ascii", "replace").decode())
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        api_key = str(body.get("api_key", ""))

        def send(event):
            data = json.dumps(event, ensure_ascii=False)
            if api_key:
                data = data.replace(api_key, "[REDACTED]")
            self.wfile.write((data + "\n").encode("utf-8"))
            self.wfile.flush()

        try:
            PipelineV2(client, on_event=send, features=features).generate(prompt, card_size, style_id)
            send({"type": "done", "ok": True})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            send({"type": "done", "ok": False, "error": str(exc)})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8766), Handler)
    print("GenUI v2 Workbench: http://127.0.0.1:8766", flush=True)
    server.serve_forever()
