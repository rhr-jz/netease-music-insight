import json
import tempfile
import unittest
from pathlib import Path

from netease_music_insight.report import PROMPT, build_data, song_row, write_reports
from netease_music_insight.utils import safe_name


def song(sid, artist="歌手甲", album="专辑甲"):
    return {"id": sid, "name": f"歌 {sid}", "artists": artist, "album": album, "duration_ms": 200000}


class ReportTests(unittest.TestCase):
    def test_song_shape_and_empty(self):
        self.assertIsNone(song_row({}))
        self.assertEqual(song_row({"id": 1, "name": "A", "ar": [{"name": "甲"}], "al": {"name": "B"}, "dt": 10})["artists"], "甲")
        data = build_data({"userId": 7, "nickname": "甲"}, [], [], [], expected_liked=0, expected_playlists=0)
        self.assertEqual(data["statistics"]["unique_song_count"], 0)
        self.assertEqual(data["export_meta"]["status"], "complete")

    def test_dedup_preserves_playlist_relationships_and_stats(self):
        p = lambda pid, tracks: {"id": pid, "name": str(pid), "created_by_user": pid == 1, "tracks": tracks}
        data = build_data({"userId": 7}, [song(10), song(10), song(11, "歌手乙")],
                          [p(1, [song(10), song(12)]), p(2, [song(10), song(12)])], [],
                          expected_liked=2, expected_playlists=2)
        stats = data["statistics"]
        self.assertEqual(stats["liked_song_count"], 2)
        self.assertEqual(stats["playlist_song_positions"], 4)
        self.assertEqual(stats["unique_song_count"], 3)
        self.assertEqual(stats["created_playlist_count"], 1)
        self.assertEqual(stats["top_artists_in_likes"][0], {"name": "歌手甲", "count": 1})
        first = next(s for s in data["song_catalog"] if s["id"] == 10)
        self.assertEqual(first["playlist_ids"], [1, 2])
        self.assertTrue(first["liked"])

    def test_prompt_and_files(self):
        self.assertIn("8 周", PROMPT)
        self.assertIn("同龄人", PROMPT)
        self.assertIn("不代表账号完整终身播放历史", PROMPT)
        data = build_data({"userId": 7, "nickname": "甲"}, [], [], [], expected_liked=0, expected_playlists=0)
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            write_reports(folder, data)
            self.assertEqual(json.loads((folder / "music_for_ai.json").read_text("utf-8"))["user_profile"]["uid"], 7)
            self.assertTrue((folder / "music_summary.md").exists())
            self.assertTrue((folder / "AI_ANALYSIS_PROMPT.md").exists())

    def test_filename(self):
        self.assertEqual(safe_name('A/B:*?"<>|'), "A_B_______")
        self.assertEqual(safe_name("CON"), "_CON")
        self.assertEqual(safe_name("..."), "netease_user")
