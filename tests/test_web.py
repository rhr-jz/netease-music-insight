"""Local Web boundary, shared UI, and download checks without real accounts."""
import json
import tempfile
import unittest
from http.cookiejar import CookieJar
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from netease_music_insight.desktop.bridge import DesktopBridge
from netease_music_insight.events import MusicEvent
from netease_music_insight.service import CancellationToken
from netease_music_insight.web.server import start_server
from test_desktop import FakeService, until


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bridge = DesktopBridge(self.root, service_factory=FakeService)
        self.server, self.thread = start_server(self.root, bridge=self.bridge, open_browser=False)
        self.client = build_opener(HTTPCookieProcessor(CookieJar()))
        self.origin = self.server.origin

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, path="/", *, method="GET", body=None, headers=None):
        request = Request(self.origin + path, data=body, method=method, headers=headers or {})
        return self.client.open(request, timeout=3)

    def call(self, name, *args, origin=None, csrf=None):
        payload = json.dumps({"method": name, "args": args}).encode()
        return self.request("/api/call", method="POST", body=payload,
                            headers={"Origin": origin or self.origin,
                                     "X-Music-Insight-CSRF": csrf or self.server.csrf,
                                     "Content-Type": "application/json"})

    def test_loopback_page_and_shared_core(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertGreater(self.server.server_port, 0)
        with self.request() as response:
            html = response.read().decode()
            self.assertIn("听见", html)
            self.assertIn("window.musicInsightWeb", html)
            self.assertIn("HttpOnly", response.headers["Set-Cookie"])
            self.assertIn("SameSite=Strict", response.headers["Set-Cookie"])
            self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        result = json.load(self.call("snapshot", -1))
        self.assertEqual(result["state"]["view"], "home")
        self.assertTrue(json.load(self.call("navigate", "platforms"))["ok"])
        self.assertEqual(self.bridge.snapshot()["state"]["view"], "platforms")
        self.bridge._change(error={"title": "出错", "body": "请重试", "detail": "secret-token"})
        state = json.load(self.call("snapshot", -1))["state"]
        self.assertNotIn("detail", state["error"])

    def test_host_origin_csrf_and_session_are_required(self):
        with self.assertRaises(HTTPError) as bad_host:
            self.request(headers={"Host": "attacker.example"})
        self.assertEqual(bad_host.exception.code, 403)
        with self.assertRaises(HTTPError) as no_cookie:
            self.call("snapshot")
        self.assertEqual(no_cookie.exception.code, 403)
        self.request().close()
        for kwargs in ({"origin": "http://attacker.example"}, {"csrf": "incorrect"}):
            with self.assertRaises(HTTPError) as denied:
                self.call("navigate", "settings", **kwargs)
            self.assertEqual(denied.exception.code, 403)
        self.assertEqual(self.bridge.snapshot()["state"]["view"], "home")
        with self.assertRaises(HTTPError) as hidden:
            self.call("__dict__")
        self.assertEqual(hidden.exception.code, 400)

    def test_downloads_only_current_export_files(self):
        folder = self.root / "output" / "user"
        folder.mkdir(parents=True)
        filename = "music_for_ai.json"
        (folder / filename).write_text('{"songs":1}', encoding="utf-8")
        (folder / "secret.txt").write_text("secret", encoding="utf-8")
        self.bridge._change(result_folder=str(folder),
                            files=[{"name": filename, "description": "data",
                                    "path": str(folder / filename)}])
        self.request().close()
        with self.request("/download/" + filename) as response:
            self.assertEqual(response.read(), b'{"songs":1}')
            self.assertIn("attachment", response.headers["Content-Disposition"])
        for name in ("secret.txt", "..%2Fsecret.txt", "music_summary.md"):
            with self.assertRaises(HTTPError) as missing:
                self.request("/download/" + name)
            self.assertEqual(missing.exception.code, 404)

    def test_web_uses_core_qr_export_dashboard_and_prompts(self):
        self.request().close()
        for provider in ("netease", "qq"):
            with self.subTest(provider=provider):
                self.assertTrue(json.load(self.call("start", provider))["ok"])
                until(lambda: self.bridge.snapshot()["state"]["view"] == "connected")
                self.assertTrue(json.load(self.call("begin_export"))["ok"])
                until(lambda: self.bridge.snapshot()["state"]["view"] == "music")
                result = json.load(self.call("snapshot", -1))["state"]
                self.assertEqual(result["dashboard"]["liked"], 6)
                self.assertEqual(len(result["files"]), 3)
                topic = json.load(self.call("get_topic", 1))
                self.assertTrue(topic["ok"])
                self.assertIn("music_for_ai.json", topic["topic"]["prompt"])
                with self.request("/download/music_for_ai.json") as response:
                    self.assertEqual(response.read(), b"test")

    def test_qr_and_login_status_reach_browser_snapshot(self):
        self.request().close()
        qr = self.root / "qr.png"
        qr.write_bytes(b"\x89PNG\r\n\x1a\n")
        self.bridge._token = CancellationToken()
        self.bridge._change(view="login", busy=True, provider="netease",
                            provider_name="网易云音乐")
        self.bridge._present_qr("netease", qr)
        state = json.load(self.call("snapshot", -1))["state"]
        self.assertTrue(state["qr"].startswith("data:image/png;base64,"))
        self.assertEqual(state["login_status"], "等待扫码")
        self.bridge._on_event(MusicEvent("login_scanned", "netease"))
        state = json.load(self.call("snapshot", -1))["state"]
        self.assertIn("已扫码", state["login_status"])
        self.bridge._on_event(MusicEvent("login_confirming", "netease"))
        state = json.load(self.call("snapshot", -1))["state"]
        self.assertIn("正在登录", state["login_status"])

    def test_auto_opens_system_browser(self):
        with patch("netease_music_insight.web.server.webbrowser.open") as opening:
            server, thread = start_server(self.root, open_browser=True)
            try:
                opening.assert_called_once_with(server.origin)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_desktop_setting_starts_shared_web(self):
        with patch("netease_music_insight.web.server.webbrowser.open") as opening:
            self.assertTrue(self.bridge.start_web()["ok"])
            web = self.bridge._web_server
            try:
                self.assertIs(web.bridge, self.bridge)
                opening.assert_called_once_with(web.origin)
            finally:
                web.shutdown()
                web.server_close()


if __name__ == "__main__":
    unittest.main()
