"""Browser import boundaries and reuse of the actual shared Core."""
import base64
import copy
import io
import json
import unittest
from zipfile import ZipFile

from netease_music_insight.browser import BrowserSession, BrowserInputError, validate_export
from netease_music_insight.combined import build_combined
from netease_music_insight.guidance import TOPICS, prompt_for, guide_markdown
from netease_music_insight.report import build_data, summary_markdown


def sample(provider="netease", count=4):
    songs = [{"id": str(i), "name": f"演示歌曲{i}", "artists": "演示歌手", "album": "演示专辑",
              "duration_ms": 180000 + i * 1000, "liked_at": "2025-04-05T00:00:00Z" if provider == "netease" else None}
             for i in range(count)]
    data = build_data({"userId": "demo", "nickname": "演示用户"}, songs,
                      [{"id": "list", "name": "演示歌单", "created_by_user": True, "tracks": songs}], [], provider=provider)
    data["export_meta"]["exported_at"] = "2026-10-01T10:00:00Z"
    return data


def load(session, *data):
    session.prepare([json.dumps(item, ensure_ascii=False) for item in data])
    return session.commit()


class BrowserTests(unittest.TestCase):
    def test_single_reuses_dashboard_prompt_and_export_core(self):
        session, data = BrowserSession(), sample()
        state = load(session, data)
        self.assertEqual(state["dashboard"]["unique"], 4)
        self.assertEqual(state["filename"], "music_for_ai.json")
        self.assertEqual(len(state["topics"]), 12)
        for topic in TOPICS[:12]:
            self.assertEqual(session.topic(topic.number)["prompt"], prompt_for(topic, data=data))
        self.assertEqual(session.download("music_summary.md")["content"], summary_markdown(data))
        self.assertEqual(session.download("AI_ANALYSIS_GUIDE.md")["content"], guide_markdown(data))
        self.assertEqual(json.loads(session.download("music_for_ai.json")["content"]), data)

    def test_combined_is_same_conservative_matching(self):
        session = BrowserSession()
        net, qq = sample(), sample("qq_music")
        qq["liked_songs"][0]["duration_ms"] += 30000
        qq["song_catalog"][0]["duration_ms"] += 30000
        expected = build_combined(net, qq)
        state = load(session, net, qq)
        actual = json.loads(session.download("music_for_ai_combined.json")["content"])
        self.assertEqual(actual["matched_catalog"], expected["matched_catalog"])
        self.assertEqual(actual["statistics"], expected["statistics"])
        self.assertEqual(len(state["topics"]), 13)
        self.assertIn("music_for_ai_combined.json", session.topic(13)["prompt"])

    def test_combined_file_and_qq_history_and_time_limits(self):
        session = BrowserSession()
        load(session, build_combined(sample(), sample("qq_music")))
        session.select("qq_music")
        self.assertIn("不要把播放历史缺失解释为用户不重复听歌", session.topic(4)["prompt"])
        self.assertIn("当前没有可靠的收藏或歌单时间", session.topic(5)["prompt"])
        with self.assertRaises(BrowserInputError):
            session.topic(13)

    def test_rejected_import_and_cancel_keep_previous_output(self):
        session = BrowserSession()
        load(session, sample())
        before = session.download("music_for_ai.json")["content"]
        with self.assertRaises(BrowserInputError):
            session.prepare([json.dumps(sample("qq_music")), "broken json"])
        with self.assertRaises(BrowserInputError):
            session.commit()
        session.prepare([json.dumps(sample("qq_music"))])
        session.discard()
        self.assertEqual(session.download("music_for_ai.json")["content"], before)
        self.assertEqual(len(session.snapshot()["sources"]), 1)

    def test_invalid_shapes_credentials_and_nonfinite_values_are_friendly(self):
        cases = [None, [], {}, {"export_meta": "bad"}, {"cookie": "example"}]
        for path, value in [("playlists", "bad"), ("song_catalog", {}), ("statistics", []), ("token", "example")]:
            data = sample(); data[path] = value; cases.append(data)
        data = sample(); data["liked_songs"][0]["play_count"] = "many"; cases.append(data)
        data = sample(); data["liked_songs"][0]["duration_ms"] = float("inf"); cases.append(data)
        for data in cases:
            with self.subTest(data_type=type(data).__name__), self.assertRaises(BrowserInputError):
                validate_export(json.dumps(data))

    def test_large_catalog_is_processed_off_main_thread_and_paginated(self):
        session = BrowserSession()
        state = load(session, sample(count=12000))
        self.assertEqual(state["dashboard"]["unique"], 12000)
        self.assertLess(len(json.dumps(state)), 16000)
        first, last = session.search(), session.search(page=300)
        self.assertEqual(len(first["results"]), 40)
        self.assertEqual(len(last["results"]), 40)
        self.assertEqual(last["pages"], 300)
        self.assertEqual(session.search("演示歌曲11999")["total"], 1)

    def test_zip_paths_and_clear(self):
        session = BrowserSession(); load(session, sample())
        for path in ("../secret.txt", "cookie.txt", "/tmp/data", "prompts/../../file"):
            with self.assertRaises(BrowserInputError):
                session.download(path)
        result = session.download("MusicInsight-export.zip")
        with ZipFile(io.BytesIO(base64.b64decode(result["content"]))) as archive:
            self.assertIn("AI_ANALYSIS_GUIDE.md", archive.namelist())
            self.assertIn("prompts/02_真实音乐审美.md", archive.namelist())
            self.assertTrue(all(not name.startswith("/") and ".." not in name for name in archive.namelist()))
        self.assertIsNone(session.clear()["dashboard"])
        with self.assertRaises(BrowserInputError):
            session.download("music_for_ai.json")

    def test_real_import_never_combines_with_demo(self):
        session = BrowserSession()
        session.demo([json.dumps(sample()), json.dumps(sample("qq_music"))])
        state = load(session, sample("qq_music"))
        self.assertFalse(state["demo"])
        self.assertEqual(state["selected"], "qq_music")
        self.assertEqual(len(state["sources"]), 1)

    def test_imported_counts_are_recomputed_without_inventing_dates(self):
        data = copy.deepcopy(sample("qq_music"))
        data["statistics"]["liked_song_count"] = 999999
        data["statistics"]["liked_songs_with_time"] = 999999
        normalized = validate_export(json.dumps(data))
        self.assertEqual(normalized["statistics"]["liked_song_count"], 4)
        self.assertEqual(normalized["statistics"]["liked_songs_with_time"], 0)
        self.assertEqual(normalized["export_meta"]["exported_at"], data["export_meta"]["exported_at"])
