"""Small client for the existing, locally hosted NetEase API wrapper."""
import time

import requests


class ApiError(RuntimeError):
    pass


class LoginExpired(ApiError):
    pass


class MusicApi:
    def __init__(self, base_url: str, cookie: str = "", interval: float = 0.25):
        self.base_url = base_url.rstrip("/")
        self.cookie = cookie
        self.interval = interval
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "NetEaseMusicInsight/1.0"})
        self._last = 0.0

    def get(self, path: str, params=None, *, auth: bool = True, timeout: int = 30):
        values = dict(params or {})
        if auth and self.cookie:
            values["cookie"] = self.cookie
        values["timestamp"] = int(time.time() * 1000)
        for attempt in range(3):
            delay = self.interval - (time.monotonic() - self._last)
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()
            try:
                response = self.session.get(self.base_url + path, params=values, timeout=timeout)
                response.raise_for_status()
                data = response.json()
            except (requests.RequestException, ValueError) as exc:
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise ApiError("网络或本地接口请求失败，请检查连接后重试。") from exc
            if not isinstance(data, dict):
                raise ApiError("接口返回了无法识别的数据。")
            code = data.get("code")
            if code in (301, 302):
                raise LoginExpired("登录已过期，请重新扫码。")
            if code in (500, 502, 503) and attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            if code not in (None, 200, 800, 801, 802, 803):
                raise ApiError(f"网易云接口暂时不可用（代码 {code}）。")
            return data
        raise ApiError("接口请求失败。")

    def profile(self):
        data = self.get("/user/account")
        profile = data.get("profile")
        if not isinstance(profile, dict) or not profile.get("userId"):
            raise LoginExpired("无法读取账号信息，请重新扫码。")
        return profile
