"""Thread-safe pywebview bridge; no account credentials enter JavaScript."""
import base64
import copy
import logging
import re
import shutil
from pathlib import Path
from threading import Event, RLock, Thread

from .. import __version__
from ..auth import LoginBack
from ..diagnostics import redact_text
from ..errors import ExportCancelled, MusicInsightError
from ..guidance import TOPICS, prompt_for
from ..platform_utils import open_path
from ..service import CancellationToken, MusicInsightService
from ..utils import atomic_json, read_json
from .clipboard import copy_text
from .library import (dashboard_data, discover_exports, file_entries,
                      read_export, source_entries, topic_cards)


PROVIDERS = {"netease": "网易云音乐", "qq": "QQ 音乐", "all": "两个平台"}
def _friendly_error(exc, provider):
    code = getattr(exc, "code", "export_failed")
    if code == "network_unavailable":
        return {"title": "连接暂时不顺畅", "body": f"暂时无法连接{PROVIDERS.get(provider, '音乐平台')}。请检查网络和代理设置，然后重试。",
                "detail": redact_text(exc)}
    if code == "login_failed":
        return {"title": "登录没有完成", "body": "请检查二维码是否过期，并用对应音乐 App 扫描、在手机上确认。",
                "detail": redact_text(exc)}
    if code == "provider_unavailable":
        return {"title": "运行组件尚未准备好", "body": "请检查网络、磁盘空间和文件夹写入权限，然后重试。",
                "detail": redact_text(exc)}
    return {"title": "这次整理没有完成", "body": "音乐平台可能暂时不可用。请稍后重试；已有缓存会保留。",
            "detail": redact_text(exc)}


class DesktopBridge:
    def __init__(self, root: Path, *, service_factory=MusicInsightService):
        self._root = Path(root).resolve()
        self._service_factory = service_factory
        self._window = None
        self._lock = RLock()
        self._revision = 0
        self._token = None
        self._thread = None
        self._begin = Event()
        self._refresh = Event()
        self._data = None
        self._records = []
        self._settings_file = self._root / ".state" / "desktop.json"
        saved = read_json(self._settings_file) or {}
        output_dir = saved.get("output_dir") if isinstance(saved, dict) else None
        theme = saved.get("theme") if isinstance(saved, dict) else None
        self._state = {
            "view": "home", "busy": False, "selected": None,
            "provider": None, "provider_name": "", "nickname": "",
            "qr": None, "login_status": "等待扫码", "message": "",
            "progress": {"liked": None, "playlists": None, "tracks_current": 0,
                         "tracks_total": 0, "history": None, "phase": ""},
            "dashboard": None, "files": [], "result_folder": None,
            "sources": [], "source_id": None, "topics": [],
            "data_filename": None,
            "error": None, "toast": "", "version": __version__,
            "settings": {"output_dir": str(Path(output_dir).expanduser()) if output_dir else str(self._root / "output"),
                         "theme": theme if theme in {"dark", "light"} else "dark"},
        }
        self._restore_library()

    def _change(self, **values):
        with self._lock:
            self._state.update(values)
            self._revision += 1

    def snapshot(self, since=-1):
        with self._lock:
            if since == self._revision:
                return {"revision": self._revision}
            return {"revision": self._revision, "state": copy.deepcopy(self._state)}

    def _set_result(self, folder, data, *, view=None, toast=""):
        folder = Path(folder)
        combined = (data.get("export_meta") or {}).get("provider") == "combined"
        # Fake and older combined exports can still be identified by their shape.
        combined = combined or "platforms" in data
        dashboard = dashboard_data(data, combined=combined)
        topics = topic_cards(data, combined=combined)
        records = discover_exports(self._state["settings"]["output_dir"])
        source_id = next((record["id"] for record in records
                          if record["path"].parent.resolve() == folder.resolve()), None)
        with self._lock:
            self._data = data
            self._records = records
            self._state.update(
                dashboard=dashboard, topics=topics, sources=source_entries(records),
                source_id=source_id, result_folder=str(folder),
                data_filename=("music_for_ai_combined.json" if combined else "music_for_ai.json"),
                files=file_entries(folder, combined), qr=None, busy=False,
                message="你的音乐数据已经准备好了。", toast=toast,
            )
            if view:
                self._state["view"] = view
            self._revision += 1

    def _restore_library(self):
        records = discover_exports(self._state["settings"]["output_dir"])
        for record in records:
            data = read_export(record)
            if data is None:
                continue
            try:
                self._set_result(record["path"].parent, data)
                return
            except (KeyError, TypeError, ValueError):
                logging.exception("invalid saved music export")
        with self._lock:
            self._data = None
            self._records = records
            self._state.update(dashboard=None, topics=[], files=[], result_folder=None,
                               sources=source_entries(records), source_id=None,
                               data_filename=None)
            self._revision += 1

    def select_source(self, source_id):
        with self._lock:
            if self._state["busy"]:
                return {"ok": False, "message": "请先完成当前任务。"}
            record = next((item for item in self._records if item["id"] == source_id), None)
        if record is None:
            return {"ok": False, "message": "没有找到这份本地数据。"}
        data = read_export(record)
        if data is None:
            return {"ok": False, "message": "这份数据文件无法读取，请重新整理音乐。"}
        try:
            self._set_result(record["path"].parent, data, view="music")
        except (KeyError, TypeError, ValueError):
            logging.exception("invalid selected music export")
            return {"ok": False, "message": "这份数据文件格式不完整。"}
        return {"ok": True}

    def get_topic(self, number):
        with self._lock:
            data = self._data
            cards = self._state["topics"]
            filename = self._state["data_filename"]
        if data is None:
            return {"ok": False, "message": "请先整理或选择一份音乐数据。"}
        card = next((item for item in cards if item["number"] == number), None)
        topic = next((item for item in TOPICS if item.number == number), None)
        if card is None or topic is None:
            return {"ok": False, "message": "没有找到这个分析方向。"}
        return {"ok": True, "topic": {**card, "prompt": prompt_for(
            topic, combined=filename == "music_for_ai_combined.json", data=data),
            "filename": filename}}

    def copy_prompt(self, number):
        result = self.get_topic(number)
        if not result["ok"]:
            return result
        try:
            copy_text(result["topic"]["prompt"])
        except (OSError, ValueError):
            logging.exception("desktop prompt clipboard failed")
            return {"ok": False, "message": "复制失败，请稍后重试；也可以手动选择上方文字。"}
        return {"ok": True, "message": "✓ 已复制"}

    def search_catalog(self, query):
        with self._lock:
            data = self._data
        if data is None or not isinstance(query, str):
            return {"ok": True, "results": []}
        needle = query.strip().casefold()[:80]
        if not needle:
            return {"ok": True, "results": []}
        if "platforms" in data:
            songs = (group["sources"][0] for group in data.get("matched_catalog", [])
                     if group.get("sources"))
        else:
            songs = iter(data.get("song_catalog", []))
        results = []
        for song in songs:
            name = str(song.get("name") or "")
            artists = str(song.get("artists") or "")
            album = str(song.get("album") or "")
            if needle in f"{name} {artists} {album}".casefold():
                results.append({"name": name, "artists": artists, "album": album})
                if len(results) == 30:
                    break
        return {"ok": True, "results": results}

    def navigate(self, view):
        if view not in {"home", "platforms", "music", "ai", "export", "settings"}:
            return {"ok": False}
        with self._lock:
            if self._state["busy"]:
                return {"ok": False, "message": "请先完成或取消当前任务。"}
        self._change(view=view, toast="")
        return {"ok": True}

    def start(self, provider, fresh=False):
        if provider not in PROVIDERS:
            return {"ok": False, "message": "请选择音乐平台。"}
        with self._lock:
            if self._state["busy"]:
                return {"ok": False, "message": "已有任务正在进行。"}
            output_dir = Path(self._state["settings"]["output_dir"])
            self._token = CancellationToken()
            self._begin = Event()
            self._refresh = Event()
            self._state.update({"view": "login", "busy": True, "selected": provider,
                                "provider": None, "provider_name": "", "nickname": "",
                                "qr": None, "login_status": "正在准备登录…", "message": "",
                                "error": None, "toast": "",
                                "progress": {"liked": None, "playlists": None,
                                             "tracks_current": 0, "tracks_total": 0,
                                             "history": None, "phase": ""}})
            self._revision += 1
            self._thread = Thread(target=self._work, args=(provider, bool(fresh), output_dir),
                                  name="music-insight-export", daemon=True)
            self._thread.start()
        return {"ok": True}

    def begin_export(self):
        with self._lock:
            if not self._state["busy"] or self._state["view"] != "connected":
                return {"ok": False}
        self._begin.set()
        self._change(view="progress", message="正在整理你的音乐世界…")
        return {"ok": True}

    def refresh_qr(self):
        with self._lock:
            if not self._state["busy"] or self._state["login_status"] != "二维码已过期":
                return {"ok": False}
        self._change(qr=None, login_status="正在生成新二维码…")
        self._refresh.set()
        return {"ok": True}

    def cancel(self):
        with self._lock:
            if not self._state["busy"]:
                return {"ok": False}
            token = self._token
        token.cancel()
        self._begin.set()
        self._refresh.set()
        self._change(message="正在取消；已获取的缓存会保留。")
        return {"ok": True}

    def _wait_for(self, signal):
        while not signal.wait(0.15):
            self._token.check()
        self._token.check()

    def _present_qr(self, provider, path, _url=None):
        self._token.check()
        image = Path(path).read_bytes()
        qr = "data:image/png;base64," + base64.b64encode(image).decode("ascii")
        self._change(qr=qr, login_status="等待扫码")
        return True

    def _expired(self, provider):
        self._refresh.clear()
        self._change(qr=None, login_status="二维码已过期")
        self._wait_for(self._refresh)
        return True

    def _on_event(self, event):
        provider = event.provider
        with self._lock:
            state = self._state
            progress = state["progress"]
            kind = event.kind
            if kind == "login_started":
                state.update(view="login", provider=provider,
                             provider_name=PROVIDERS.get(provider, provider), qr=None,
                             login_status="正在准备登录…", message="")
            elif kind == "login_qr_ready":
                state.update(view="login", qr=None, login_status="等待扫码")
            elif kind == "login_waiting":
                state["login_status"] = "等待扫码"
            elif kind == "login_scanned":
                state["login_status"] = "已扫码，请在手机确认"
            elif kind == "login_confirming":
                state["login_status"] = "手机已确认，正在登录…"
            elif kind == "login_qr_expired":
                state["login_status"] = "二维码已过期"
            elif kind == "login_success":
                state["login_status"] = "登录成功"
            elif kind == "profile_done":
                state.update(view="connected", nickname=event.details.get("nickname") or "音乐用户",
                             login_status="登录成功", qr=None)
            elif kind == "liked_songs_done":
                match = re.search(r"[:：]\s*(\d+)", event.message)
                progress["liked"] = int(match.group(1)) if match else None
                progress["phase"] = "喜欢歌曲已整理"
            elif kind == "playlists_progress":
                numbers = [int(v) for v in re.findall(r"[:：]\s*(\d+)", event.message)]
                if len(numbers) >= 2:
                    progress["playlists"] = sum(numbers[:2])
                progress["phase"] = "正在整理你的歌单…"
            elif kind == "playlist_tracks_progress":
                progress.update(tracks_current=event.current or 0,
                                tracks_total=event.total or 0, phase="正在整理歌单歌曲…")
            elif kind == "history_progress":
                if "✓" in event.message:
                    match = re.search(r"[:：]\s*(\d+)", event.message)
                    progress["history"] = int(match.group(1)) if match else 0
                progress["phase"] = "正在整理可获取的播放记录…"
            elif kind == "statistics_done" and provider != "combined":
                progress["liked"] = event.details.get("liked_songs", progress["liked"])
                progress["playlists"] = event.details.get("playlists", progress["playlists"])
                progress["phase"] = "正在整理适合 AI 阅读的数据…"
            elif kind == "export_finished":
                progress["phase"] = "数据已准备好"
            elif kind in {"login_failed", "network_unavailable", "provider_unavailable", "export_failed"}:
                state["message"] = "遇到问题，正在整理可读的说明…"
            elif kind == "status":
                if "首次运行" in event.message:
                    state["message"] = "首次使用正在准备运行组件，可能需要几分钟…"
                elif "获取喜欢" in event.message or "获取我喜欢" in event.message:
                    progress["phase"] = "正在整理喜欢的歌曲…"
                elif "获取歌单" in event.message or "获取自建" in event.message:
                    progress["phase"] = "正在整理你的歌单…"
                elif "生成 AI" in event.message or "写入 AI" in event.message:
                    progress["phase"] = "正在整理适合 AI 阅读的数据…"
            if kind == "export_started" and provider == "combined":
                state.update(view="progress", message="正在生成双平台联合音乐画像…")
                progress["phase"] = "正在合并两个平台的数据…"
            self._revision += 1
        if event.kind == "export_started" and provider != "combined":
            if not self._begin.is_set():
                self._wait_for(self._begin)
            self._change(view="progress", message="正在整理你的音乐世界…")

    def _work(self, selected, fresh, output_dir):
        try:
            service = self._service_factory(
                self._root, fresh=fresh, output_dir=output_dir, emit=self._on_event,
                present_qr=self._present_qr, on_qr_expired=self._expired,
                cancellation=self._token)
            providers = ("netease", "qq") if selected == "all" else (selected,)
            results = {}
            for provider in providers:
                results[provider] = service.export_provider(provider)
            if selected == "all":
                folder, data = service.combine(results["netease"][1], results["qq"][1])
            else:
                folder, data = results[selected]
            self._token.check()
            self._set_result(folder, data, view="music", toast="整理完成。")
        except (ExportCancelled, LoginBack):
            self._change(view="platforms", busy=False, qr=None, login_status="",
                         toast="已取消；已有缓存会保留，下次可以继续。", message="")
        except Exception as exc:
            logging.exception("desktop export failed")
            provider = self._state.get("provider") or selected
            self._change(view="error", busy=False, qr=None,
                         error=_friendly_error(exc, provider), message="")

    def open_result_folder(self):
        with self._lock:
            folder = self._state["result_folder"]
        return {"ok": bool(folder and open_path(Path(folder)))}

    def open_logs(self):
        folder = self._root / "logs"
        folder.mkdir(parents=True, exist_ok=True)
        return {"ok": open_path(folder)}

    def start_web(self):
        """Open the local browser UI while sharing this window's Core state."""
        from ..web.server import start_server

        with self._lock:
            server = getattr(self, "_web_server", None)
            if server is None:
                try:
                    server, _thread = start_server(self._root, bridge=self)
                    self._web_server = server
                except Exception:
                    logging.exception("local web startup failed")
                    return {"ok": False, "message": "无法启动本地网页版，请查看日志。"}
            else:
                import webbrowser
                webbrowser.open(server.origin)
        return {"ok": True}

    def set_theme(self, theme):
        if theme not in {"dark", "light"}:
            return {"ok": False}
        with self._lock:
            self._state["settings"]["theme"] = theme
            self._revision += 1
        self._save_settings()
        return {"ok": True}

    def set_output_dir(self, value):
        with self._lock:
            if self._state["busy"]:
                return {"ok": False, "message": "请先完成当前任务。"}
        try:
            path = Path(value).expanduser()
            if not path.is_absolute():
                return {"ok": False, "message": "请输入完整的文件夹路径。"}
            path.mkdir(parents=True, exist_ok=True)
            path = path.resolve()
        except (OSError, TypeError, ValueError) as exc:
            return {"ok": False, "message": f"无法使用该文件夹：{exc}"}
        with self._lock:
            self._state["settings"]["output_dir"] = str(path)
            self._revision += 1
        self._save_settings()
        self._restore_library()
        return {"ok": True}

    def choose_output_dir(self):
        if self._window is None:
            return {"ok": False, "message": "文件夹选择窗口尚未准备好。"}
        import webview
        with self._lock:
            current = self._state["settings"]["output_dir"]
        chosen = self._window.create_file_dialog(webview.FileDialog.FOLDER, directory=current)
        if not chosen:
            return {"ok": False, "cancelled": True}
        return self.set_output_dir(chosen[0])

    def clear_cache(self):
        with self._lock:
            if self._state["busy"]:
                return {"ok": False, "message": "请先完成或取消当前任务。"}
        target = self._root / ".cache"
        try:
            if target.exists():
                shutil.rmtree(target)
        except OSError as exc:
            logging.exception("desktop cache cleanup failed")
            return {"ok": False, "message": f"清除缓存失败：{exc}"}
        self._change(toast="缓存已清除；下次将重新获取数据。")
        return {"ok": True}

    def _save_settings(self):
        with self._lock:
            settings = self._state["settings"].copy()
        atomic_json(self._settings_file, settings)

    def on_closing(self):
        with self._lock:
            busy = self._state["busy"]
        if busy:
            self.cancel()
            self._change(toast="正在安全取消任务，请稍后再次关闭窗口。")
            return False
        return True
