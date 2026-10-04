"""Serve the shared desktop UI on a loopback-only, authenticated HTTP origin."""
import json
import logging
import secrets
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from ..desktop.bridge import DesktopBridge
from ..frontend import document


CALLS = {
    "snapshot", "navigate", "start", "begin_export", "refresh_qr", "cancel",
    "select_source", "get_topic", "search_catalog", "set_theme",
    "set_output_dir", "clear_cache", "open_result_folder", "open_logs",
    "browse_library", "get_comparison", "get_guide", "prepare_archive",
}


class LocalWebServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, root, bridge=None):
        self.bridge = bridge if bridge is not None else DesktopBridge(root)
        self.session = secrets.token_urlsafe(32)
        self.csrf = secrets.token_urlsafe(32)
        self.nonce = secrets.token_urlsafe(20)
        self.html = document(inline=True)
        super().__init__(("127.0.0.1", 0), LocalWebHandler)

    @property
    def origin(self):
        return f"http://127.0.0.1:{self.server_port}"


class LocalWebHandler(BaseHTTPRequestHandler):
    server: LocalWebServer

    def log_message(self, format, *args):
        # Requests can contain private paths or search terms; never log them.
        return

    def _headers(self, status, content_type, length, *, cookie=False, download=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", (
            "default-src 'none'; script-src 'nonce-%s'; style-src 'unsafe-inline'; "
            "img-src data:; connect-src 'self'; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'none'" % self.server.nonce))
        if cookie:
            self.send_header("Set-Cookie", f"music_insight_session={self.server.session}; "
                             "HttpOnly; SameSite=Strict; Path=/")
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{download}"')
        self.end_headers()

    def _json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def _allowed_host(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def _session_ok(self):
        cookies = self.headers.get("Cookie", "").split(";")
        for item in cookies:
            key, _, value = item.strip().partition("=")
            if key == "music_insight_session":
                return secrets.compare_digest(value, self.server.session)
        return False

    def _download(self, name):
        if name not in {"music_for_ai.json", "music_for_ai_combined.json",
                        "music_summary.md", "music_summary_combined.md",
                        "AI_ANALYSIS_GUIDE.md", "music-insight-export.zip"}:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False})
            return
        state = self.server.bridge.snapshot()["state"]
        folder = state.get("result_folder")
        if not folder or name not in {entry["name"] for entry in state.get("files", [])}:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False})
            return
        try:
            root = Path(folder).resolve(strict=True)
            path = (root / name).resolve(strict=True)
            if path.parent != root or not path.is_file():
                raise FileNotFoundError(name)
            with path.open("rb") as source:
                size = path.stat().st_size
                kind = "application/zip" if name.endswith(".zip") else "application/json" if name.endswith(".json") else "text/markdown"
                self._headers(HTTPStatus.OK, kind, size, download=name)
                while chunk := source.read(65536):
                    self.wfile.write(chunk)
        except (OSError, ValueError):
            logging.exception("local web download failed")
            try:
                self._json(HTTPStatus.NOT_FOUND, {"ok": False})
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_GET(self):
        if not self._allowed_host():
            self._json(HTTPStatus.FORBIDDEN, {"ok": False})
            return
        path = urlsplit(self.path).path
        if path == "/":
            config = json.dumps({"csrf": self.server.csrf}, ensure_ascii=False).replace("<", "\\u003c")
            html = self.server.html.replace("<script>", f'<script nonce="{self.server.nonce}">')
            html = html.replace(f'<script nonce="{self.server.nonce}">',
                f'<script nonce="{self.server.nonce}">window.musicInsightWeb={config};</script>'
                f'<script nonce="{self.server.nonce}">', 1)
            body = html.encode("utf-8")
            self._headers(HTTPStatus.OK, "text/html; charset=utf-8", len(body), cookie=True)
            self.wfile.write(body)
        elif path.startswith("/download/") and self._session_ok():
            self._download(unquote(path[len("/download/"):]))
        else:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False})

    def do_POST(self):
        if (not self._allowed_host() or
                self.headers.get("Origin") != self.server.origin or
                not self._session_ok() or
                not secrets.compare_digest(self.headers.get("X-Music-Insight-CSRF", ""),
                                           self.server.csrf)):
            self._json(HTTPStatus.FORBIDDEN, {"ok": False})
            return
        if urlsplit(self.path).path != "/api/call":
            self._json(HTTPStatus.NOT_FOUND, {"ok": False})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                raise ValueError("invalid request size")
            request = json.loads(self.rfile.read(length))
            name, args = request.get("method"), request.get("args")
            if name not in CALLS or not isinstance(args, list) or len(args) > 4:
                raise ValueError("invalid method")
            result = getattr(self.server.bridge, name)(*args)
            if name == "snapshot" and "state" in result:
                # Exception details stay in logs, not in browser responses.
                error = result["state"].get("error")
                if error:
                    error.pop("detail", None)
            self._json(HTTPStatus.OK, result)
        except (TypeError, ValueError, KeyError, AttributeError):
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "请求无效，请刷新页面后重试。"})
        except Exception:
            logging.exception("local web request failed")
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR,
                       {"ok": False, "message": "操作没有完成，请查看本机日志。"})


def start_server(root, *, bridge=None, open_browser=True):
    server = LocalWebServer(root, bridge)
    thread = threading.Thread(target=server.serve_forever, name="music-insight-web", daemon=True)
    thread.start()
    if open_browser:
        webbrowser.open(server.origin)
    return server, thread
