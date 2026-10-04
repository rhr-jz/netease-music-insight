"""Read existing local exports for the desktop Dashboard and AI Center."""
from collections import Counter
from datetime import datetime
from pathlib import Path

from ..guidance import TOPICS, available_topics
from ..utils import read_json


FILE_NAMES = (
    ("music_for_ai.json", "上传给 AI 的音乐数据"),
    ("music_summary.md", "自己阅读的音乐摘要"),
    ("AI_ANALYSIS_GUIDE.md", "AI 分析方向与提示词"),
)
COMBINED_FILE_NAMES = (
    ("music_for_ai_combined.json", "上传给 AI 的双平台联合数据"),
    ("music_summary_combined.md", "两个平台的音乐摘要"),
    ("AI_ANALYSIS_GUIDE.md", "AI 分析方向与提示词"),
)
SOURCE_NAMES = {"netease": "网易云音乐", "qq_music": "QQ 音乐",
                "combined": "两个平台"}
DISPLAY_TOPICS = {
    1: ("音乐全景画像", "我到底是一个怎样的听歌的人？"),
    2: ("真实音乐审美", "我真正喜欢的声音是什么？"),
    3: ("核心歌手", "我真正喜欢哪些音乐人？"),
    4: ("听歌习惯", "我是如何发现、收藏和反复听音乐的？"),
    5: ("音乐成长轨迹", "我的音乐偏好可能经历了怎样的变化？"),
    6: ("我的音乐地图", "我的音乐世界已经延伸到哪里？"),
    7: ("审美盲区", "还有哪些音乐离我的口味只有一步？"),
    8: ("同龄人音乐谈资", "有哪些音乐人和音乐文化值得了解？"),
    9: ("系统听歌计划", "怎样在轻松的情况下逐渐形成自己的音乐品味？"),
    10: ("歌单整理", "我的收藏和歌单应该怎么重新整理？"),
    11: ("情绪与音乐", "不同情绪和生活场景下，我在听什么？"),
    12: ("年度音乐总结", "生成属于我的个人音乐年度回顾。"),
    13: ("网易云 / QQ音乐跨平台分析", "我在两个音乐平台上的行为有什么不同？"),
}


def discover_exports(output_dir):
    """Only consider the directory shapes produced by the existing exporters."""
    root = Path(output_dir)
    paths = [root / "combined" / "music_for_ai_combined.json"]
    paths.extend((root / "qq_music").glob("*/music_for_ai.json"))
    paths.extend(path for path in root.glob("*/music_for_ai.json")
                 if path.parent.name not in {"combined", "qq_music"})
    records = []
    for path in paths:
        try:
            if not path.is_file():
                continue
            modified = path.stat().st_mtime
        except OSError:
            continue
        provider = ("combined" if path.name == "music_for_ai_combined.json"
                    else "qq_music" if path.parent.parent.name == "qq_music"
                    else "netease")
        records.append({"path": path, "provider": provider, "modified": modified})
    records.sort(key=lambda item: item["modified"], reverse=True)
    for index, record in enumerate(records):
        record["id"] = index
    return records


def read_export(record):
    data = read_json(record["path"])
    if not isinstance(data, dict):
        return None
    if record["provider"] == "combined":
        platforms = data.get("platforms")
        if not isinstance(platforms, dict) or not {"netease", "qq_music"} <= platforms.keys():
            return None
    elif not isinstance(data.get("statistics"), dict) or not isinstance(data.get("song_catalog"), list):
        return None
    return data


def file_entries(folder, combined=False):
    names = COMBINED_FILE_NAMES if combined else FILE_NAMES
    return [{"name": name, "description": description, "path": str(folder / name)}
            for name, description in names if (folder / name).is_file()]


def source_entries(records):
    entries = []
    for record in records:
        try:
            updated = datetime.fromtimestamp(record["modified"]).astimezone().isoformat()
        except (OSError, OverflowError, ValueError):
            updated = ""
        entries.append({"id": record["id"],
                        "label": SOURCE_NAMES[record["provider"]],
                        "updated_at": updated})
    return entries


def _platforms(data, combined):
    return list(data["platforms"].values()) if combined else [data]


def _artist_names(song):
    return {name.strip() for name in (song.get("artists") or "").split(" / ")
            if name.strip()}


def dashboard_data(data, *, combined=False):
    platforms = _platforms(data, combined)
    liked_songs = [song for platform in platforms for song in platform.get("liked_songs", [])]
    artist_counts = Counter()
    album_counts = Counter()
    for song in liked_songs:
        artist_counts.update(_artist_names(song))
        if song.get("album"):
            album_counts[song["album"]] += 1
    if combined:
        catalog = [group["sources"][0] for group in data.get("matched_catalog", [])
                   if group.get("sources")]
        unique = data["statistics"]["combined_unique_tracks"]
    else:
        catalog = data.get("song_catalog", [])
        unique = data["statistics"]["unique_song_count"]
    artists = {name for song in catalog for name in _artist_names(song)}
    playlists = [playlist for platform in platforms for playlist in platform.get("playlists", [])]
    stats = [platform.get("statistics") or {} for platform in platforms]
    platform_counts = [
        {"name": SOURCE_NAMES.get((platform.get("export_meta") or {}).get("provider"),
                                  "音乐平台"),
         "liked": stat.get("liked_song_count", 0),
         "playlists": stat.get("playlist_count", 0),
         "unique": stat.get("unique_song_count", 0)}
        for platform, stat in zip(platforms, stats)
    ]
    meta = data.get("export_meta") or {}
    return {
        "liked": sum(stat.get("liked_song_count", 0) for stat in stats),
        "playlists": sum(stat.get("playlist_count", 0) for stat in stats),
        "unique": unique, "artists": len(artists),
        "albums": len({song.get("album") for song in catalog if song.get("album")}),
        "history": sum(len(platform.get("play_history", [])) for platform in platforms),
        "coverage": [str(issue.get("type", "数据缺口")) if isinstance(issue, dict) else "数据缺口"
                     for platform in platforms for issue in platform.get("export_meta", {}).get("issues", [])],
        "top_artists": [{"name": name, "count": count}
                        for name, count in artist_counts.most_common(6)],
        "top_albums": [{"name": name, "count": count}
                       for name, count in album_counts.most_common(5)],
        "created_playlists": sum(stat.get("created_playlist_count", 0) for stat in stats),
        "subscribed_playlists": sum(stat.get("subscribed_playlist_count", 0) for stat in stats),
        "largest_playlist": max((playlist.get("track_count") or len(playlist.get("tracks", []))
                                 for playlist in playlists), default=0),
        "source": SOURCE_NAMES["combined"] if combined else platform_counts[0]["name"],
        "updated_at": meta.get("exported_at") or "",
        "status": meta.get("status") or "unknown",
        "platforms": platform_counts if combined else [],
    }


def topic_cards(data, *, combined=False):
    available = {topic.number for topic in available_topics(data, combined=combined)}
    cards = []
    for topic in TOPICS:
        if topic.number == 13 and not combined:
            continue
        reason = ""
        if topic.number not in available:
            reason = ("缺少可靠的收藏或歌单时间；AI 只能说明数据不足。"
                      if topic.number in {5, 12} else
                      "当前没有可整理的歌单。")
        title, question = DISPLAY_TOPICS[topic.number]
        cards.append({"number": topic.number, "title": title,
                      "question": question, "scope": topic.scope,
                      "network": topic.network, "depth": topic.depth,
                      "available": topic.number in available, "reason": reason})
    return cards
