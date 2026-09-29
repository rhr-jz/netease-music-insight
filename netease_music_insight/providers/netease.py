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

    def __init__(self, base_url, root: Path, *, fresh=False, notify=None,
                 present_qr=None, on_qr_expired=None, check_cancel=None,
                 output_dir=None):
        self.api = MusicApi(base_url)
        self.root = root
        self.output_dir = output_dir
        self.fresh = fresh
        self.notify = notify or (lambda message: None)
        self.present_qr = present_qr
        self.on_qr_expired = on_qr_expired
        self.check_cancel = check_cancel

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
            return qr_login(self.api, show=self.notify, qr_path=Path(temp) / "netease-login-qr.png",
                            present_qr=self.present_qr, on_expired=self.on_qr_expired,
                            check_cancel=self.check_cancel)

    def export(self, profile):
        return ExportService(self.api, self.root, fresh=self.fresh, notify=self.notify,
                             output_dir=self.output_dir).run(profile)

    def logout(self):
        self.api.cookie = ""
