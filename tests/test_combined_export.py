import unittest

from netease_music_insight.combined import build_combined


def item(provider, sid, title, artist="甲", duration=200000):
    return {"provider": provider, "id": sid, "name": title,
            "artists": artist, "duration_ms": duration, "playlist_ids": []}


class CombinedTests(unittest.TestCase):
    def test_only_unique_high_confidence_matches_merge(self):
        netease = {"export_meta": {"status": "complete"}, "song_catalog": [
            item("netease", 1, "晴天"), item("netease", 2, "晴天 Live"),
            item("netease", 3, "同名", duration=None)]}
        qq = {"export_meta": {"status": "complete"}, "song_catalog": [
            item("qq_music", "M1", " 晴天 ", duration=201000),
            item("qq_music", "M2", "晴天", duration=230000),
            item("qq_music", "M3", "同名", duration=None)]}
        result = build_combined(netease, qq)
        self.assertEqual(result["statistics"]["cross_platform_high_confidence_matches"], 1)
        self.assertEqual(result["statistics"]["combined_unique_tracks"], 5)
        self.assertEqual(result["matched_catalog"][0]["match_confidence"], "high")
