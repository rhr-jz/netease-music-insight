"""Normalize songs, compute factual statistics, and write AI-facing documents."""
from collections import Counter
from datetime import datetime

from .utils import atomic_json, atomic_text


HISTORY_NOTE = "播放历史受网易云服务端可返回范围限制，不等于账号完整终身播放历史。"


def song_row(song):
    if not isinstance(song, dict):
        return None
    artists = song.get("ar") or song.get("artists") or []
    album = song.get("al") or song.get("album") or {}
    if isinstance(artists, str):
        artist_text = artists
    else:
        artist_text = " / ".join(a.get("name", "") for a in artists if isinstance(a, dict))
    if not song.get("id"):
        return None
    return {
        "id": song["id"],
        "name": song.get("name") or "",
        "artists": artist_text,
        "album": album.get("name", "") if isinstance(album, dict) else "",
        "duration_ms": song.get("dt") or song.get("duration") or None,
    }


def unique_songs(songs):
    by_id = {}
    for song in songs:
        if song and song.get("id") is not None:
            by_id.setdefault(str(song["id"]), song)
    return list(by_id.values())


def top_artists(songs, limit=10, weighted=False):
    counts = Counter()
    for song in songs:
        names = {name.strip() for name in (song.get("artists") or "").split(" / ") if name.strip()}
        for name in names:
            counts[name] += (song.get("play_count") or 0) if weighted else 1
    return [{"name": name, "count": count} for name, count in counts.most_common(limit)]


def top_albums(songs, limit=10):
    counts = Counter(s.get("album") for s in songs if s.get("album"))
    return [{"name": name, "count": count} for name, count in counts.most_common(limit)]


def build_data(profile, liked, playlists, history, issues=None, expected_liked=None, expected_playlists=None):
    uid = profile["userId"]
    liked = unique_songs(liked)
    normalized_playlists = []
    catalog = {}
    for song in liked:
        catalog[str(song["id"])] = {**song, "liked": True, "playlist_ids": []}
    for playlist in playlists:
        tracks = unique_songs(playlist.get("tracks", []))
        normalized = {**playlist, "tracks": tracks, "track_count": playlist.get("track_count", len(tracks))}
        normalized_playlists.append(normalized)
        for song in tracks:
            key = str(song["id"])
            if key not in catalog:
                catalog[key] = {**song, "liked": False, "playlist_ids": []}
            catalog[key]["playlist_ids"].append(playlist["id"])
    owned = sum(p.get("created_by_user") is True for p in normalized_playlists)
    positions = sum(len(p["tracks"]) for p in normalized_playlists)
    issues = issues or []
    stats = {
        "liked_song_count": len(liked),
        "liked_song_expected": expected_liked,
        "playlist_count": len(normalized_playlists),
        "playlist_expected": expected_playlists,
        "created_playlist_count": owned,
        "subscribed_playlist_count": len(normalized_playlists) - owned,
        "playlist_song_positions": positions,
        "unique_song_count": len(catalog),
        "play_history_count": len(history),
        "top_artists_in_likes": top_artists(liked),
        "top_albums_in_likes": top_albums(liked),
        "top_artists_in_history_by_play_count": top_artists(history, weighted=True),
    }
    return {
        "export_meta": {
            "exported_at": datetime.now().astimezone().isoformat(),
            "source": "NetEase Cloud Music",
            "status": "partial" if issues else "complete",
            "notes": HISTORY_NOTE,
            "issues": issues,
        },
        "user_profile": {"uid": uid, "nickname": profile.get("nickname") or "网易云用户"},
        "liked_songs": liked,
        "playlists": normalized_playlists,
        "song_catalog": list(catalog.values()),
        "play_history": history,
        "statistics": stats,
    }


def summary_markdown(data):
    profile, stats = data["user_profile"], data["statistics"]
    def lines(items):
        return "\n".join(f"- {item['name']}：{item['count']}" for item in items) or "- 暂无可用数据"
    playlists = "\n".join(
        f"- {p['name']}（{'自建' if p['created_by_user'] else '收藏'}，可获取 {len(p['tracks'])}/{p['track_count']} 首）"
        for p in data["playlists"]
    ) or "- 暂无可用歌单"
    issues = "\n".join(f"- {issue}" for issue in data["export_meta"]["issues"]) or "- 无"
    return f"""# 我的网易云音乐数据

账号：{profile['nickname']}（UID {profile['uid']}）
导出时间：{data['export_meta']['exported_at']}

## 数据概况

- 喜欢音乐：{stats['liked_song_count']} 首（接口返回 {stats['liked_song_expected']} 个 ID）
- 歌单：{stats['playlist_count']} / {stats['playlist_expected']} 个；自建 {stats['created_playlist_count']}，收藏 {stats['subscribed_playlist_count']}
- 歌单歌曲位置：{stats['playlist_song_positions']}；全部去重歌曲：{stats['unique_song_count']}
- 可获取播放记录：{stats['play_history_count']} 条

## 喜欢音乐中出现最多的歌手

{lines(stats['top_artists_in_likes'])}

## 喜欢音乐中出现最多的专辑

{lines(stats['top_albums_in_likes'])}

## 可获取播放记录中播放次数较多的歌手

{lines(stats['top_artists_in_history_by_play_count'])}

## 我的歌单

{playlists}

## 数据检查与说明

- 状态：{data['export_meta']['status']}
- {HISTORY_NOTE}
- 歌单内重复歌曲按歌曲 ID 去重，song_catalog 保留了歌曲属于哪些歌单。
- 无权限、下架或接口失败的内容可能缺失；请查看下面的问题列表。

### 问题

{issues}
"""


PROMPT = """# AI 音乐品味分析提示词

请读取我上传的 `music_for_ai.json`，用中文为我做一份有证据、可实践的个人音乐分析。先检查 `export_meta.status`、`issues` 和 `statistics`，说明数据覆盖范围。播放历史受网易云服务端限制，不代表账号完整终身播放历史；歌单中的曲目可能是他人整理或功能性收藏。

## 分析任务

1. **真实偏好**：结合喜欢歌曲、自建歌单、收藏歌单和可获取播放记录，区分长期审美、阶段性偏好、怀旧、功能性音乐、热歌收藏、情绪型收藏及随机收藏。只在有证据时分类。
2. **核心歌手**：辨别核心歌手、高潜力歌手、单曲型歌手和历史型歌手。比较收藏与播放是否一致，指出可能只是早期收藏的歌。
3. **个人音乐地图**：画出“已有审美 → 邻近风格 → 值得探索的音乐”路径。讨论偏单曲还是专辑、对推荐算法的依赖、歌手集中度和跨类型探索，但没有足够信息时说明无法判断。
4. **有趣且可行的探索**：按 70% 熟悉音乐、20% 邻近探索、10% 陌生音乐设计听歌方法。给出 8 周计划，每周一个主题、一个核心音乐人或专辑、3–6 首歌、一个音乐知识点和一个简短问题；不要要求写长篇乐评。
5. **同龄人音乐谈资**：把“我真正喜欢的”和“值得知道的公共音乐语汇”分开。如果能够联网，请核查当前中国约 18–25 岁人群中的歌手、乐队、音乐节、热门专辑、独立音乐、Hip-Hop、R&B、摇滚及 Livehouse 等话题，给出来源和时间。不能联网就明确说明时效限制，不要编造最新热度，也不要只列热歌榜。
6. **最后用几句话回答**：我喜欢什么音乐、为什么可能喜欢、最喜欢哪些歌手、最近可能在探索什么。区分事实、推测和待验证的问题。

## 证据与边界

- 引用我数据中的具体歌曲、歌手或歌单作为证据，注明来自喜欢、歌单还是可获取播放记录。
- 收藏数量不等于喜欢程度；不要凭一首歌推断人格，不要给我贴模糊人格标签。
- 不把小众当高级，也不把流行当低级。保持听歌的娱乐属性。
- 若 `export_meta.status` 是 `partial`，先列出缺失范围，降低结论确定性。
- 每一步推荐控制数量，不要一次推荐 100 首；优先从现有审美自然向外扩展。
- 不要把上传的个人数据分享给其他人或外部服务。
"""


def write_reports(folder, data):
    atomic_json(folder / "music_for_ai.json", data)
    atomic_text(folder / "music_summary.md", summary_markdown(data))
    atomic_text(folder / "AI_ANALYSIS_PROMPT.md", PROMPT)
