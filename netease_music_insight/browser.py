"""On-device browser adapter. Only stdlib and the existing shared Core are used.

Pyodide runs this module in a Web Worker. No network or persistent storage is
used here. Imports are staged so cancelling an import keeps the previous data.
"""
import base64
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile
from io import BytesIO

from . import __version__
from .combined import build_combined, write_combined
from .desktop.library import dashboard_data, topic_cards, SOURCE_NAMES
from .guidance import TOPICS, prompt_for
from .report import build_data, write_reports

MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_SONGS = 100_000


class BrowserInputError(ValueError):
    pass


def _number(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def _songs(value):
    if not isinstance(value, list) or len(value) > MAX_SONGS:
        raise BrowserInputError("歌曲列表格式不正确，或超过了 100,000 首的处理上限。")
    for song in value:
        if not isinstance(song, dict) or song.get("id") is None:
            raise BrowserInputError("文件中的歌曲缺少有效 ID。请选择 Music Insight 导出的 JSON。")
        if not isinstance(song["id"], (str, int)) or isinstance(song["id"], bool):
            raise BrowserInputError("歌曲 ID 格式不正确。")
        for key in ("name", "artists", "album"):
            if song.get(key) is not None and not isinstance(song[key], str):
                raise BrowserInputError("歌曲名称、歌手或专辑字段格式不正确。")
            song[key] = song.get(key) or ""
        if song.get("duration_ms") is not None and not _number(song["duration_ms"]):
            raise BrowserInputError("歌曲时长格式不正确。")
        if song.get("play_count") is not None and not _number(song["play_count"]):
            raise BrowserInputError("播放次数字段格式不正确。")
        if song.get("liked_at") is not None and not isinstance(song["liked_at"], str):
            raise BrowserInputError("歌曲收藏时间格式不正确。")
    return value


def _single(data, expected=None):
    if not isinstance(data, dict):
        raise BrowserInputError("请选择 Music Insight 导出的音乐数据 JSON。")
    meta = data.get("export_meta")
    profile = data.get("user_profile")
    if not isinstance(meta, dict) or not isinstance(profile, dict):
        raise BrowserInputError("这不是 Music Insight 音乐数据文件。请不要导入 Cookie 或登录凭证文件。")
    provider = meta.get("provider") or profile.get("provider") or "netease"
    if provider not in {"netease", "qq_music"} or (expected and provider != expected):
        raise BrowserInputError("文件中的音乐平台标记不正确。")
    if any(key in data for key in ("cookie", "token", "qm_keyst", "qqmusic_key", "credentials")):
        raise BrowserInputError("检测到登录凭证字段。请只选择 music_for_ai.json 音乐数据文件。")
    for key in ("nickname", "user_id"):
        if profile.get(key) is not None and not isinstance(profile[key], str):
            raise BrowserInputError("用户资料字段格式不正确。")
    if profile.get("uid") is not None and (not isinstance(profile["uid"], (str, int)) or isinstance(profile["uid"], bool)):
        raise BrowserInputError("用户 ID 格式不正确。")
    for key in ("status", "exported_at", "notes"):
        if meta.get(key) is not None and not isinstance(meta[key], str):
            raise BrowserInputError("导出说明字段格式不正确。")
    liked = _songs(data.get("liked_songs"))
    _songs(data.get("song_catalog"))
    history = _songs(data.get("play_history", []))
    playlists = data.get("playlists")
    if not isinstance(playlists, list) or len(playlists) > 10_000:
        raise BrowserInputError("歌单列表格式不正确，或超过处理上限。")
    for playlist in playlists:
        if not isinstance(playlist, dict) or not isinstance(playlist.get("id"), (str, int)):
            raise BrowserInputError("歌单缺少有效 ID。")
        if not isinstance(playlist.get("name", ""), str):
            raise BrowserInputError("歌单名称格式不正确。")
        playlist.setdefault("name", "未命名歌单")
        if not isinstance(playlist.get("created_by_user"), bool):
            raise BrowserInputError("歌单归属字段格式不正确。")
        tracks = _songs(playlist.get("tracks", []))
        if not _number(playlist.get("track_count", len(tracks))):
            raise BrowserInputError("歌单歌曲数量格式不正确。")
        for key in ("created_at", "subscribed_at", "favorite_order_at"):
            if playlist.get(key) is not None and not isinstance(playlist[key], str):
                raise BrowserInputError("歌单时间字段格式不正确。")
    issues = meta.get("issues", [])
    if not isinstance(issues, list) or any(not isinstance(issue, (str, dict)) for issue in issues):
        raise BrowserInputError("数据缺口字段格式不正确。")
    # Recompute factual statistics through the same exporter Core, retaining
    # imported fields and metadata rather than trusting supplied count values.
    original_stats = data.get("statistics", {})
    if not isinstance(original_stats, dict):
        raise BrowserInputError("统计字段格式不正确。")
    for key in ("liked_song_expected", "playlist_expected"):
        if original_stats.get(key) is not None and not _number(original_stats[key]):
            raise BrowserInputError("统计数量格式不正确。")
    fresh = build_data({"userId": profile.get("uid", profile.get("user_id", "")),
                        "nickname": profile.get("nickname", ""), "avatar": profile.get("avatar", "")},
                       liked, playlists, history, issues=issues,
                       expected_liked=original_stats.get("liked_song_expected"),
                       expected_playlists=original_stats.get("playlist_expected"), provider=provider,
                       capabilities=data.get("capabilities") or None)
    result = {**data, "statistics": {**original_stats, **fresh["statistics"]},
              "song_catalog": fresh["song_catalog"], "liked_songs": fresh["liked_songs"],
              "playlists": fresh["playlists"], "play_history": history,
              "export_meta": {**meta, "provider": provider,
                              "status": meta.get("status") or fresh["export_meta"]["status"],
                              "exported_at": meta.get("exported_at") or "",
                              "issues": issues, "notes": meta.get("notes") or fresh["export_meta"]["notes"]},
              "user_profile": {**fresh["user_profile"], **profile}}
    return result


def validate_export(text):
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise BrowserInputError("文件超过 64 MB，请导入较小的音乐数据文件。")
    try:
        data = json.loads(text.lstrip("\ufeff"))
    except (ValueError, RecursionError):
        raise BrowserInputError("JSON 无法读取。请重新选择完整的 Music Insight 导出文件。") from None
    if not isinstance(data, dict):
        raise BrowserInputError("请选择 Music Insight 导出的 JSON 文件。")
    meta = data.get("export_meta")
    if not isinstance(meta, dict):
        raise BrowserInputError("请选择 Music Insight 导出的音乐数据 JSON。")
    if meta.get("provider") == "combined" or "platforms" in data:
        platforms = data.get("platforms")
        if not isinstance(platforms, dict) or set(platforms) != {"netease", "qq_music"}:
            raise BrowserInputError("联合数据需要同时包含网易云和 QQ 音乐。")
        combined = build_combined(_single(platforms["netease"], "netease"),
                                  _single(platforms["qq_music"], "qq_music"))
        imported_meta = data.get("export_meta")
        if isinstance(imported_meta, dict) and isinstance(imported_meta.get("exported_at"), str):
            combined["export_meta"]["exported_at"] = imported_meta["exported_at"]
        return combined
    return _single(data)


class BrowserSession:
    def __init__(self):
        self._datasets = {}
        self._selected = None
        self._prepared = None
        self._demo = False

    def prepare(self, texts):
        self._prepared = None
        if not isinstance(texts, list) or not 1 <= len(texts) <= 2:
            raise BrowserInputError("请选择一个联合数据文件，或网易云与 QQ 音乐各一个文件。")
        values = [validate_export(text) for text in texts]
        providers = [data["export_meta"]["provider"] for data in values]
        if len(set(providers)) != len(providers) or ("combined" in providers and len(values) > 1):
            raise BrowserInputError("每个平台请选择一个文件；联合文件可以单独导入。")
        self._prepared = values
        return {"ready": True}

    def discard(self):
        self._prepared = None
        return {"discarded": True}

    def commit(self):
        if self._prepared is None:
            raise BrowserInputError("尚未选择有效的音乐数据。")
        values, self._prepared = self._prepared, None
        records = {} if self._demo else dict(self._datasets)
        for data in values:
            provider = data["export_meta"]["provider"]
            if provider == "combined":
                records.update(data["platforms"])
                records["combined"] = data
            else:
                records[provider] = data
                records.pop("combined", None)
        if {"netease", "qq_music"} <= records.keys() and "combined" not in records:
            records["combined"] = build_combined(records["netease"], records["qq_music"])
        self._datasets = records
        self._selected = "combined" if "combined" in records else values[-1]["export_meta"]["provider"]
        self._demo = False
        return self.snapshot()

    def snapshot(self):
        data = self._datasets.get(self._selected)
        if data is None:
            return {"version": __version__, "dashboard": None, "sources": [], "topics": [], "demo": False}
        combined = self._selected == "combined"
        return {"version": __version__, "dashboard": dashboard_data(data, combined=combined),
                "sources": [{"id": key, "label": SOURCE_NAMES[key]} for key in self._datasets],
                "selected": self._selected, "topics": topic_cards(data, combined=combined),
                "time_coverage": {key: sum((platform.get("statistics") or {}).get(key, 0)
                                          for platform in (list(data["platforms"].values()) if combined else [data]))
                                  for key in ("liked_songs_with_time", "playlists_with_creation_time",
                                              "playlists_with_subscription_time")},
                "filename": "music_for_ai_combined.json" if combined else "music_for_ai.json",
                "demo": self._demo}

    def select(self, provider):
        if provider not in self._datasets:
            raise BrowserInputError("尚未导入这个平台的数据。")
        self._selected = provider
        return self.snapshot()

    def topic(self, number):
        data = self._datasets.get(self._selected)
        if data is None or (number == 13 and self._selected != "combined"):
            raise BrowserInputError("请先导入对应平台的音乐数据。")
        topic = next((item for item in TOPICS if item.number == number), None)
        if topic is None:
            raise BrowserInputError("没有这个分析方向。")
        card = next(item for item in topic_cards(data, combined=self._selected == "combined")
                    if item["number"] == number)
        return {**card, "prompt": prompt_for(topic, combined=self._selected == "combined", data=data),
                "filename": self.snapshot()["filename"]}

    def search(self, query="", page=1):
        data = self._datasets.get(self._selected)
        if data is None:
            return {"results": [], "total": 0, "page": 1, "pages": 1}
        if not isinstance(query, str) or len(query) > 200 or not isinstance(page, int) or page < 1:
            raise BrowserInputError("搜索内容太长或页码无效。")
        songs = ([group["sources"][0] for group in data["matched_catalog"]]
                 if self._selected == "combined" else data["song_catalog"])
        query = query.casefold().strip()
        hits = [song for song in songs if not query or any(
            query in (song.get(key) or "").casefold() for key in ("name", "artists", "album"))]
        pages = max(1, (len(hits) + 39) // 40)
        page = min(page, pages)
        return {"total": len(hits), "page": page, "pages": pages,
                "results": [{key: song.get(key) for key in ("name", "artists", "album", "liked_at")}
                            for song in hits[(page - 1) * 40:page * 40]]}

    def download(self, name):
        data = self._datasets.get(self._selected)
        if data is None:
            raise BrowserInputError("请先导入音乐数据，再导出文件。")
        allowed = {self.snapshot()["filename"], "AI_ANALYSIS_GUIDE.md", "MusicInsight-export.zip",
                   "music_summary_combined.md" if self._selected == "combined" else "music_summary.md"}
        if name not in allowed:
            raise BrowserInputError("不支持导出这个文件。")
        with TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (write_combined if self._selected == "combined" else write_reports)(folder, data)
            if name != "MusicInsight-export.zip":
                return {"name": name, "content": (folder / name).read_text(encoding="utf-8"),
                        "binary": False, "mime": "application/json" if name.endswith(".json") else "text/markdown;charset=utf-8"}
            stream = BytesIO()
            with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
                for path in sorted(folder.rglob("*")):
                    if path.is_file():
                        archive.write(path, path.relative_to(folder).as_posix())
            return {"name": name, "content": base64.b64encode(stream.getvalue()).decode("ascii"),
                    "binary": True, "mime": "application/zip"}

    def clear(self):
        self._datasets.clear()
        self._selected = self._prepared = None
        self._demo = False
        return self.snapshot()

    def demo(self, texts):
        self.clear()
        self.prepare(texts)
        self.commit()
        self._demo = True
        return self.snapshot()
