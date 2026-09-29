import json
import tempfile
import unittest
from pathlib import Path

from netease_music_insight.api import ApiError
from netease_music_insight.exporter import ExportService


class FakeApi:
    def __init__(self):
        self.calls = []

    def get(self, path, params=None, **kwargs):
        self.calls.append((path, params))
        if path == "/likelist":
            return {"ids": [1]}
        if path == "/song/detail":
            return {"songs": [{"id": 1, "name": "歌曲", "ar": [{"name": "歌手"}], "al": {"name": "专辑"}}]}
        if path == "/user/playlist":
            return {"playlist": [
                {"id": 11, "name": "正常", "trackCount": 1, "creator": {"userId": 9, "nickname": "我"}},
                {"id": 12, "name": "无权限", "trackCount": 1, "creator": {"userId": 8, "nickname": "别人"}},
            ], "more": False}
        if path == "/playlist/track/all":
            if params["id"] == 12:
                raise ApiError("无权限")
            return {"songs": [{"id": 1, "name": "歌曲", "ar": [{"name": "歌手"}], "al": {"name": "专辑"}}]}
        if path == "/user/record":
            raise ApiError("暂不可用")
        raise AssertionError(path)


class ExportTests(unittest.TestCase):
    def test_partial_export_and_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            api = FakeApi()
            folder, data = ExportService(api, root, notify=lambda _: None).run({"userId": 9, "nickname": "A/B"})
            self.assertEqual(folder.name, "A_B_9")
            self.assertEqual(data["export_meta"]["status"], "partial")
            self.assertEqual(data["statistics"]["playlist_count"], 1)
            self.assertEqual(data["statistics"]["playlist_expected"], 2)
            self.assertEqual(len(data["export_meta"]["issues"]), 2)
            saved = json.loads((folder / "music_for_ai.json").read_text("utf-8"))
            self.assertEqual(saved["liked_songs"][0]["id"], 1)
            self.assertTrue((root / ".cache" / "9" / "playlists" / "11.json").exists())
            api2 = FakeApi()
            ExportService(api2, root, notify=lambda _: None).run({"userId": 9, "nickname": "A/B"})
            self.assertFalse(any(path == "/playlist/track/all" and params["id"] == 11 for path, params in api2.calls))

    def test_invalid_api_shape_is_reported(self):
        class BadApi(FakeApi):
            def get(self, path, params=None, **kwargs):
                if path == "/likelist":
                    return {"unexpected": []}
                return super().get(path, params, **kwargs)
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ApiError):
                ExportService(BadApi(), Path(temp), notify=lambda _: None).run({"userId": 9})

    def test_corrupt_cache_is_refetched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / ".cache" / "9"
            cache.mkdir(parents=True)
            (cache / "liked_ids.json").write_text("{broken", encoding="utf-8")
            api = FakeApi()
            folder, data = ExportService(api, root).run({"userId": 9, "nickname": "测试"})
            self.assertEqual(data["statistics"]["liked_song_count"], 1)
            self.assertTrue((folder / "music_for_ai.json").is_file())
            self.assertIn("/likelist", [path for path, _ in api.calls])
