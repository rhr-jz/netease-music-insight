"""Online presentation adapter: shared Core and progress, isolated results."""
import logging
import secrets
import shutil
import time
import copy
from pathlib import Path
from threading import Event, Thread

from ..auth import LoginBack
from ..desktop.bridge import DesktopBridge, PROVIDERS
from ..desktop.library import dashboard_data, topic_cards
from ..errors import ExportCancelled
from ..events import MusicEvent
from ..service import CancellationToken, MusicInsightService
from .provider_runtime import prepared_context

LOG = logging.getLogger("music_insight.online")


class OnlineBridge(DesktopBridge):
    def __init__(self, storage, jobs, settings, service_factory=None, clock=time.monotonic):
        self._storage, self._jobs, self._config, self._clock = storage, jobs, settings, clock
        self._revoked = False
        self._datasets = {}
        self._job_history = {}
        self._job = None
        self._finished_at = None
        factory = service_factory or (lambda *a, **kw: MusicInsightService(
            *a, api_context=prepared_context(settings.netease_api_dir, kw.get("cancellation")), **kw))
        super().__init__(storage.root, service_factory=factory)
        self._state["mode"] = "online"
        self._state["retention"] = {"session_ttl": settings.session_ttl, "result_ttl": settings.result_ttl}
        self._state["settings"] = {"theme": "system", "output_dir": "会话临时目录"}

    def _restore_library(self):
        # Never discover files from any other user's directory, or prior process.
        self._data = None

    def _save_settings(self):
        pass

    def _change(self, **values):
        with self._lock:
            if not self._revoked:
                super()._change(**values)

    def snapshot(self, since=-1):
        with self._lock:
            if self._revoked:
                return {"revision": self._revision, "expired": True}
            result = super().snapshot(since)
            if "state" in result:
                result["state"]["job"] = dict(self._job) if self._job else None
            return result

    def start(self, provider, fresh=False):
        if provider not in PROVIDERS:
            return {"ok": False, "message": "请选择音乐平台。"}
        with self._lock:
            if self._revoked or self._state["busy"]:
                return {"ok": False, "message": "请先完成或取消当前任务。"}
            if not self._jobs.acquire():
                return {"ok": False, "message": "服务器正在整理其他音乐，请稍后重试。"}
            job_id = secrets.token_urlsafe(18)
            self._token, self._begin, self._refresh = CancellationToken(), Event(), Event()
            self._job = {"id": job_id, "status": "pending", "provider": provider, "failures": []}
            self._job_history[job_id] = self._job
            if len(self._job_history) > 16:
                self._job_history.pop(next(iter(self._job_history)))
            self._state.update(view="login", busy=True, selected=provider, qr=None,
                               provider=None, nickname="", login_status="正在生成二维码…",
                               message="", toast="", error=None,
                               progress={"liked": None, "playlists": None, "tracks_current": 0,
                                         "tracks_total": 0, "history": None, "phase": "",
                                         "page_current": 0, "page_total": 0})
            self._revision += 1
            root = self._storage.root / "jobs" / job_id
            root.mkdir(parents=True)
            self._thread = Thread(target=self._work, args=(provider, bool(fresh), root),
                                  daemon=True, name="music-insight-online-job")
            self._thread.start()
            return {"ok": True, "job_id": job_id}

    def _on_event(self, event):
        self._token.check()
        if self._revoked:
            raise ExportCancelled()
        with self._lock:
            if event.kind == "login_started":
                self._job["status"] = "login"
                self._state["progress"] = {"liked": None, "playlists": None,
                    "tracks_current": 0, "tracks_total": 0, "history": None, "phase": "",
                    "page_current": 0, "page_total": 0}
            elif event.kind == "export_started":
                self._job["status"] = "syncing"
            elif event.kind == "statistics_done":
                self._job["status"] = "processing"
            elif event.kind == "track_pages_progress":
                self._state["progress"].update(page_current=event.current or 0,
                    page_total=event.total or 0, phase="正在读取当前歌单的歌曲…")
            elif event.kind == "status" and "分页" in event.message:
                import re
                numbers = re.search(r"(\d+)/(\d+)", event.message)
                if numbers:
                    self._state["progress"].update(page_current=int(numbers[1]), page_total=int(numbers[2]))
            # Free-form exceptions, filesystem paths and QR URLs never reach UI.
            # Only count notices consumed by the shared view are forwarded.
            # Failure messages may contain upstream credentials or private URLs.
            message = event.message if event.kind in {"liked_songs_done", "playlists_progress", "history_progress"} else ""
            safe = MusicEvent(event.kind, event.provider, message, event.current, event.total,
                              details={"nickname": event.details.get("nickname", ""),
                                       **{key: event.details[key] for key in ("liked_songs", "playlists", "unique_songs") if key in event.details}})
        super()._on_event(safe)

    def _set_result(self, folder, data, *, view=None, toast=""):
        self._token.check()
        provider = data["export_meta"]["provider"]
        files = self._storage.publish(provider, folder)
        with self._lock:
            self._token.check()
            if provider != "combined" and "combined" in self._datasets:
                self._datasets.pop("combined")
                self._storage.unpublish("combined")
            self._datasets[provider] = {"data": data, "files": files, "generation": secrets.token_urlsafe(12)}
            self._select(provider, view=view, toast=toast)

    def _select(self, provider, *, view=None, toast=""):
        record = self._datasets[provider]
        data = record["data"]
        combined = provider == "combined"
        self._data = data
        self._state.update(dashboard=dashboard_data(data, combined=combined),
            topics=[card for card in topic_cards(data, combined=combined) if card["available"]],
            sources=[{"id": key, "label": {"netease": "网易云音乐", "qq_music": "QQ 音乐", "combined": "两个平台"}[key],
                      "updated_at": value["data"]["export_meta"]["exported_at"]} for key, value in self._datasets.items()],
            source_id=provider, result_folder=record["generation"], files=record["files"],
            data_filename="music_for_ai_combined.json" if combined else "music_for_ai.json", qr=None,
            message="你的音乐数据已经准备好了。", toast=toast)
        if view:
            self._state["view"] = view
        self._revision += 1

    def select_source(self, source_id):
        with self._lock:
            if self._state["busy"] or source_id not in self._datasets:
                return {"ok": False, "message": "请先完成任务，或选择当前会话的数据。"}
            self._select(source_id, view="music")
            return {"ok": True}

    def _work(self, selected, fresh, root):
        try:
            service = self._service_factory(root, fresh=fresh, output_dir=root / "output",
                emit=self._on_event, present_qr=self._present_qr, on_qr_expired=self._expired,
                cancellation=self._token)
            results = {}
            for provider in (("netease", "qq") if selected == "all" else (selected,)):
                self._token.check()
                try:
                    folder, data = service.export_provider(provider)
                    self._set_result(folder, data)
                    results[provider] = (folder, data)
                except (ExportCancelled, LoginBack):
                    raise
                except Exception as exc:
                    LOG.warning("job stage=provider_failed provider=%s error_type=%s", provider, type(exc).__name__)
                    self._job["failures"].append({"provider": provider, "code": getattr(exc, "code", "provider_unavailable")})
                    if selected != "all":
                        raise
            if len(results) == 2:
                folder, data = service.combine(results["netease"][1], results["qq"][1])
                self._set_result(folder, data)
            self._token.check()
            if not results:
                raise RuntimeError("No provider result")
            partial = bool(self._job["failures"]) or any(value[1]["export_meta"]["status"] == "partial" for value in results.values())
            self._job["status"] = "partial" if partial else "completed"
            self._finished_at = self._clock()
            self._change(view="music", busy=False, qr=None,
                         toast="整理完成；部分数据不可用，请查看数据覆盖说明。" if partial else "整理完成。")
        except (ExportCancelled, LoginBack):
            self._job["status"] = "cancelled"
            self._change(view="platforms", busy=False, qr=None, nickname="", message="", toast="已取消，当前会话中已完成的结果仍可查看。")
        except Exception as exc:
            LOG.warning("job stage=failed error_type=%s", type(exc).__name__)
            self._job["status"] = "failed"
            self._change(view="error", busy=False, qr=None,
                error={"title": "这次连接没有完成", "body": "音乐平台可能暂时不可用，请检查二维码并稍后重试。",
                       "detail": "错误类别：" + getattr(exc, "code", "provider_unavailable")}, message="")
        finally:
            # Provider finally blocks discard credentials before leaving the worker.
            if self._finished_at is None and self._datasets:
                self._finished_at = self._clock()
            self._jobs.release()
            if self._revoked:
                self._storage.close()

    def get_job(self, job_id):
        with self._lock:
            record = self._job_history.get(job_id)
            return copy.deepcopy(record) if record else None

    def cancel(self):
        result = super().cancel()
        if result.get("ok"):
            self._change(message="正在安全取消整理…")
        return result

    def set_theme(self, theme):
        if theme not in {"dark", "light", "system"}:
            return {"ok": False}
        with self._lock:
            self._state["settings"]["theme"] = theme
            self._revision += 1
        return {"ok": True}

    def clear_cache(self):
        with self._lock:
            if self._state["busy"]:
                return {"ok": False, "message": "请先取消当前任务。"}
            for path in self._storage.root.glob("jobs/*/.cache"):
                if path.resolve().is_relative_to(self._storage.root) and not path.is_symlink():
                    shutil.rmtree(path)
            self._change(toast="当前会话的阶段缓存已清除。")
            return {"ok": True}

    def dispose(self):
        with self._lock:
            self._revoked = True
            if self._token:
                self._token.cancel()
            self._begin.set()
            self._refresh.set()
            self._storage.revoke()
            self._data = None
            self._datasets.clear()
            self._state.update(qr=None, nickname="", dashboard=None, files=[],
                               topics=[], sources=[], result_folder=None, error=None,
                               message="", toast="", busy=False)
            thread = self._thread
        if not thread or not thread.is_alive():
            self._storage.close()
