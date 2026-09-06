"""Local-only workbench. Run: python -m genui_intent.workbench"""
import json
import re
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from .config import Settings
from .providers import create_provider
from .pipeline import IntentPipeline
from .morpheme_pipeline import MorphemePipeline
from .layout_engine import plan as plan_layout, render_spec as build_render_spec
from .renderers import render as render_output

ROOT = Path(__file__).resolve().parents[1] / "web"
TOKEN = secrets.token_urlsafe(32)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = urlparse(self.path).path
        case_match = re.fullmatch(r"/assets/pdf-cases/(P[1-4]-\d{2}\.jpg)", path)
        if case_match:
            content = (ROOT / "assets" / "pdf-cases" / case_match.group(1)).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers(); self.wfile.write(content)
            return
        files = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
                 "/style.css": ("style.css", "text/css"), "/preview.css": ("preview.css", "text/css"),
                 "/preview-sizing.css": ("preview-sizing.css", "text/css"),
                 "/dark.css": ("dark.css", "text/css"),
                 "/docs.css": ("docs.css", "text/css"), "/graph.css": ("graph.css", "text/css"),
                 "/docs.js": ("docs.js", "text/javascript"),
                 "/architecture-examples.css": ("architecture-examples.css", "text/css"),
                 "/layout-decision.js": ("layout-decision.js", "text/javascript"),
                 "/layout-decision.css": ("layout-decision.css", "text/css"),
                 "/layout.css": ("layout.css", "text/css"),
                 "/layout.js": ("layout.js", "text/javascript"),
                 "/layout-scoring.js": ("layout-scoring.js", "text/javascript"),
                 "/layout-scoring.css": ("layout-scoring.css", "text/css"),
                 "/morpheme-viz.js": ("morpheme-viz.js", "text/javascript"),
                 "/diagrams.css": ("diagrams.css", "text/css"),
                 "/pdf-tests.js": ("pdf-tests.js", "text/javascript"),
                 "/pdf-compare.js": ("pdf-compare.js", "text/javascript"),
                 "/pdf-compare.css": ("pdf-compare.css", "text/css"),
                 "/architecture": ("architecture.html", "text/html"),
                 "/morpheme": ("morpheme.html", "text/html"),
                 "/layout": ("layout.html", "text/html"),
                 "/assets/pdf-2x1.jpg": ("assets/pdf-2x1.jpg", "image/jpeg"),
                 "/assets/pdf-2x2.jpg": ("assets/pdf-2x2.jpg", "image/jpeg"),
                 "/assets/pdf-3x2.jpg": ("assets/pdf-3x2.jpg", "image/jpeg"),
                 "/assets/pdf-3x3.jpg": ("assets/pdf-3x3.jpg", "image/jpeg")}
        if path not in files:
            self.send_error(404)
            return
        filename, mime = files[path]
        file_path = ROOT / filename
        content = file_path.read_bytes() if mime == "image/jpeg" else file_path.read_text(encoding="utf-8").replace("__REQUEST_TOKEN__", TOKEN).encode()
        self.send_response(200)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        if self.path not in ("/api/run", "/api/layout-test"):
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
            if self.path == "/api/layout-test":
                surface_size = body.get("size")
                morphemes = body.get("morphemes")
                allowed = {"TEXT", "METRIC", "STATUS", "PROGRESS", "SWITCH", "SLIDER", "BUTTON", "LIST", "IMAGE", "ICON"}
                if surface_size not in ("2x1", "2x2", "3x2", "3x3") or not isinstance(morphemes, list) or not 0 < len(morphemes) <= 20:
                    raise ValueError("布局测试输入无效")
                normalized = []
                for index, item in enumerate(morphemes):
                    if not isinstance(item, dict) or item.get("type") not in allowed:
                        raise ValueError("布局测试组件无效")
                    normalized.append({"id": "pdf_" + str(index + 1), "type": item["type"],
                                       "role": item.get("role", "SECONDARY"),
                                       "priority": max(0, min(100, int(item.get("priority", 60)))),
                                       "label": str(item.get("label", item["type"]))[:80],
                                       "content": item.get("content", {}) if isinstance(item.get("content", {}), dict) else {}})
                spec = {"title": str(body.get("title", "PDF 测试"))[:80],
                        "surface": {"type": "CARD", "size": surface_size}, "morphemes": normalized}
                layout = plan_layout(spec, body.get("style_id", "neutral"))
                rendered_spec = build_render_spec(spec, layout)
                result = {"morphemeSpec": spec, "layout": layout, "renderSpec": rendered_spec,
                          "outputs": {"dsl": render_output(rendered_spec, "dsl"),
                                      "html_css": render_output(rendered_spec, "html_css"),
                                      "a2ui": render_output(rendered_spec, "a2ui")}}
                content = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(content)))
                self.end_headers(); self.wfile.write(content)
                return
            prompt = body["prompt"]
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("请输入提示词")
            provider = body.get("provider", "ollama")
            base = body.get("base_url", "").rstrip("/")
            url = urlparse(base)
            if provider != "mock" and (url.scheme not in ("http", "https") or not url.hostname or url.username or url.password):
                raise ValueError("API 地址应为不含凭据的 HTTP(S) 地址")
            if url.scheme == "http" and url.hostname not in ("localhost", "127.0.0.1", "::1"):
                raise ValueError("外部 API 请使用 HTTPS")
            settings = Settings(provider, body.get("model", ""), base, body.get("api_key", ""),
                                max(5, min(600, float(body.get("timeout", 180)))),
                                body.get("response_mode", "json_schema"))
            client = create_provider(settings)
        except Exception as exc:
            self.send_error(400, str(exc).encode("ascii", "replace").decode())
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        def send(event):
            # Remove exact credential echoes in upstream errors without exposing configuration.
            data = json.dumps(event, ensure_ascii=False)
            if settings.api_key:
                data = data.replace(settings.api_key, "[REDACTED]")
            self.wfile.write((data + "\n").encode("utf-8"))
            self.wfile.flush()
        try:
            pipeline = MorphemePipeline(client, on_event=send) if body.get("flow") == "morpheme" else IntentPipeline(client, on_event=send)
            pipeline.generate(prompt, body.get("card_size", "AUTO"), body.get("render_protocol", "html_css"),
                              body.get("style_id", "neutral"), bool(body.get("semantic_review", False))) if body.get("flow") == "morpheme" else pipeline.generate(prompt)
            send({"type": "done", "ok": True})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            send({"type": "done", "ok": False, "error": str(exc)})

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("GenUI Workbench: http://127.0.0.1:8765", flush=True)
    server.serve_forever()
