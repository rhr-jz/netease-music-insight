"""Desktop flow checks with a fake Core; no account or network access."""
import tempfile
import time
import unittest
from pathlib import Path
from threading import Thread

from netease_music_insight.desktop.bridge import DesktopBridge
from netease_music_insight.events import MusicEvent
from netease_music_insight.service import CancellationToken


def until(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("desktop worker did not reach the expected state")


class FakeService:
    instances = []

    def __init__(self, root, *, emit, present_qr, on_qr_expired, cancellation,
                 output_dir, fresh):
        self.emit = emit
        self.present_qr = present_qr
        self.on_qr_expired = on_qr_expired
        self.cancellation = cancellation
        self.output_dir = output_dir
        self.fresh = fresh
        self.providers = []
        self.__class__.instances.append(self)

    def export_provider(self, provider):
        self.providers.append(provider)
        self.emit(MusicEvent("login_started", provider))
        with tempfile.TemporaryDirectory() as temp:
            qr = Path(temp) / "qr.png"
            qr.write_bytes(b"\x89PNG\r\n\x1a\n")
            self.present_qr(provider, qr)
        self.emit(MusicEvent("login_scanned", provider))
        self.emit(MusicEvent("profile_done", provider,
                             details={"nickname": provider + " user"}))
        self.emit(MusicEvent("export_started", provider))
        self.cancellation.check()
        self.emit(MusicEvent("playlist_tracks_progress", provider,
                             current=3, total=8))
        data = {"statistics": {"liked_song_count": 6, "playlist_count": 8,
                               "unique_song_count": 10},
                "song_catalog": [{"artists": "A / B"}]}
        folder = self.output_dir / provider
        folder.mkdir(parents=True, exist_ok=True)
        for name in ("music_for_ai.json", "music_summary.md", "AI_ANALYSIS_GUIDE.md"):
            (folder / name).write_text("test", encoding="utf-8")
        return folder, data

    def combine(self, netease, qq):
        data = {"platforms": {"netease": netease, "qq_music": qq},
                "statistics": {"combined_unique_tracks": 19},
                "matched_catalog": [{"sources": [{"artists": "A / B"}]}]}
        folder = self.output_dir / "combined"
        folder.mkdir(parents=True, exist_ok=True)
        for name in ("music_for_ai_combined.json", "music_summary_combined.md",
                     "AI_ANALYSIS_GUIDE.md"):
            (folder / name).write_text("test", encoding="utf-8")
        return folder, data


class DesktopTests(unittest.TestCase):
    def test_bridge_does_not_expose_window_or_core_objects_to_js(self):
        with tempfile.TemporaryDirectory() as temp:
            bridge = DesktopBridge(Path(temp), service_factory=FakeService)
            self.assertFalse([name for name in vars(bridge) if not name.startswith("_")])

    def test_qr_login_progress_and_dashboard(self):
        with tempfile.TemporaryDirectory() as temp:
            bridge = DesktopBridge(Path(temp), service_factory=FakeService)
            self.assertTrue(bridge.start("netease")["ok"])
            until(lambda: bridge.snapshot()["state"]["view"] == "connected")
            state = bridge.snapshot()["state"]
            self.assertEqual(state["nickname"], "netease user")
            self.assertIsNone(state["qr"])
            self.assertFalse(bridge.navigate("settings")["ok"])
            self.assertTrue(bridge.begin_export()["ok"])
            until(lambda: bridge.snapshot()["state"]["view"] == "music")
            state = bridge.snapshot()["state"]
            self.assertEqual(state["dashboard"],
                             {"liked": 6, "playlists": 8, "unique": 10, "artists": 2})
            self.assertEqual(len(state["files"]), 3)
            self.assertFalse(state["busy"])

    def test_combined_and_output_setting(self):
        with tempfile.TemporaryDirectory() as temp:
            bridge = DesktopBridge(Path(temp), service_factory=FakeService)
            target = Path(temp) / "my-exports"
            self.assertTrue(bridge.set_output_dir(str(target))["ok"])
            self.assertTrue(bridge.set_theme("light")["ok"])
            self.assertTrue(bridge.start("all", True)["ok"])
            until(lambda: bridge.snapshot()["state"]["view"] == "connected")
            self.assertTrue(bridge.begin_export()["ok"])
            until(lambda: bridge.snapshot()["state"]["view"] == "music")
            state = bridge.snapshot()["state"]
            self.assertEqual(state["dashboard"]["unique"], 19)
            self.assertEqual(len(state["files"]), 3)
            self.assertEqual(FakeService.instances[-1].providers, ["netease", "qq"])
            self.assertTrue(FakeService.instances[-1].fresh)
            self.assertEqual(FakeService.instances[-1].output_dir, target.resolve())
            restored = DesktopBridge(Path(temp))
            self.assertEqual(restored.snapshot()["state"]["settings"]["theme"], "light")
            self.assertEqual(restored.snapshot()["state"]["settings"]["output_dir"],
                             str(target.resolve()))

    def test_cancel_waiting_for_export(self):
        with tempfile.TemporaryDirectory() as temp:
            bridge = DesktopBridge(Path(temp), service_factory=FakeService)
            bridge.start("qq")
            until(lambda: bridge.snapshot()["state"]["view"] == "connected")
            self.assertTrue(bridge.cancel()["ok"])
            until(lambda: not bridge.snapshot()["state"]["busy"])
            self.assertEqual(bridge.snapshot()["state"]["view"], "platforms")
            self.assertFalse((Path(temp) / "output" / "qq").exists())

    def test_expired_qr_waits_for_refresh(self):
        with tempfile.TemporaryDirectory() as temp:
            bridge = DesktopBridge(Path(temp), service_factory=FakeService)
            bridge._token = CancellationToken()
            bridge._change(busy=True, view="login")
            qr = Path(temp) / "qr.png"
            qr.write_bytes(b"test-image")
            bridge._present_qr("qq", qr)
            self.assertTrue(bridge.snapshot()["state"]["qr"].startswith("data:image/png;base64,"))
            worker = Thread(target=bridge._expired, args=("qq",))
            worker.start()
            until(lambda: bridge.snapshot()["state"]["login_status"] == "二维码已过期")
            self.assertIsNone(bridge.snapshot()["state"]["qr"])
            self.assertTrue(bridge.refresh_qr()["ok"])
            worker.join(timeout=2)
            self.assertFalse(worker.is_alive())


if __name__ == "__main__":
    unittest.main()
