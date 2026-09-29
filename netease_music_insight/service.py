"""Shared export coordinator; frontends supply events and QR interactions."""
import asyncio
import re
from pathlib import Path
from threading import Event

from .auth import LoginBack
from .bootstrap import SetupError, local_api
from .combined import build_combined, write_combined
from .errors import (ExportCancelled, ExportFailed, LoginFailure,
                     MusicInsightError, NetworkUnavailable, ProviderUnavailable)
from .events import MusicEvent
from .providers.netease import NetEaseProvider


class CancellationToken:
    def __init__(self):
        self._flag = Event()

    def cancel(self):
        self._flag.set()

    def check(self):
        if self._flag.is_set():
            raise ExportCancelled("已取消本次导出。")


def _legacy_event(provider, message):
    """Bridge existing provider notices without changing their data paths."""
    kinds = (("已扫码", "login_scanned"), ("已确认", "login_confirming"),
             ("等待扫码", "login_waiting"), ("二维码已过期", "login_qr_expired"),
             ("歌单进度", "playlist_tracks_progress"),
             ("✓ 喜欢音乐", "liked_songs_done"), ("✓ 我喜欢", "liked_songs_done"),
             ("自建歌单", "playlists_progress"), ("播放记录", "history_progress"))
    kind = next((value for marker, value in kinds if marker in message), "status")
    if "喜欢音乐：" in message and "/" in message:
        kind = "liked_songs_progress"
    numbers = re.search(r"(\d+)\s*/\s*(\d+)", message)
    return MusicEvent(kind, provider, message,
                      int(numbers.group(1)) if numbers else None,
                      int(numbers.group(2)) if numbers else None)


def _failure(exc, phase):
    if isinstance(exc, (ExportCancelled, LoginBack)):
        return exc
    if isinstance(exc, MusicInsightError):
        return exc
    if isinstance(exc, SetupError) or isinstance(exc, ImportError):
        return ProviderUnavailable(str(exc))
    if any(word in str(exc).lower() for word in ("网络", "timeout", "连接", "请求失败", "http")):
        return NetworkUnavailable(str(exc))
    return LoginFailure(str(exc)) if phase == "login" else ExportFailed(str(exc))


class MusicInsightService:
    def __init__(self, root: Path, *, fresh=False, emit=None, present_qr=None,
                 on_qr_expired=None, cancellation=None, output_dir=None):
        self.root = Path(root)
        self.output_dir = Path(output_dir) if output_dir is not None else self.root / "output"
        self.fresh = fresh
        self.emit = emit or (lambda event: None)
        self.present_qr = present_qr
        self.on_qr_expired = on_qr_expired
        self.cancellation = cancellation or CancellationToken()

    def _notice(self, provider, message):
        self.cancellation.check()
        self.emit(_legacy_event(provider, message))

    def _qr(self, provider, path, url=None):
        self.cancellation.check()
        self.emit(MusicEvent("login_qr_ready", provider, path=path))
        return bool(self.present_qr and self.present_qr(provider, path, url))

    def _expired(self, provider):
        self.cancellation.check()
        return True if self.on_qr_expired is None else self.on_qr_expired(provider)

    def export_provider(self, provider):
        if provider not in {"netease", "qq"}:
            raise ProviderUnavailable(f"不支持的音乐平台：{provider}")
        self.cancellation.check()
        self.emit(MusicEvent("login_started", provider))
        phase = "login"
        try:
            if provider == "netease":
                with local_api(self.root, notify=lambda msg: self._notice(provider, msg)) as base:
                    client = NetEaseProvider(
                        base, self.root, fresh=self.fresh,
                        output_dir=self.output_dir,
                        notify=lambda msg: self._notice(provider, msg),
                        present_qr=lambda path, url: self._qr(provider, path, url),
                        on_qr_expired=lambda: self._expired(provider),
                        check_cancel=self.cancellation.check)
                    try:
                        profile = client.login()
                        self.emit(MusicEvent("login_success", provider))
                        self.emit(MusicEvent("profile_done", provider, details={
                            "nickname": profile.get("nickname") or "网易云用户",
                            "avatar": profile.get("avatarUrl") or profile.get("avatar") or ""}))
                        phase = "export"
                        self.emit(MusicEvent("export_started", provider))
                        self.cancellation.check()
                        result = client.export(profile)
                    finally:
                        client.logout()
            else:
                result = asyncio.run(self._export_qq(provider))
            self.cancellation.check()
            folder, data = result
            self.emit(MusicEvent("statistics_done", provider, details={
                "liked_songs": data["statistics"]["liked_song_count"],
                "playlists": data["statistics"]["playlist_count"],
                "unique_songs": data["statistics"]["unique_song_count"]}))
            self.emit(MusicEvent("export_finished", provider, path=folder))
            return result
        except (KeyboardInterrupt, LoginBack):
            raise
        except Exception as exc:
            failure = _failure(exc, phase)
            self.emit(MusicEvent(failure.code, provider, str(failure)))
            if failure is exc:
                raise
            raise failure from exc

    async def _export_qq(self, provider):
        from .providers.qqmusic import QQMusicProvider
        client = QQMusicProvider(
            self.root, fresh=self.fresh,
            output_dir=self.output_dir,
            notify=lambda msg: self._notice(provider, msg),
            present_qr=lambda path: self._qr(provider, path),
            on_qr_expired=lambda: self._expired(provider),
            check_cancel=self.cancellation.check)
        try:
            profile = await client.login()
            self.emit(MusicEvent("login_success", provider))
            self.emit(MusicEvent("profile_done", provider, details={
                "nickname": profile.get("nickname") or "QQ音乐用户",
                "avatar": profile.get("avatar") or ""}))
            self.emit(MusicEvent("export_started", provider))
            self.cancellation.check()
            try:
                return await client.export(profile)
            except Exception as exc:
                failure = _failure(exc, "export")
                if failure is exc:
                    raise
                raise failure from exc
        finally:
            await client.logout()

    def combine(self, netease_data, qq_data):
        self.cancellation.check()
        self.emit(MusicEvent("export_started", "combined"))
        try:
            folder = self.output_dir / "combined"
            self.cancellation.check()
            data = build_combined(netease_data, qq_data)
            write_combined(folder, data)
            self.emit(MusicEvent("statistics_done", "combined", details={
                "unique_songs": data["statistics"]["combined_unique_tracks"]}))
            self.emit(MusicEvent("export_finished", "combined", path=folder))
            return folder, data
        except Exception as exc:
            failure = _failure(exc, "export")
            self.emit(MusicEvent(failure.code, "combined", str(failure)))
            if failure is exc:
                raise
            raise failure from exc
