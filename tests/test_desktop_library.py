"""Offline Dashboard and AI Center checks using real report files."""
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from netease_music_insight.combined import build_combined, write_combined
from netease_music_insight.desktop.bridge import DesktopBridge
from netease_music_insight.report import build_data, write_reports


def sample(provider):
    songs = [
        {"id": 1, "name": "夜色", "artists": "甲 / 乙", "album": "第一张",
         "liked_at": "2025-05-01T10:00:00+08:00"},
        {"id": 2, "name": "晨光", "artists": "甲", "album": "第一张",
         "liked_at": None},
    ]
    playlists = [{"id": 10, "name": "日常", "created_by_user": True,
                  "tracks": songs, "track_count": 2,
                  "created_at": "2025-01-01T10:00:00+08:00"}]
    data = build_data({"userId": provider, "nickname": "测试"},
                      songs, playlists, [], provider=provider)
    if provider == "qq_music":
        data["capabilities"]["play_history"] = False
    return data


class DesktopLibraryTests(unittest.TestCase):
    def test_empty_library_has_friendly_state(self):
        with tempfile.TemporaryDirectory() as temp:
            bridge = DesktopBridge(Path(temp))
            state = bridge.snapshot()["state"]
            self.assertIsNone(state["dashboard"])
            self.assertEqual(state["topics"], [])
            self.assertEqual(state["files"], [])
            self.assertFalse(bridge.get_topic(1)["ok"])
            self.assertEqual(bridge.search_catalog("夜色")["results"], [])

    def test_offline_restore_source_switch_topics_and_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "output"
            netease, qq = sample("netease"), sample("qq_music")
            net_folder = output / "netease-user"
            qq_folder = output / "qq_music" / "qq-user"
            joint_folder = output / "combined"
            write_reports(net_folder, netease)
            write_reports(qq_folder, qq)
            write_combined(joint_folder, build_combined(netease, qq))
            os.utime(net_folder / "music_for_ai.json", (1_700_000_100, 1_700_000_100))
            os.utime(qq_folder / "music_for_ai.json", (1_700_000_200, 1_700_000_200))
            os.utime(joint_folder / "music_for_ai_combined.json", (1_700_000_300, 1_700_000_300))

            # A new process can load the exported data without a provider or network.
            bridge = DesktopBridge(root)
            state = bridge.snapshot()["state"]
            self.assertEqual(state["view"], "home")
            self.assertEqual(state["dashboard"]["source"], "两个平台")
            self.assertEqual(state["dashboard"]["liked"], 4)
            self.assertEqual(state["dashboard"]["top_artists"][0],
                             {"name": "甲", "count": 4})
            self.assertEqual(state["dashboard"]["top_albums"][0],
                             {"name": "第一张", "count": 4})
            self.assertEqual(len(state["sources"]), 3)
            self.assertEqual(len(state["topics"]), 13)
            self.assertTrue(bridge.search_catalog("夜色")["results"])
            for number in range(1, 14):
                result = bridge.get_topic(number)
                self.assertTrue(result["ok"], number)
                self.assertIn("请完整读取我上传的 music_for_ai_combined.json。",
                              result["topic"]["prompt"])
            with patch("netease_music_insight.desktop.bridge.copy_text") as copied:
                self.assertTrue(bridge.copy_prompt(13)["ok"])
                self.assertIn("两个平台上的我有哪些相同和不同", copied.call_args.args[0])

            qq_id = next(row["id"] for row in state["sources"]
                         if row["label"] == "QQ 音乐")
            self.assertTrue(bridge.select_source(qq_id)["ok"])
            state = bridge.snapshot()["state"]
            self.assertEqual(state["view"], "music")
            self.assertEqual(len(state["topics"]), 12)
            self.assertFalse(bridge.get_topic(13)["ok"])
            prompt = bridge.get_topic(4)["topic"]["prompt"]
            self.assertIn("请完整读取我上传的 music_for_ai.json。", prompt)
            self.assertIn("不要把播放历史缺失解释为用户不重复听歌", prompt)
            self.assertEqual(len(state["files"]), 3)
            self.assertEqual(len(bridge.search_catalog("第一张")["results"]), 2)

    def test_missing_time_is_explicit_in_prompt(self):
        data = sample("qq_music")
        data["statistics"]["liked_songs_with_time"] = 0
        data["statistics"]["playlists_with_creation_time"] = 0
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "output" / "qq_music" / "user"
            write_reports(folder, data)
            bridge = DesktopBridge(Path(temp))
            topic = bridge.get_topic(12)["topic"]
            self.assertFalse(topic["available"])
            self.assertIn("不要编造变化年份", topic["prompt"])

    def test_large_catalog_does_not_enter_gui_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            bridge = DesktopBridge(Path(temp))
            for total in (5000, 10001):
                with self.subTest(total=total):
                    data = sample("netease")
                    songs = [{"id": index, "name": f"测试歌曲 {index}",
                              "artists": "测试歌手", "album": "测试专辑"}
                             for index in range(total)]
                    data["liked_songs"] = songs
                    data["song_catalog"] = songs
                    data["statistics"]["liked_song_count"] = total
                    data["statistics"]["unique_song_count"] = total
                    bridge._set_result(Path(temp) / "output" / "demo", data, view="music")
                    state = bridge.snapshot()["state"]
                    self.assertEqual(state["dashboard"]["unique"], total)
                    self.assertNotIn("song_catalog", state)
                    self.assertLess(len(json.dumps(state, ensure_ascii=False)), 30_000)
                    self.assertEqual(len(bridge.search_catalog("测试歌曲")["results"]), 30)


if __name__ == "__main__":
    unittest.main()
