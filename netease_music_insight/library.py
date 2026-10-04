"""Paged factual browsing shared by all interactive interfaces."""
from .guidance import guide_markdown


def platforms(data):
    return data.get("platforms", {}) if "platforms" in data else {data["export_meta"].get("provider", "netease"): data}


def browse(data, kind="catalog", query="", page=1, playlist_id=None):
    if kind not in {"catalog", "liked", "playlists", "playlist", "history"}:
        raise ValueError("Unknown library view")
    if not isinstance(query, str) or len(query) > 200 or not isinstance(page, int) or page < 1:
        raise ValueError("Invalid search")
    if data is None:
        return {"ok": True, "results": [], "total": 0, "page": 1, "pages": 1, "reason": "先整理音乐数据。"}
    results = []
    title = ""
    needle = query.strip().casefold()
    for provider, platform in platforms(data).items():
        playlists = platform.get("playlists", [])
        names = {str(p["id"]): p["name"] for p in playlists}
        catalog = {str(s["id"]): s for s in platform.get("song_catalog", [])}
        if kind == "playlists":
            results += [{"id": provider + ":" + str(p["id"]), "name": p["name"], "provider": provider,
                         "owned": p.get("created_by_user", False), "count": len(p.get("tracks", [])),
                         "expected": p.get("track_count"), "created_at": p.get("created_at"),
                         "subscribed_at": p.get("subscribed_at"), "favorite_order_at": p.get("favorite_order_at")}
                        for p in playlists if not needle or needle in p["name"].casefold()]
            continue
        songs = platform.get({"catalog": "song_catalog", "liked": "liked_songs", "history": "play_history"}.get(kind, "song_catalog"), [])
        if kind == "playlist":
            playlist = next((p for p in playlists if provider + ":" + str(p["id"]) == playlist_id), None)
            if playlist is None:
                continue
            title, songs = playlist["name"], playlist.get("tracks", [])
        for song in songs:
            if needle and not any(needle in str(song.get(key) or "").casefold() for key in ("name", "artists", "album")):
                continue
            indexed = catalog.get(str(song["id"]), {})
            results.append({"name": song.get("name", ""), "artists": song.get("artists", ""),
                            "album": song.get("album", ""), "provider": provider,
                            "liked": indexed.get("liked", False),
                            "playlists": [names[str(pid)] for pid in indexed.get("playlist_ids", []) if str(pid) in names],
                            "liked_at": song.get("liked_at"), "added_at": song.get("added_at"),
                            "play_count": song.get("play_count") if kind == "history" else None})
    pages = max(1, (len(results) + 39) // 40)
    page = min(page, pages)
    reason = ""
    if kind == "history":
        reason = "网易云播放记录仅为平台可返回范围，QQ 音乐没有可靠完整播放历史；缺失不代表没有听歌。"
    return {"ok": True, "results": results[(page - 1) * 40:page * 40], "total": len(results),
            "page": page, "pages": pages, "title": title, "reason": reason}


def usage_guide(data):
    if data is None:
        return {"ok": False, "message": "请先整理音乐数据。"}
    return {"ok": True, "text": guide_markdown(data, combined="platforms" in data)}
