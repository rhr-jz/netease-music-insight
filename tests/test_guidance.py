import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from netease_music_insight.combined import build_combined, write_combined
from netease_music_insight.guidance import available_topics, prompt_for
from netease_music_insight.report import build_data, write_reports
from netease_music_insight.ui import ConsoleUI
from netease_music_insight import cli


def sample(provider="netease", *, timed=False, playlist=True):
    liked = [{"id": 1, "name": "一首歌", "artists": "甲", "album": "甲",
              "liked_at": "2025-02-01T00:00:00+08:00" if timed else None}]
    playlists = ([{"id": 2, "name": "收藏", "created_by_user": True, "tracks": liked,
                   "created_at": "2024-01-01T00:00:00+08:00" if timed else None}]
                 if playlist else [])
    return build_data({"userId": "测试/用户", "nickname": "测试"}, liked, playlists, [],
                      expected_liked=1, expected_playlists=len(playlists), provider=provider)


class GuidanceTests(unittest.TestCase):
    def test_topics_follow_available_data_and_each_prompt_is_independent(self):
        data = sample(playlist=False)
        numbers = {topic.number for topic in available_topics(data)}
        self.assertNotIn(5, numbers)
        self.assertNotIn(10, numbers)
        self.assertNotIn(12, numbers)
        self.assertNotIn(13, numbers)
        for topic in available_topics(sample(timed=True)):
            prompt = prompt_for(topic)
            self.assertTrue(prompt.startswith("请完整读取我上传的 music_for_ai.json。"))
            self.assertIn("时间为空就说未知", prompt)

    def test_single_and_combined_guides_are_written_without_touching_legacy_prompt(self):
        netease, qq = sample(timed=True), sample("qq_music", timed=True)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_reports(root / "网易云_测试", netease)
            single = root / "网易云_测试"
            self.assertTrue((single / "AI_ANALYSIS_PROMPT.md").exists())
            self.assertFalse(any(p.name.startswith("13_") for p in (single / "prompts").iterdir()))
            self.assertIn("01 音乐全景画像", (single / "AI_ANALYSIS_GUIDE.md").read_text("utf-8"))
            combined = build_combined(netease, qq)
            write_combined(root / "combined", combined)
            joined = root / "combined"
            self.assertTrue((joined / "prompts" / "13_网易云与QQ音乐跨平台对比.md").exists())
            self.assertTrue((joined / "prompts" / "13_网易云与QQ音乐跨平台对比.md").read_text("utf-8")
                            .count("请完整读取我上传的 music_for_ai_combined.json。") == 1)
            write_reports(single, sample())
            self.assertFalse((single / "prompts" / "05_音乐成长轨迹.md").exists())

    def test_console_explains_upload_and_handles_help(self):
        output = io.StringIO()
        ui = ConsoleUI()
        with patch("builtins.input", side_effect=["h", "2"]), contextlib.redirect_stdout(output):
            self.assertEqual(ui.choose_provider(), "qq")
            ui.result("QQ 音乐", Path("output/测试"), sample("qq_music"))
        shown = output.getvalue()
        self.assertIn("用对应音乐 App 扫码", shown)
        self.assertIn("上传给 AI，里面是整理好的音乐数据", shown)
        self.assertIn("AI_ANALYSIS_GUIDE.md", shown)

    def test_console_scan_state_and_next_steps(self):
        output = io.StringIO()
        ui = ConsoleUI()
        with contextlib.redirect_stdout(output):
            ui.event("等待扫码……")
            ui.event("已扫码，等待手机确认……")
            ui.event("已确认，正在登录……")
            ui.next_ideas()
        shown = output.getvalue()
        self.assertLess(shown.index("等待扫码"), shown.index("已扫码，请在手机上确认"))
        self.assertLess(shown.index("已扫码，请在手机上确认"), shown.index("手机已确认"))
        for title in ("真实音乐审美", "真正喜欢的歌手", "音乐地图", "音乐社交谈资", "8 周听歌计划"):
            self.assertIn(title, shown)

    def test_legacy_all_argument_generates_combined_without_prompting(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            netease, qq = sample(timed=True), sample("qq_music", timed=True)
            def fake_export(_service, provider):
                return (root / "netease", netease) if provider == "netease" else (root / "qq", qq)
            with patch.object(cli, "app_root", return_value=root), \
                 patch.object(cli.MusicInsightService, "export_provider", fake_export), \
                 patch.object(cli.logging, "basicConfig"), \
                 patch("builtins.input", side_effect=AssertionError("unexpected prompt")), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(cli.main(["--provider", "all"]), 0)
            self.assertTrue((root / "output" / "combined" / "AI_ANALYSIS_GUIDE.md").exists())
            self.assertIn("music_for_ai_combined.json", output.getvalue())


if __name__ == "__main__":
    unittest.main()
