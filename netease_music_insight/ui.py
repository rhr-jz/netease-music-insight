"""A quiet, dependency-free console interface for first-time users."""
import os
import re

from .guidance import available_topics, prompt_for


PLATFORM_NAMES = {"netease": "网易云音乐", "qq": "QQ 音乐", "all": "两个平台"}


class ConsoleUI:
    def __init__(self):
        self._last_step = None
        self._last_event = None

    def line(self, message=""):
        print(message, flush=True)

    def welcome(self, version):
        self.line("=" * 48)
        self.line(f"  Music Insight {version}")
        self.line("  看见属于你的音乐世界")
        self.line("=" * 48)
        self.line("导出音乐数据后，选一个感兴趣的问题交给 AI 分析。")
        self.line("你的音乐数据默认只保存在这台电脑上。")
        self.line()

    def help(self):
        self.line("\n它会读取喜欢歌曲、歌单和平台可获取的播放记录，并整理在本机。")
        self.line("用对应音乐 App 扫码；不用输入密码，也不会下载歌曲。")
        self.line("完成后，上传结果文件夹里的 music_for_ai.json，选择一段分析提示词。")
        self.line("详细隐私说明见程序文件夹中的 PRIVACY.md。\n")

    def choose_provider(self):
        self.line("请选择音乐平台")
        self.line("  1  网易云音乐   喜欢歌曲、歌单和可获取的播放记录")
        self.line("  2  QQ 音乐     我喜欢、自建和收藏歌单")
        self.line("  3  两个平台    分别导出并生成联合音乐画像")
        self.line("  H  查看帮助     Q  退出")
        while True:
            value = input("请输入 1 / 2 / 3：").strip().lower()
            if value in {"1", "2", "3"}:
                return {"1": "netease", "2": "qq", "3": "all"}[value]
            if value == "h":
                self.help()
                continue
            if value == "q":
                return None
            self.line("请选择 1、2、3，或输入 H 查看帮助。")

    def step(self, number, title, *, platform=None):
        key = (number, title, platform)
        if key == self._last_step:
            return
        self._last_step = key
        self._last_event = None
        suffix = f" · {platform}" if platform else ""
        self.line(f"\n步骤 {number} / 4 · {title}{suffix}")

    def event(self, message):
        """Translate provider progress into a small set of human messages."""
        if "首次运行" in message:
            shown = "首次使用正在准备运行组件，可能需要几分钟……"
        elif "二维码已过期" in message:
            shown = ("二维码已过期，正在重新生成……" if "正在刷新" in message
                     else "二维码已过期。按 Enter 重新生成，或按 Q 返回平台选择。")
        elif "二维码图片" in message or "扫描二维码" in message:
            shown = "二维码已在新窗口打开。请用对应的音乐 App 扫码并在手机确认。"
        elif "等待扫码" in message:
            shown = "等待扫码或手机确认……"
        elif "已扫码" in message or "已确认" in message:
            shown = "手机已确认，正在登录……"
        elif "登录成功" in message or "已迁移旧版登录状态" in message:
            shown = "登录成功。"
        elif "账号：" in message:
            shown = "已读取账号信息。"
        elif "获取喜欢" in message or "获取我喜欢" in message:
            shown = "正在获取喜欢歌曲……"
        elif "喜欢音乐：" in message and "/" in message:
            shown = message.replace("喜欢音乐", "喜欢歌曲")
        elif "✓ 喜欢音乐：" in message or "✓ 我喜欢：" in message:
            shown = message.replace("喜欢音乐", "喜欢歌曲").replace("我喜欢", "喜欢歌曲")
        elif "获取歌单" in message or "获取自建与收藏歌单" in message:
            shown = "正在读取歌单和歌曲……"
        elif "自建歌单：" in message:
            shown = message
        elif "歌单进度" in message:
            match = re.search(r"(\d+)\s*/\s*(\d+)", message)
            shown = f"歌单歌曲：已整理 {match.group(1)} / {match.group(2)} 个歌单" if match else "正在整理歌单歌曲……"
        elif "播放记录" in message:
            shown = "正在读取可获取的播放记录……" if "获取" in message else message
        elif "生成 AI" in message or "写入 AI" in message or "整理数据" in message:
            self.step(3, "检查数据并整理文件")
            shown = "正在生成结果文件和分析指南……"
        elif "数据检查" in message:
            return
        elif message.startswith("!"):
            shown = "部分内容暂时无法获取，已记录在结果摘要中。"
        else:
            return
        if shown != self._last_event:
            self.line("  " + shown)
            self._last_event = shown

    def error(self, exc):
        detail = str(exc).lower()
        if any(word in detail for word in ("二维码", "扫码", "登录", "cookie")):
            title, advice = "登录未完成", "请确认二维码未过期，并用对应音乐 App 扫码。"
        elif any(word in detail for word in ("网络", "timeout", "连接", "请求", "http")):
            title, advice = "网络连接暂时不顺畅", "请检查网络和代理设置，然后重试。"
        elif any(word in detail for word in ("组件", "node", "依赖", "安装")):
            title, advice = "运行组件准备失败", "请检查网络、磁盘空间和文件夹写入权限。"
        elif isinstance(exc, PermissionError):
            title, advice = "无法保存文件", "请将程序解压到有写入权限的文件夹后重试。"
        else:
            title, advice = "这次导出没有完成", "可以稍后重试；详细错误已写入 logs/error.log。"
        self.line(f"\n{title}。{advice}")
        self.line("详细错误已保存在 logs/error.log。")

    def retry(self):
        while True:
            choice = input("按 Enter 重试，H 返回平台选择，Q 退出：").strip().lower()
            if choice in {"", "h", "q"}:
                return choice
            self.line("按 Enter、H 或 Q。")

    def result(self, name, folder, data):
        stats = data["statistics"]
        self.line(f"\n{name}：数据已准备好")
        self.line(f"  喜欢歌曲  {stats['liked_song_count']} 首")
        self.line(f"  歌单      {stats['playlist_count']} 个")
        self.line(f"  独立歌曲  {stats['unique_song_count']} 首")
        history = data.get("data_availability", {}).get("play_history", {})
        if history.get("available", True):
            self.line(f"  播放记录  {stats['play_history_count']} 条（平台可获取范围）")
        else:
            self.line("  播放记录  当前平台未提供可靠数据")
        if data["export_meta"].get("issues"):
            self.line(f"  提示：{len(data['export_meta']['issues'])} 项数据缺口，详见 music_summary.md。")
        self.files(folder)

    def data_check(self, data):
        stats = data["statistics"]
        expected_likes = stats.get("liked_song_expected")
        expected_lists = stats.get("playlist_expected")
        self.line("  数据检查：")
        self.line(f"    喜欢歌曲  {stats['liked_song_count']} / {expected_likes if expected_likes is not None else '未知'}")
        self.line(f"    歌单      {stats['playlist_count']} / {expected_lists if expected_lists is not None else '未知'}")
        self.line(f"    歌单歌曲位置  {stats['playlist_song_positions']}")
        issues = data["export_meta"].get("issues") or []
        self.line(f"    需要留意  {len(issues)} 项" if issues else "    检查完成，未记录数据缺口。")

    def files(self, folder, *, combined=False):
        filename = "music_for_ai_combined.json" if combined else "music_for_ai.json"
        summary = "music_summary_combined.md" if combined else "music_summary.md"
        self.line(f"\n结果文件夹：{folder}")
        self.line(f"  {filename}  ← 上传给 AI 的主要文件")
        self.line(f"  {summary}  ← 自己查看的数据摘要")
        self.line("  AI_ANALYSIS_GUIDE.md  ← 按兴趣选择一个问题和对应提示词")
        self.line("  prompts/  ← 每个问题单独存放，方便复制")

    def next_ideas(self):
        self.line("\n接下来可以分析：我喜欢什么、最重要的歌手、音乐地图、同龄人谈资或 8 周听歌计划。")

    def after_export(self, folder, data, *, combined=False):
        self.next_ideas()
        while True:
            self.line("\n接下来：1 查看 AI 分析方向  2 打开结果文件夹  3 退出")
            answer = input("请选择 1 / 2 / 3：").strip()
            if answer == "1":
                self.topic_menu(data, combined=combined)
            elif answer == "2":
                if os.name == "nt":
                    try:
                        os.startfile(folder)
                    except OSError:
                        self.line(f"无法自动打开，请在文件管理器中进入：{folder}")
                else:
                    self.line(f"请在文件管理器中进入：{folder}")
            elif answer == "3":
                return
            else:
                self.line("请选择 1、2 或 3。")

    def topic_menu(self, data, *, combined=False):
        topics = available_topics(data, combined=combined)
        self.line("\n想分析什么？输入编号查看可直接复制的提示词；按 Enter 返回。")
        for topic in topics:
            self.line(f"  {topic.number:02d} {topic.title}  （联网：{topic.network}）")
        while True:
            choice = input("模块编号：").strip()
            if not choice:
                return
            topic = next((item for item in topics if choice in {str(item.number), f"{item.number:02d}"}), None)
            if topic is None:
                self.line("请输入上方的模块编号。")
                continue
            self.line(f"\n{topic.title} · {topic.question}\n")
            self.line(prompt_for(topic, combined=combined))
            self.line("\n上面的完整提示词也已保存在 AI_ANALYSIS_GUIDE.md 和 prompts/ 中。")
