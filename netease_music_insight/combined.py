"""Conservative cross-platform catalog matching and joint AI documents."""
import re
import unicodedata
from datetime import datetime

from .utils import atomic_json, atomic_text
from .guidance import write_guidance


def _key(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value or "").casefold())


def _match(left, right):
    if not _key(left.get("name")) or _key(left.get("name")) != _key(right.get("name")):
        return False
    la = {_key(s) for s in (left.get("artists") or "").split(" / ") if _key(s)}
    ra = {_key(s) for s in (right.get("artists") or "").split(" / ") if _key(s)}
    if not la or la != ra:
        return False
    a, b = left.get("duration_ms"), right.get("duration_ms")
    return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= 2000


def _title_artist_key(song):
    artists = frozenset(_key(s) for s in (song.get("artists") or "").split(" / ") if _key(s))
    return _key(song.get("name")), artists


def build_combined(netease, qq):
    groups = []
    used_qq = set()
    qq_songs = [{"provider": "qq_music", **song} for song in qq.get("song_catalog", [])]
    qq_index = {}
    for i, song in enumerate(qq_songs):
        qq_index.setdefault(_title_artist_key(song), []).append(i)
    for song in netease.get("song_catalog", []):
        song = {"provider": "netease", **song}
        candidates = [i for i in qq_index.get(_title_artist_key(song), [])
                      if i not in used_qq and _match(song, qq_songs[i])]
        if len(candidates) == 1:
            i = candidates[0]
            used_qq.add(i)
            groups.append({"name": song["name"], "artists": song["artists"],
                           "match_confidence": "high", "same_recording": True,
                           "sources": [song, qq_songs[i]]})
        else:
            groups.append({"name": song["name"], "artists": song["artists"],
                           "match_confidence": "unmatched", "same_recording": None,
                           "sources": [song]})
    for i, song in enumerate(qq_songs):
        if i not in used_qq:
            groups.append({"name": song["name"], "artists": song["artists"],
                           "match_confidence": "unmatched", "same_recording": None,
                           "sources": [song]})
    return {
        "export_meta": {"provider": "combined", "exported_at": datetime.now().astimezone().isoformat(),
                        "status": "partial" if any(d["export_meta"]["status"] == "partial" for d in (netease, qq)) else "complete",
                        "matching_rule": "相同标准化标题、相同歌手集合、时长差不超过 2 秒且匹配唯一时自动合并。"},
        "platforms": {"netease": netease, "qq_music": qq},
        "matched_catalog": groups,
        "statistics": {"netease_unique_tracks": len(netease.get("song_catalog", [])),
                       "qq_music_unique_tracks": len(qq_songs),
                       "cross_platform_high_confidence_matches": len(used_qq),
                       "combined_unique_tracks": len(groups)},
    }


def write_combined(folder, data):
    stats = data["statistics"]
    atomic_json(folder / "music_for_ai_combined.json", data)
    atomic_text(folder / "music_summary_combined.md", f"""# 双平台音乐数据概要

导出时间：{data['export_meta']['exported_at']}

- 网易云去重歌曲：{stats['netease_unique_tracks']}
- QQ 音乐去重歌曲：{stats['qq_music_unique_tracks']}
- 高置信跨平台匹配：{stats['cross_platform_high_confidence_matches']}
- 联合去重歌曲：{stats['combined_unique_tracks']}

{data['export_meta']['matching_rule']} 不确定的版本保持分开。两个平台的收藏时间、歌单时间和数据缺口分别保留在 platforms 中。
""")
    atomic_text(folder / "AI_ANALYSIS_PROMPT_COMBINED.md", """# 双平台音乐分析提示词

请读取 `music_for_ai_combined.json`，用中文分析网易云音乐与 QQ 音乐的个人数据。先核对两个平台各自的导出状态和可用能力。播放历史只在实际可用的平台上分析，不能把 QQ 的空历史解释为不听歌。

比较两个平台的喜欢歌曲、主动创建歌单、收藏歌单、跨平台高置信重复歌曲和歌手。时间字段仅在非空时用于判断偏好变化；QQ 的 `favorite_order_at` 是收藏排序时间，不保证等于首次收藏日期。不得用歌单顺序推测收藏时间。平台差异可能来自使用场景或平台推荐，不能直接解释为人格差异。

区分核心审美、阶段偏好、怀旧和功能性音乐，引用具体曲目或歌单作为证据。按 70% 熟悉、20% 邻近探索、10% 陌生探索给出八周可实践的听歌计划。若能联网，可核查当前 18–25 岁人群的音乐谈资并注明来源和时间。不要编造热度或用户的播放行为。
""")
    write_guidance(folder, data, combined=True)


def comparison_data(data):
    """Factual cross-platform summary derived from the existing matched catalog."""
    if not data or "platforms" not in data:
        return None
    net, qq = data["platforms"]["netease"], data["platforms"]["qq_music"]
    groups = data.get("matched_catalog", [])
    common = [group for group in groups if group.get("match_confidence") == "high"]
    unique = {provider: [group for group in groups if len(group["sources"]) == 1 and group["sources"][0].get("provider") == provider]
              for provider in ("netease", "qq_music")}
    artists = {}
    for provider, platform in (("netease", net), ("qq_music", qq)):
        artists[provider] = {_key(name): name.strip() for song in platform.get("song_catalog", [])
                             for name in (song.get("artists") or "").split(" / ") if _key(name)}
    shared = sorted(artists["netease"].keys() & artists["qq_music"].keys())
    return {"common_tracks": len(common), "netease_only": len(unique["netease"]),
            "qq_only": len(unique["qq_music"]), "common_artists_count": len(shared),
            "common_artists": [artists["netease"][key] for key in shared[:20]],
            "netease_only_artists": [artists["netease"][key] for key in sorted(artists["netease"].keys() - artists["qq_music"].keys())[:20]],
            "qq_only_artists": [artists["qq_music"][key] for key in sorted(artists["qq_music"].keys() - artists["netease"].keys())[:20]],
            "sample_common": [{"name": group["name"], "artists": group["artists"]} for group in common[:20]],
            "playlists": [{"provider": provider, "created": sum(p.get("created_by_user") is True for p in platform.get("playlists", [])),
                           "subscribed": sum(p.get("created_by_user") is not True for p in platform.get("playlists", []))}
                          for provider, platform in (("netease", net), ("qq_music", qq))]}
