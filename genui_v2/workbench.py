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
from .pipeline import PipelineV2, MockProviderV2
from .tokens import SIZES, STYLES

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
        if self.path != "/api/run":
            self.send_error(404)
            return
        if self.headers.get("X-Workbench-Token") != TOKEN:
            self.send_error(403)
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
            PipelineV2(client, on_event=send).generate(prompt, card_size, style_id)
            send({"type": "done", "ok": True})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            send({"type": "done", "ok": False, "error": str(exc)})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8766), Handler)
    print("GenUI v2 Workbench: http://127.0.0.1:8766", flush=True)
    server.serve_forever()
