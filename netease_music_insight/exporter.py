"""Resumable, sequential export using the existing local API endpoints."""
import time
from pathlib import Path

from .api import ApiError, LoginExpired
from .report import build_data, song_row, write_reports
from .utils import atomic_json, read_json, safe_name


def _timestamp(value):
    if not value:
        return None
    from datetime import datetime
    try:
        return datetime.fromtimestamp(int(value) / 1000).astimezone().isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return None


class ExportService:
    def __init__(self, api, root: Path, notify=None, *, fresh=False, output_dir=None):
        self.api = api
        self.root = root
        self.output_dir = Path(output_dir) if output_dir is not None else root / "output"
        self.notify = notify or (lambda message: None)
        self.fresh = fresh
        self.issues = []
        self.index_incomplete = False

    def _cached(self, path, fetch):
        if not self.fresh and path.exists() and time.time() - path.stat().st_mtime < 86400:
            data = read_json(path)
            if data is not None:
                return data
        data = fetch()
        atomic_json(path, data)
        return data

    def _song_details(self, ids):
        rows = []
        for start in range(0, len(ids), 300):
            block = ids[start:start + 300]
            try:
                data = self.api.get("/song/detail", {"ids": ",".join(map(str, block))}, timeout=60)
                songs = data.get("songs")
                if not isinstance(songs, list):
                    raise ApiError("歌曲详情为空或格式异常。")
                rows.extend(filter(None, (song_row(s) for s in songs)))
            except ApiError as exc:
                self.notify(f"! 喜欢列表第 {start + 1}–{start + len(block)} 首暂不可用：{exc}")
            self.notify(f"喜欢音乐：{min(start + 300, len(ids))}/{len(ids)}")
        return rows

    def _playlist_index(self, uid):
        playlists, offset = [], 0
        while True:
            try:
                data = self.api.get("/user/playlist", {"uid": uid, "limit": 100, "offset": offset}, timeout=60)
            except ApiError as exc:
                if not playlists:
                    raise
                self.issues.append(f"歌单列表在第 {offset + 1} 个位置中断：{exc}")
                self.index_incomplete = True
                break
            batch = data.get("playlist")
            if not isinstance(batch, list):
                raise ApiError("歌单列表格式异常。")
            playlists.extend(batch)
            if not data.get("more") or not batch:
                break
            offset += len(batch)
        return playlists

    def _tracks(self, playlist):
        rows, offset, limit = [], 0, 500
        while True:
            data = self.api.get("/playlist/track/all", {"id": playlist["id"], "limit": limit, "offset": offset}, timeout=60)
            batch = data.get("songs")
            if not isinstance(batch, list):
                raise ApiError("歌单歌曲格式异常。")
            rows.extend(filter(None, (song_row(song) for song in batch)))
            if len(batch) < limit:
                break
            offset += limit
        return rows

    def run(self, profile):
        uid = profile["userId"]
        nickname = profile.get("nickname") or "网易云用户"
        folder = self.output_dir / f"{safe_name(nickname)}_{uid}"
        cache = self.root / ".cache" / str(uid)
        cache.mkdir(parents=True, exist_ok=True)
        folder.mkdir(parents=True, exist_ok=True)
        self.notify(f"账号：{nickname}（UID {uid}）")

        self.notify("[1/4] 获取喜欢音乐……")
        liked_ids = self._cached(cache / "liked_ids.json", lambda: self._liked_ids(uid))
        liked = self._cached(cache / "liked_songs.json", lambda: self._song_details(liked_ids))
        if len(liked) < len(set(map(str, liked_ids))):
            existing = {str(song["id"]) for song in liked}
            missing = [sid for sid in liked_ids if str(sid) not in existing]
            recovered = self._song_details(missing)
            if recovered:
                liked.extend(recovered)
                atomic_json(cache / "liked_songs.json", liked)
        if len(liked) < len(set(map(str, liked_ids))):
            self.issues.append(f"喜欢歌曲详情仅获取 {len(liked)}/{len(set(map(str, liked_ids)))} 首；部分歌曲可能已下架。")
        self.notify(f"✓ 喜欢音乐：{len(liked)} 首")

        self.notify("[2/4] 获取歌单与歌曲……")
        index = self._cached(cache / "playlist_index.json", lambda: self._playlist_index(uid))
        if self.index_incomplete:
            (cache / "playlist_index.json").unlink(missing_ok=True)
        playlists = []
        liked_times = {}
        liked_list = next((item for item in index if item.get("specialType") == 5
                           and str((item.get("creator") or {}).get("userId")) == str(uid)), None)
        if liked_list:
            try:
                detail = self._cached(cache / "liked_playlist_detail.json",
                                      lambda: self.api.get("/playlist/detail", {"id": liked_list["id"]}, timeout=60))
                for entry in (detail.get("playlist") or {}).get("trackIds") or []:
                    if entry.get("id") and entry.get("at"):
                        liked_times[str(entry["id"])] = _timestamp(entry["at"])
            except ApiError as exc:
                self.issues.append(f"逐首喜欢时间未获取：{exc}")
        for song in liked:
            song["liked_at"] = liked_times.get(str(song["id"]))
        for n, item in enumerate(index, 1):
            pid = item.get("id")
            if not pid:
                self.issues.append("遇到缺少 ID 的歌单，已跳过。")
                continue
            name = item.get("name") or str(pid)
            try:
                tracks = self._cached(cache / "playlists" / f"{pid}.json", lambda item=item: self._tracks(item))
            except LoginExpired:
                raise
            except ApiError as exc:
                self.issues.append(f"歌单《{name}》无法访问：{exc}")
                self.notify(f"! {n}/{len(index)} 《{name}》已跳过")
                continue
            count = item.get("trackCount") or len(tracks)
            if len(tracks) < count:
                self.issues.append(f"歌单《{name}》可获取 {len(tracks)}/{count} 首；可能包含下架歌曲。")
            creator = item.get("creator") or {}
            playlists.append({
                "id": pid,
                "name": name,
                "creator": creator.get("nickname") or "",
                "creator_user_id": creator.get("userId"),
                "created_by_user": str(creator.get("userId")) == str(uid),
                "created_at": _timestamp(item.get("createTime")),
                "subscribed_at": _timestamp(item.get("subscribedTime")),
                "track_count": count,
                "tracks": tracks,
            })
            if n == len(index) or n % 10 == 0:
                self.notify(f"✓ 歌单进度 {n}/{len(index)}")

        self.notify("[3/4] 获取可用播放记录……")
        try:
            history = self._cached(cache / "play_history.json", lambda: self._history(uid))
            history_available = True
        except LoginExpired:
            raise
        except ApiError as exc:
            history = []
            history_available = False
            self.issues.append(f"播放记录未获取：{exc}")
        self.notify(f"✓ 可用播放记录：{len(history)} 条")

        self.notify("[4/4] 生成 AI 数据与提示词……")
        data = build_data(profile, liked, playlists, history, self.issues,
                          expected_liked=len(liked_ids), expected_playlists=len(index))
        data["data_availability"] = {"play_history": {"available": history_available,
            "reason": None if history_available else "网易云本次未返回可用播放记录。"}}
        write_reports(folder, data)
        raw = folder / "raw"
        atomic_json(raw / "liked_ids.json", liked_ids)
        atomic_json(raw / "playlist_index.json", index)
        self.notify(f"数据检查：喜欢 {len(liked)}/{len(liked_ids)}；歌单 {len(playlists)}/{len(index)}；"
                    f"歌曲位置 {data['statistics']['playlist_song_positions']}，去重 {data['statistics']['unique_song_count']}；"
                    f"问题 {len(self.issues)} 项")
        return folder, data

    def _liked_ids(self, uid):
        data = self.api.get("/likelist", {"uid": uid}, timeout=60)
        ids = data.get("ids")
        if not isinstance(ids, list):
            raise ApiError("喜欢列表为空或格式异常。")
        return ids

    def _history(self, uid):
        data = self.api.get("/user/record", {"uid": uid, "type": 0}, timeout=60)
        raw = data.get("allData")
        if raw is None:
            raw = data.get("weekData")
        if not isinstance(raw, list):
            raise ApiError("播放记录为空或格式异常。")
        result = []
        for item in raw:
            song = song_row(item.get("song")) if isinstance(item, dict) else None
            if song:
                song["play_count"] = item.get("playCount")
                song["score"] = item.get("score")
                result.append(song)
        return result
