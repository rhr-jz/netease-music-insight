"""FastAPI application factory for a single persistent Online Web instance."""
import asyncio
import importlib.util
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from .. import __version__
from ..frontend import ASSETS, document
from .jobs import JobManager
from .provider_runtime import ready
from .security import RateLimiter, SecurityMiddleware
from .sessions import SessionManager
from .settings import Settings


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class JobInput(Input):
    provider: Literal["netease", "qq", "all"]
    fresh: bool = False
    consent: bool


class ActionInput(Input):
    method: Literal["navigate", "begin_export", "refresh_qr", "cancel", "select_source", "set_theme", "clear_cache"]
    args: list = Field(default_factory=list, max_length=1)


class LibraryInput(Input):
    kind: Literal["catalog", "liked", "playlists", "playlist", "history"] = "catalog"
    query: str = Field(default="", max_length=200)
    page: int = Field(default=1, ge=1, le=100000)
    playlist_id: str | None = Field(default=None, max_length=200)


def create_app(settings=None, *, service_factory=None, clock=None):
    settings = settings or Settings.from_env()
    jobs = JobManager(settings.max_active_jobs)
    manager = SessionManager(settings, jobs, service_factory, **({"clock": clock} if clock else {}))
    limiter = RateLimiter(settings.secret, **({"clock": clock} if clock else {}))

    @asynccontextmanager
    async def lifespan(app):
        async def cleanup():
            while True:
                await asyncio.sleep(1)
                await run_in_threadpool(manager.reap)
        task = asyncio.create_task(cleanup())
        try:
            yield
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await run_in_threadpool(manager.close)

    app = FastAPI(title="Music Insight Online", version=__version__, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.sessions, app.state.jobs, app.state.settings = manager, jobs, settings
    app.add_middleware(SecurityMiddleware, settings=settings)

    def rate(request, session=None, category="read", limit=300, ip_limit=1200):
        # Deliberately ignore spoofable X-Forwarded-For. Behind a reverse proxy,
        # the IP bucket may be shared; session limits still isolate consumers.
        address = request.client.host if request.client else "unknown"
        identity = limiter.identity(address)
        if not limiter.allow((identity, category), ip_limit) or (session and not limiter.allow((session.id, category), limit)):
            raise HTTPException(429, "请求较频繁，请稍后重试。")

    def session_for(request, category="read", limit=300, ip_limit=1200):
        session = manager.get(request.cookies.get(settings.cookie_name))
        if not session:
            raise HTTPException(401, "会话已结束，请重新开始。")
        rate(request, session, category, limit, ip_limit)
        return session

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        headers = {"Retry-After": "60"} if exc.status_code == 429 else None
        return JSONResponse({"ok": False, "message": str(exc.detail)}, status_code=exc.status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        # Pydantic's default errors echo input values; never echo private inputs.
        return JSONResponse({"ok": False, "message": "请求格式不正确。"}, status_code=400)

    @app.exception_handler(Exception)
    async def failed(request, exc):
        logging.getLogger("music_insight.online").error("request stage=failed error_type=%s", type(exc).__name__)
        return JSONResponse({"ok": False, "message": "操作暂时无法完成，请稍后重试。"}, status_code=500)

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return document().replace("<head>", '<head><meta name="music-insight-mode" content="online"><meta name="style-nonce" content="' + request.state.style_nonce + '">')

    @app.get("/assets/{name}")
    async def asset(name: str):
        types = {"ui.css": "text/css", "bridge.js": "text/javascript", "library.js": "text/javascript", "app.js": "text/javascript"}
        if name not in types:
            raise HTTPException(404, "文件不存在。")
        return Response((ASSETS / name).read_bytes(), media_type=types[name])

    @app.get("/health")
    @app.get("/api/status")
    async def health():
        return {"status": "ok", "version": __version__,
                "netease_provider": "ready" if ready(settings.netease_api_dir) else "unavailable",
                "qq_provider": "ready" if importlib.util.find_spec("qqmusic_api") else "unavailable"}

    @app.post("/api/session")
    async def create_session(request: Request):
        rate(request, category="session", ip_limit=20)
        existing = manager.get(request.cookies.get(settings.cookie_name))
        try:
            session = existing or await run_in_threadpool(manager.create)
        except RuntimeError:
            raise HTTPException(503, "服务器正在使用中，请稍后再试。") from None
        response = JSONResponse({"ok": True, "expires_at": session.expires_wall})
        response.set_cookie(settings.cookie_name, session.id, max_age=settings.session_ttl,
                            httponly=True, secure=settings.secure, samesite="strict", path="/")
        return response

    @app.get("/api/snapshot")
    async def snapshot(request: Request, since: int = -1):
        session = session_for(request)
        result = await run_in_threadpool(session.bridge.snapshot, since)
        if "state" in result:
            result["state"]["session_expires_at"] = session.expires_wall
        return result

    @app.post("/api/jobs", status_code=202)
    async def start_job(request: Request, payload: JobInput):
        session = session_for(request, "login", 5, 50)
        if not payload.consent:
            raise HTTPException(400, "请先阅读并同意临时会话的隐私说明。")
        result = await run_in_threadpool(session.bridge.start, payload.provider, payload.fresh)
        if not result.get("ok"):
            raise HTTPException(409, result["message"])
        return result

    @app.get("/api/jobs/{job_id}")
    async def job(request: Request, job_id: str):
        session = session_for(request)
        result = session.bridge.get_job(job_id)
        if not result:
            raise HTTPException(404, "任务不存在或已过期。")
        return result

    @app.post("/api/actions")
    async def action(request: Request, payload: ActionInput):
        session = session_for(request, "qr" if payload.method == "refresh_qr" else "action", 10 if payload.method == "refresh_qr" else 120, 100 if payload.method == "refresh_qr" else 600)
        one_arg = {"navigate", "select_source", "set_theme"}
        if ((payload.method in one_arg and (len(payload.args) != 1 or not isinstance(payload.args[0], str) or len(payload.args[0]) > 100)) or
                (payload.method not in one_arg and payload.args)):
            raise HTTPException(400, "请求参数无效。")
        return await run_in_threadpool(getattr(session.bridge, payload.method), *payload.args)

    @app.post("/api/library")
    async def library(request: Request, payload: LibraryInput):
        session = session_for(request, "search", 180, 900)
        return await run_in_threadpool(session.bridge.browse_library, payload.kind, payload.query, payload.page, payload.playlist_id)

    @app.get("/api/comparison")
    async def comparison(request: Request):
        return await run_in_threadpool(session_for(request).bridge.get_comparison)

    @app.get("/api/topics/{number}")
    async def topic(request: Request, number: int):
        return await run_in_threadpool(session_for(request).bridge.get_topic, number)

    @app.get("/api/guide")
    async def guide(request: Request):
        return await run_in_threadpool(session_for(request).bridge.get_guide)

    @app.get("/api/download/{file_id}")
    async def download(request: Request, file_id: str):
        session = session_for(request, "download", 60, 300)
        try:
            body, name, kind = await run_in_threadpool(session.bridge._storage.read, file_id)
        except (OSError, ValueError):
            raise HTTPException(404, "文件不存在或已过期。") from None
        filename = Path(name).name
        return Response(body, media_type=kind,
                        headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(filename)})

    @app.post("/api/logout")
    async def logout(request: Request):
        session = session_for(request, "logout", 10, 100)
        await run_in_threadpool(manager.drop, session.id)
        response = JSONResponse({"ok": True})
        response.delete_cookie(settings.cookie_name, path="/", secure=settings.secure, httponly=True, samesite="strict")
        return response

    @app.get("/api/events")
    async def events(request: Request):
        session = session_for(request, "stream", 20, 100)
        with manager._lock:
            if session.streams >= 2:
                raise HTTPException(429, "请减少同时打开的标签页。")
            session.streams += 1
        async def stream():
            revision = -1
            try:
                while manager.get(session.id) is session and not await request.is_disconnected():
                    update = await run_in_threadpool(session.bridge.snapshot, revision)
                    if "state" in update:
                        update["state"]["session_expires_at"] = session.expires_wall
                        revision = update["revision"]
                        yield "data: " + json.dumps(update, ensure_ascii=False) + "\n\n"
                    else:
                        yield ": keepalive\n\n"
                    await asyncio.sleep(0.5)
                yield 'event: expired\ndata: {}\n\n'
            finally:
                with manager._lock:
                    session.streams -= 1
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    return app
