"""Same-origin request boundary, bounded bodies, and in-memory rate limits."""
import hashlib
import hmac
import json
import time
import secrets
from collections import OrderedDict, deque
from threading import Lock
from urllib.parse import urlsplit


class RateLimiter:
    def __init__(self, secret, clock=time.monotonic, max_keys=10000):
        self.secret, self.clock, self.max_keys = secret.encode(), clock, max_keys
        self._lock = Lock()
        self._buckets = OrderedDict()

    def identity(self, address):
        return hmac.new(self.secret, address.encode(), hashlib.sha256).hexdigest()

    def allow(self, key, limit, window=60):
        with self._lock:
            now = self.clock()
            bucket = self._buckets.setdefault(key, deque())
            while bucket and bucket[0] <= now - window:
                bucket.popleft()
            self._buckets.move_to_end(key)
            if len(self._buckets) > self.max_keys:
                self._buckets.popitem(last=False)
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


class SecurityMiddleware:
    def __init__(self, app, settings):
        self.app, self.settings = app, settings
        self.host = urlsplit(settings.public_url).netloc.lower()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        nonce = secrets.token_urlsafe(24)
        scope.setdefault("state", {})["style_nonce"] = nonce
        async def secured_send(message):
            if message["type"] == "http.response.start":
                message["headers"] += [(b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"), (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"), (b"cross-origin-resource-policy", b"same-origin"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    (b"content-security-policy", ("default-src 'none'; script-src 'self'; style-src 'self' 'nonce-" + nonce + "'; img-src 'self' data:; connect-src 'self'; font-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'; object-src 'none'").encode())]
                if self.settings.secure:
                    message["headers"].append((b"strict-transport-security", b"max-age=31536000"))
            await send(message)
        async def denied(status, message):
            body = json.dumps({"ok": False, "message": message}, ensure_ascii=False).encode()
            await secured_send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"application/json; charset=utf-8")]})
            await secured_send({"type": "http.response.body", "body": body})
        if headers.get("host", "").lower() != self.host:
            return await denied(403, "网页地址不匹配。")
        path, method = scope["path"], scope["method"]
        if path.startswith("/api/"):
            origin = headers.get("origin")
            if origin and origin != self.settings.public_url:
                return await denied(403, "请从本网站发起请求。")
            if headers.get("sec-fetch-site") == "cross-site":
                return await denied(403, "请从本网站发起请求。")
            # No browser-visible CSRF secret is needed: a fixed custom header,
            # strict Origin validation and SameSite cookie prevent cross-site writes.
            if method not in {"GET", "HEAD"} and (origin != self.settings.public_url or headers.get("x-music-insight-request") != "1"):
                return await denied(403, "请求来源验证失败，请重新打开网页。")
        if method not in {"GET", "HEAD"}:
            try:
                if int(headers.get("content-length", "0")) > 16384:
                    return await denied(413, "请求内容过大。")
            except ValueError:
                return await denied(400, "请求格式无效。")
            messages, length = [], 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                length += len(message.get("body", b""))
                if length > 16384:
                    return await denied(413, "请求内容过大。")
                messages.append(message)
                if not message.get("more_body"):
                    break
            async def replay():
                return messages.pop(0) if messages else await receive()
            return await self.app(scope, replay, secured_send)
        await self.app(scope, receive, secured_send)
