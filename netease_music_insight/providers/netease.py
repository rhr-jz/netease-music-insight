"""Existing NetEase flow behind the common provider contract."""
import tempfile
from pathlib import Path

from ..api import ApiError, MusicApi
from ..auth import qr_login
from ..exporter import ExportService
from .base import MusicProvider


class NetEaseProvider(MusicProvider):
    name = "netease"
    capabilities = {"liked_songs": True, "playlists": True,
                    "playlist_tracks": True, "play_history": True}

    def __init__(self, base_url, root: Path, *, fresh=False, notify=print):
        self.api = MusicApi(base_url)
        self.root = root
        self.fresh = fresh
        self.notify = notify

    def login(self):
        legacy = self.root / ".state" / "cookie.txt"
        if legacy.exists():
            try:
                self.api.cookie = legacy.read_text(encoding="utf-8").strip()
                profile = self.api.profile()
                self.notify("✓ 已迁移旧版登录状态")
                return profile
            except (ApiError, OSError):
                self.api.cookie = ""
            finally:
                try:
                    legacy.unlink()
                except OSError:
                    pass
        with tempfile.TemporaryDirectory() as temp:
            return qr_login(self.api, qr_path=Path(temp) / "netease-login-qr.png")

    def export(self, profile):
        return ExportService(self.api, self.root, fresh=self.fresh, notify=self.notify).run(profile)

    def logout(self):
        self.api.cookie = ""
