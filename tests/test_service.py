import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from netease_music_insight.auth import qr_login
from netease_music_insight.errors import ExportCancelled, LoginFailure
from netease_music_insight.report import build_data
from netease_music_insight.service import CancellationToken, MusicInsightService


def sample(provider="netease"):
    return build_data({"userId": "9", "nickname": "测试"},
                      [{"id": 1, "name": "歌", "artists": "甲", "album": "专辑"}],
                      [], [], expected_liked=1, expected_playlists=0, provider=provider)


class FakeNetEase:
    def __init__(self, _base, root, *, notify, present_qr, **kwargs):
        self.root, self.notify, self.present_qr = root, notify, present_qr
        self.logged_out = False

    def login(self):
        self.notify("等待扫码……")
        return {"userId": "9"}

    def export(self, _profile):
        self.notify("✓ 喜欢音乐：1 首")
        return self.root / "output" / "test", sample()

    def logout(self):
        self.logged_out = True


class FakeQQ:
    def __init__(self, root, *, notify, present_qr, **kwargs):
        self.root, self.notify = root, notify

    async def login(self):
        self.notify("已扫码，等待手机确认……")
        return {"userId": "9"}

    async def export(self, _profile):
        self.notify("歌单进度：1/1")
        return self.root / "output" / "qq", sample("qq_music")

    async def logout(self):
        pass


class FakeQrApi:
    def __init__(self):
        self.cookie = ""
        self.codes = iter((801, 802, 803))

    def get(self, path, params=None, **kwargs):
        if path.endswith("/key"):
            return {"data": {"unikey": "key"}}
        if path.endswith("/create"):
            return {"data": {"qrurl": "https://example.invalid/qr"}}
        if path.endswith("/check"):
            code = next(self.codes)
            return {"code": code, "cookie": "temporary" if code == 803 else None}
        raise AssertionError(path)

    def profile(self):
        return {"userId": "9"}


class ServiceTests(unittest.TestCase):
    def test_shared_netease_service_emits_structured_events_without_console(self):
        events = []
        with tempfile.TemporaryDirectory() as temp, \
             patch("netease_music_insight.service.local_api", lambda *_args, **_kwargs: contextlib.nullcontext("http://127.0.0.1")), \
             patch("netease_music_insight.service.NetEaseProvider", FakeNetEase):
            service = MusicInsightService(Path(temp), emit=events.append)
            folder, data = service.export_provider("netease")
        self.assertEqual(folder.name, "test")
        self.assertEqual(data["statistics"]["liked_song_count"], 1)
        kinds = [event.kind for event in events]
        self.assertEqual(kinds[0], "login_started")
        self.assertIn("login_waiting", kinds)
        self.assertIn("profile_done", kinds)
        self.assertIn("liked_songs_done", kinds)
        self.assertEqual(kinds[-1], "export_finished")
        self.assertEqual(events[-1].as_dict()["path"], str(folder))

    def test_qr_login_uses_injected_presentation_and_expiry_decision(self):
        notices, paths = [], []
        with tempfile.TemporaryDirectory() as temp, patch("netease_music_insight.auth.time.sleep"):
            profile = qr_login(FakeQrApi(), show=notices.append, qr_path=Path(temp) / "qr.png",
                               present_qr=lambda path, url: paths.append((path, url)) or True,
                               on_expired=lambda: True)
        self.assertEqual(profile["userId"], "9")
        self.assertEqual(len(paths), 1)
        self.assertTrue(any("已扫码" in notice for notice in notices))

    def test_shared_qq_service_runs_async_provider_and_emits_progress(self):
        events = []
        with tempfile.TemporaryDirectory() as temp, \
             patch("netease_music_insight.providers.qqmusic.QQMusicProvider", FakeQQ):
            folder, data = MusicInsightService(Path(temp), emit=events.append).export_provider("qq")
        self.assertEqual(folder.name, "qq")
        self.assertEqual(data["export_meta"]["provider"], "qq_music")
        self.assertIn("login_scanned", [event.kind for event in events])
        progress = next(event for event in events if event.kind == "playlist_tracks_progress")
        self.assertEqual((progress.current, progress.total), (1, 1))
        self.assertEqual(events[-1].kind, "export_finished")

    def test_cancel_and_failure_are_typed(self):
        token = CancellationToken()
        token.cancel()
        with self.assertRaises(ExportCancelled):
            MusicInsightService(Path("."), cancellation=token).export_provider("netease")
        events = []
        class Broken(FakeNetEase):
            def login(self):
                raise RuntimeError("扫码没有完成")
        with patch("netease_music_insight.service.local_api", lambda *_args, **_kwargs: contextlib.nullcontext("http://127.0.0.1")), \
             patch("netease_music_insight.service.NetEaseProvider", Broken):
            with self.assertRaises(LoginFailure):
                MusicInsightService(Path("."), emit=events.append).export_provider("netease")
        self.assertEqual(events[-1].kind, "login_failed")


if __name__ == "__main__":
    unittest.main()
