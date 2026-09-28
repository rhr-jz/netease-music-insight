"""QQ Music account metadata export through QQMusicApi 0.7.3.

Only read-only account endpoints are used. Credentials live in memory for this run.
"""
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

from ..api import ApiError
from ..errors import ExportCancelled
from ..report import build_data, write_reports
from ..utils import atomic_json, read_json, safe_name
from .base import MusicProvider


def _dict(value):
    return value.model_dump() if hasattr(value, "model_dump") else dict(value or {})


def _date(value):
    """Preserve only plausible provider timestamps, without inventing dates."""
    if not value:
        return None
    if isinstance(value, str) and not value.isdigit():
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        except ValueError:
            return None
    try:
        seconds = int(value)
        if seconds > 10**12:
            seconds /= 1000
        if not 946684800 <= seconds <= 4102444800:
            return None
        return datetime.fromtimestamp(seconds).astimezone().isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def qq_song_row(value):
    song = _dict(value)
    sid = song.get("id")
    mid = song.get("mid") or song.get("songmid")
    if not sid and not mid:
        return None
    singers = song.get("singer") or song.get("artists") or []
    if isinstance(singers, dict):
        singers = [singers]
    artists = [{"id": str(s.get("id") or ""), "mid": str(s.get("mid") or ""),
                "name": s.get("name") or ""} for s in singers if isinstance(s, dict)]
    album = song.get("album") or {}
    if not isinstance(album, dict):
        album = {}
    duration = song.get("interval")
    return {
        "provider": "qq_music", "id": str(sid or mid),
        "provider_song_id": str(sid or ""), "provider_song_mid": str(mid or ""),
        "name": song.get("name") or song.get("title") or "",
        "artists": " / ".join(a["name"] for a in artists if a["name"]),
        "artist_details": artists,
        "album": album.get("name") or "",
        "album_details": {"id": str(album.get("id") or ""), "mid": str(album.get("mid") or ""),
                          "name": album.get("name") or ""},
        "duration_ms": int(duration * 1000) if isinstance(duration, (int, float)) and duration >= 0 else None,
        "liked_at": _date(song.get("liked_at") or song.get("fav_time") or song.get("collect_time")),
        "favorite_order_at": _date(song.get("order_time")),
        "added_at": _date(song.get("added_at") or song.get("add_time")),
    }


def qq_playlist_row(value, *, owned, uid):
    item = _dict(value)
    pid = item.get("id") or item.get("dissid")
    return {
        "provider": "qq_music", "id": str(pid or ""), "dirid": int(item.get("dirid") or 0),
        "name": item.get("title") or item.get("name") or str(pid or ""),
        "creator": item.get("nick") or item.get("nickname") or (str(uid) if owned else ""),
        "created_by_user": owned, "subscribed": not owned,
        "track_count": int(item.get("songnum") or 0),
        "created_at": _date(item.get("create_time")),
        "updated_at": _date(item.get("update_time")),
        "subscribed_at": None,
        "favorite_order_at": _date(item.get("order_time")) if not owned else None,
        "tracks": [],
    }


class QQMusicProvider(MusicProvider):
    name = "qq_music"
    capabilities = {"liked_songs": True, "playlists": True,
                    "playlist_tracks": True, "play_history": False}

    def __init__(self, root: Path, *, fresh=False, notify=None, client=None,
                 present_qr=None, check_cancel=None):
        self.root, self.fresh, self.notify = root, fresh, notify or (lambda message: None)
        self.present_qr = present_qr
        self.check_cancel = check_cancel
        if client is None:
            try:
                from qqmusic_api import Client, Platform
            except ImportError as exc:
                raise ApiError("QQ 音乐组件未安装，请运行一键运行.bat 安装依赖。") from exc
            (root / ".qqmusic").mkdir(parents=True, exist_ok=True)
            client = Client(platform=Platform.ANDROID, rate=2, capacity=2, connect_retries=2,
                            device_path=str(root / ".qqmusic" / "device.json"))
        self.client = client
        self.issues = []

    async def _request(self, request, label):
        for attempt in range(3):
            try:
                result = await asyncio.wait_for(request, timeout=60)
                if self.check_cancel:
                    self.check_cancel()
                return result
            except ExportCancelled:
                raise
            except Exception as exc:
                if attempt == 2:
                    raise ApiError(f"{label}请求失败或超时；请稍后重试。") from exc
                if self.check_cancel:
                    self.check_cancel()
                await asyncio.sleep(1.5 * (attempt + 1))

    async def login(self):
        from qqmusic_api.models.login import QRLoginType, QRCodeLoginEvents
        from qqmusic_api.modules.login_utils import QRCodeLoginSession
        for _ in range(3):
            if self.check_cancel:
                self.check_cancel()
            session = QRCodeLoginSession(self.client.login, QRLoginType.MOBILE,
                                         interval=1.5, timeout_seconds=180)
            try:
                qr = await asyncio.wait_for(session.get_qrcode(), 60)
                with tempfile.TemporaryDirectory() as temp:
                    path = qr.save(Path(temp))
                    if path and self.present_qr and self.present_qr(path):
                        self.notify(f"请使用 QQ 音乐 App 扫描二维码：{path}")
                    else:
                        self.notify(f"二维码窗口未能打开，请手动打开图片：{path}")
                    async for result in session.iter_events():
                        if self.check_cancel:
                            self.check_cancel()
                        if result.event == QRCodeLoginEvents.SCAN:
                            self.notify("已扫码，等待手机确认……")
                        elif result.event == QRCodeLoginEvents.CONF:
                            self.notify("已确认，正在登录……")
                        elif result.event == QRCodeLoginEvents.DONE:
                            if not result.credential:
                                raise ApiError("扫码已确认，但未收到登录凭据。")
                            self.client.credential = result.credential
                            if await self._request(self.client.login.check_expired(), "登录验证"):
                                raise ApiError("QQ 音乐登录凭据无效，请重新扫码。")
                            return await self.get_user_profile()
                        elif result.event == QRCodeLoginEvents.REFUSE:
                            raise ApiError("手机上拒绝了 QQ 登录。")
                        elif result.event == QRCodeLoginEvents.TIMEOUT:
                            self.notify("二维码已过期，正在刷新……")
                            break
            except (ApiError, ExportCancelled):
                raise
            except Exception as exc:
                raise ApiError("QQ 扫码登录失败，请检查网络后重试。") from exc
        raise ApiError("二维码多次过期，请重新启动后扫码。")

    async def get_user_profile(self):
        credential = self.client.credential
        uid = str(credential.musicid)
        euin = credential.encrypt_uin
        if not uid or uid == "0" or not euin:
            raise ApiError("QQ 登录成功，但没有收到完整的用户标识。")
        home = _dict(await self._request(self.client.user.get_homepage(euin), "用户资料"))
        base = _dict(home.get("base_info"))
        return {"userId": uid, "nickname": base.get("name") or "QQ音乐用户",
                "avatar": base.get("avatar") or "", "encrypted_uin": euin}

    async def _pages(self, factory, label, field):
        rows, expected, page = [], None, 1
        while True:
            response = _dict(await self._request(factory(page), label))
            batch = response.get(field)
            if batch is None and field == "songs":
                batch = response.get("songlist")
            if not isinstance(batch, list):
                raise ApiError(f"{label}返回格式异常。")
            expected = response.get("total", response.get("total_song_num", expected))
            rows.extend(batch)
            has_more = bool(response.get("hasmore"))
            if not batch or (not has_more and (expected is None or len(rows) >= int(expected))):
                break
            page += 1
            if page > 10000:
                raise ApiError(f"{label}页数异常。")
            await asyncio.sleep(0.35)
        if expected is not None and len(rows) < int(expected):
            self.issues.append(f"{label}仅获取 {len(rows)}/{expected} 项。")
        return rows, expected

    def _liked_request(self, euin, page):
        request = self.client.user.get_fav_song(euin, page=page, num=100)
        # The typed Song model omits provider-specific time fields. Use the
        # validated raw data to retain them when the endpoint supplies them.
        if hasattr(request, "disable_parse"):
            request.disable_parse = True
        return request

    def _cache(self, path, fetch):
        async def run():
            if not self.fresh and path.exists():
                import time
                if time.time() - path.stat().st_mtime < 86400:
                    cached = read_json(path)
                    if cached is not None:
                        return cached
            data = await fetch()
            atomic_json(path, data)
            return data
        return run()

    async def _tracks(self, playlist):
        pid, dirid = int(playlist["id"]), playlist["dirid"]
        values, expected = await self._pages(
            lambda page: self.client.songlist.get_detail(pid, dirid=dirid, num=100, page=page),
            f"歌单《{playlist['name']}》", "songs")
        tracks = [row for row in (qq_song_row(v) for v in values) if row]
        if playlist["track_count"] and len(tracks) < playlist["track_count"]:
            self.issues.append(f"歌单《{playlist['name']}》可获取 {len(tracks)}/{playlist['track_count']} 首。")
        return tracks

    async def export(self, profile):
        uid = profile["userId"]
        folder = self.root / "output" / "qq_music" / f"{safe_name(profile['nickname'])}_{safe_name(uid)}"
        cache = self.root / ".cache" / "qq_music" / safe_name(uid)
        folder.mkdir(parents=True, exist_ok=True)
        cache.mkdir(parents=True, exist_ok=True)
        euin = profile["encrypted_uin"]
        self.notify("[1/4] 获取我喜欢……")
        liked_raw, liked_expected = await self._cache(cache / "liked.json", lambda: self._pages(
            lambda page: self._liked_request(euin, page), "我喜欢", "songs"))
        liked = [row for row in (qq_song_row(v) for v in liked_raw) if row]
        self.notify(f"✓ 我喜欢：{len(liked)} 首")
        self.notify("[2/4] 获取自建与收藏歌单……")
        async def fetch_created():
            return _dict(await self._request(self.client.user.get_created_songlist(int(uid)), "自建歌单"))
        created = await self._cache(cache / "created_playlists.json", fetch_created)
        created_items = created.get("playlists") or []
        if created.get("total") is not None and len(created_items) < int(created["total"]):
            self.issues.append(f"自建歌单仅获取 {len(created_items)}/{created['total']} 个。")
        fav_items, fav_expected = await self._cache(cache / "favorite_playlists.json", lambda: self._pages(
            lambda page: self.client.user.get_fav_songlist(euin, page=page, num=100),
            "收藏歌单", "playlists"))
        index = [qq_playlist_row(v, owned=True, uid=uid) for v in created_items]
        index += [qq_playlist_row(v, owned=False, uid=uid) for v in fav_items]
        seen = set()
        deduplicated = []
        for item in index:
            if not item["id"] or item["dirid"] == 201 or item["id"] in seen:
                continue
            seen.add(item["id"])
            deduplicated.append(item)
        index = deduplicated
        self.notify(f"✓ 自建歌单：{sum(v['created_by_user'] for v in index)}；收藏歌单：{sum(v['subscribed'] for v in index)}")
        playlists = []
        for n, item in enumerate(index, 1):
            try:
                tracks = await self._cache(cache / "playlists" / f"{safe_name(item['id'])}.json",
                                           lambda item=item: self._tracks(item))
                playlists.append({**item, "tracks": tracks})
            except ApiError as exc:
                self.issues.append(f"歌单《{item['name']}》无法读取：{exc}")
            if n % 10 == 0 or n == len(index):
                self.notify(f"歌单进度：{n}/{len(index)}")
        self.notify("[3/4] 整理数据……")
        public_profile = {"userId": uid, "nickname": profile["nickname"], "avatar": profile.get("avatar") or ""}
        data = build_data(public_profile, liked, playlists, [], self.issues,
                          expected_liked=liked_expected, expected_playlists=len(index),
                          provider="qq_music", capabilities=self.capabilities)
        data["data_availability"] = {"play_history": {"available": False,
            "reason": "QQ Music currently does not provide a verified reliable play history endpoint."}}
        self.notify("[4/4] 写入 AI 文件……")
        write_reports(folder, data)
        self.notify(f"数据检查：我喜欢 {len(liked)}/{liked_expected}；歌单 {len(playlists)}/{len(index)}；"
                    f"歌曲位置 {data['statistics']['playlist_song_positions']}；问题 {len(self.issues)} 项")
        return folder, data

    async def logout(self):
        try:
            await self.client.close()
        finally:
            self.client.credential = None
