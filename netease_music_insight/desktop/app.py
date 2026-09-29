"""Create the desktop window without starting a standalone Web application."""
import argparse
import logging
import sys
from pathlib import Path

from .. import __version__
from .bridge import DesktopBridge


def app_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def html_path():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "netease_music_insight" / "desktop" / "assets" / "index.html"
    return Path(__file__).resolve().parent / "assets" / "index.html"


def _configure_logging(root):
    folder = root / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.ERROR)
    if not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        handler = logging.FileHandler(folder / "error.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Music Insight Windows desktop")
    parser.add_argument("--version", action="version", version=f"Music Insight {__version__}")
    parser.add_argument("--smoke", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = app_root()
    path = html_path()
    if args.smoke:
        assert path.is_file(), f"Desktop asset missing: {path}"
        assert "Music Insight" in path.read_text(encoding="utf-8")
        assert DesktopBridge(root).snapshot()["state"]["view"] == "home"
        print("Music Insight desktop assets OK")
        return 0
    _configure_logging(root)
    try:
        import webview
        bridge = DesktopBridge(root)
        window = webview.create_window(
            "Music Insight", html=path.read_text(encoding="utf-8"), js_api=bridge,
            width=1180, height=780, min_size=(1024, 700), resizable=True,
            background_color="#10152C", text_select=True, zoomable=True)
        bridge._window = window
        window.events.closing += bridge.on_closing
        webview.start(gui="edgechromium", debug=False, private_mode=True)
        return 0
    except Exception:
        logging.exception("desktop startup failed")
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, "桌面窗口未能启动。请确认已安装 Microsoft Edge WebView2 Runtime，"
                   "详细信息见 logs/error.log。", "Music Insight", 0x10)
        return 1
