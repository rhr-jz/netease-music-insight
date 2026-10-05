"""Create the desktop window without starting a standalone Web application."""
import argparse
import logging
import sys
import os
from pathlib import Path

from .. import __version__
from ..diagnostics import configure_error_logging
from .bridge import DesktopBridge
from ..frontend import ASSETS, document


def app_root():
    if getattr(sys, "frozen", False):
        # App bundles may live in /Applications, a read-only DMG, or Program Files.
        # Keep credentials, exports and settings outside redistributed application files.
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "MusicInsight"
        if sys.platform == "win32":
            return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "MusicInsight"
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def html_path():
    return ASSETS / "index.html"


def _configure_logging(root):
    configure_error_logging(root)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--cli" in argv:
        from ..cli import main as cli_main
        return cli_main([arg for arg in argv if arg != "--cli"])
    if "--local-web" in argv:
        from ..web.app import main as web_main
        return web_main([arg for arg in argv if arg != "--local-web"])
    parser = argparse.ArgumentParser(description="Music Insight desktop")
    parser.add_argument("--version", action="version", version=f"Music Insight {__version__}")
    parser.add_argument("--smoke", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--web-smoke", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--runtime-smoke", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--gui-smoke", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = app_root()
    path = html_path()
    if args.runtime_smoke:
        from ..bootstrap import local_api
        import requests
        import tempfile
        with tempfile.TemporaryDirectory() as scratch:
            with local_api(Path(scratch)) as base:
                probe = requests.Session()
                probe.trust_env = False
                try:
                    # Verify packaged helper and QR encoding without a real account
                    # or third-party network dependency in the build gate.
                    response = probe.get(base + "/login/qr/create", params={
                        "key": "portable-component-check", "qrimg": "true"}, timeout=10)
                    response.raise_for_status()
                    assert response.json().get("data", {}).get("qrimg", "").startswith("data:image/"), "QR image unavailable"
                finally:
                    probe.close()
        return 0
    if args.smoke:
        assert path.is_file(), f"Desktop asset missing: {path}"
        assert "Music Insight" in path.read_text(encoding="utf-8")
        assert DesktopBridge(root).snapshot()["state"]["view"] == "home"
        print("Music Insight desktop assets OK")
        return 0
    if args.web_smoke:
        from urllib.request import urlopen
        from ..web.server import start_server

        server, thread = start_server(root, open_browser=False)
        try:
            with urlopen(server.origin, timeout=5) as response:
                assert b"Music Insight" in response.read()
            print("Music Insight packaged Local Web OK")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        return 0
    _configure_logging(root)
    try:
        import webview
        bridge = DesktopBridge(root)
        window = webview.create_window(
            "Music Insight", html=document(inline=True), js_api=bridge,
            width=1180, height=780, min_size=(1024, 700), resizable=True,
            background_color="#10152C", text_select=True, zoomable=True)
        bridge._window = window
        window.events.closing += bridge.on_closing
        passed = []
        if args.gui_smoke:
            from threading import Timer
            def check_window():
                try:
                    passed.append(window.evaluate_js("document.body.innerText.includes('Music Insight')"))
                finally:
                    window.destroy()
            window.events.loaded += check_window
            watchdog = Timer(30, window.destroy)
            watchdog.daemon = True
            watchdog.start()
        webview.start(gui="edgechromium" if sys.platform == "win32" else None,
                      debug=False, private_mode=True)
        if args.gui_smoke:
            watchdog.cancel()
            return 0 if passed == [True] else 1
        return 0
    except Exception:
        logging.exception("desktop startup failed")
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, "桌面窗口未能启动，将使用系统浏览器打开相同的本地界面。"
                   "详细信息见日志目录。", "Music Insight", 0x40)
        if not args.gui_smoke:
            from ..web.app import main as web_main
            return web_main([])
        return 1
