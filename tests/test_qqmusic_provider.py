import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from netease_music_insight.providers.qqmusic import QQMusicProvider, qq_playlist_row, qq_song_row
from netease_music_insight.api import ApiError


class FakeClient:
    def __init__(self):
        self.user = self
        self.songlist = self
        self.login = self
        self.calls = []

    def get_fav_song(self, euin, page=1, num=100):
        async def fetch():
            self.calls.append(("liked", page))
            return {"songs": [{"id": page, "mid": f"M{page}", "name": "测试歌曲",
                               "singer": [{"id": 7, "name": "甲"}, {"id": 8, "name": "乙"}],
                               "album": {"id": 9, "name": "专辑"}, "interval": 200}],
                    "total": 2, "hasmore": page == 1}
        return fetch()

    def get_created_songlist(self, uid):
        async def fetch():
            return {"total": 1, "playlists": [{"id": 10, "title": "自建", "songnum": 2,
                                               "create_time": 1700000000}]}
        return fetch()

    def get_fav_songlist(self, euin, page=1, num=100):
        async def fetch():
            self.calls.append(("favorites", page))
            return {"total": 1, "hasmore": False, "playlists": [
                {"id": 11, "title": "收藏", "songnum": 0, "order_time": 1700001000}]}
        return fetch()

    def get_detail(self, pid, dirid=0, num=100, page=1):
        async def fetch():
            self.calls.append(("tracks", pid, page))
            if pid == 11:
                return {"total": 0, "hasmore": False, "songs": []}
            return {"total": 2, "hasmore": page == 1,
                    "songs": [{"id": page, "mid": f"M{page}", "name": "测试歌曲",
                               "singer": [{"name": "甲"}], "interval": 200}]}
        return fetch()

    async def close(self):
        pass


class QQProviderTests(unittest.TestCase):
    def test_qr_expiry_and_request_timeout_are_clear(self):
        from qqmusic_api.models.login import QRCodeLoginEvents

        class QR:
            def save(self, path):
                output = Path(path) / "qr.png"
                output.write_bytes(b"qr")
                return output

        class Session:
            def __init__(self, *args, **kwargs):
                pass

            async def get_qrcode(self):
                return QR()

            async def iter_events(self):
                yield type("Event", (), {"event": QRCodeLoginEvents.TIMEOUT})()

        async def no_sleep(_):
            pass

        async def fails():
            raise TimeoutError()

        with tempfile.TemporaryDirectory() as temp:
            provider = QQMusicProvider(Path(temp), client=FakeClient(), notify=lambda _: None)
            with patch("qqmusic_api.modules.login_utils.QRCodeLoginSession", Session), \
                 patch("os.startfile", create=True), \
                 patch("netease_music_insight.providers.qqmusic.asyncio.sleep", no_sleep):
                with self.assertRaisesRegex(ApiError, "多次过期"):
                    asyncio.run(provider.login())
                with self.assertRaisesRegex(ApiError, "失败或超时"):
                    asyncio.run(provider._request(fails(), "测试"))

    def test_song_and_playlist_normalization(self):
        row = qq_song_row({"id": 4, "mid": "abc", "name": "歌", "singer": [
            {"id": 1, "name": "甲"}, {"id": 2, "name": "乙"}],
            "album": {"id": 3, "name": "专辑"}, "interval": 123})
        self.assertEqual(row["artists"], "甲 / 乙")
        self.assertEqual(row["album"], "专辑")
        self.assertEqual(row["duration_ms"], 123000)
        self.assertIsNone(row["liked_at"])
        self.assertIsNone(qq_song_row({}))
        playlist = qq_playlist_row({"id": 1, "title": "A/B", "order_time": 1700000000}, owned=False, uid="9")
        self.assertIsNone(playlist["subscribed_at"])
        self.assertTrue(playlist["favorite_order_at"].startswith("2023-"))

    def test_full_pages_empty_playlist_and_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = FakeClient()
            provider = QQMusicProvider(root, client=fake, notify=lambda _: None)
            profile = {"userId": "9", "nickname": "A/B", "encrypted_uin": "enc"}
            folder, data = asyncio.run(provider.export(profile))
            self.assertEqual(folder.name, "A_B_9")
            self.assertEqual(data["statistics"]["liked_song_count"], 2)
            self.assertEqual(data["statistics"]["playlist_song_positions"], 2)
            self.assertEqual(data["statistics"]["created_playlist_count"], 1)
            self.assertEqual(data["statistics"]["subscribed_playlist_count"], 1)
            self.assertFalse(data["capabilities"]["play_history"])
            self.assertEqual([v for v in fake.calls if v[0] == "tracks"],
                             [("tracks", 10, 1), ("tracks", 10, 2), ("tracks", 11, 1)])
            fake.calls.clear()
            asyncio.run(QQMusicProvider(root, client=fake, notify=lambda _: None).export(profile))
            self.assertFalse(any(v[0] in {"liked", "favorites", "tracks"} for v in fake.calls))
            self.assertTrue((folder / "music_for_ai.json").exists())
            self.assertIn("收藏于", (folder / "music_summary.md").read_text("utf-8"))
