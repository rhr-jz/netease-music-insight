"""QR login with presentation and expiry decisions supplied by the caller."""
import time
from pathlib import Path

import qrcode

from .api import ApiError


class LoginBack(Exception):
    """The user chose to return to platform selection during QR login."""


def qr_login(api, show, qr_path: Path | None = None, poll_seconds=2,
             present_qr=None, on_expired=None, check_cancel=None):
    while True:
        if check_cancel:
            check_cancel()
        key = (api.get("/login/qr/key", auth=False).get("data") or {}).get("unikey")
        if not key:
            raise ApiError("无法生成登录二维码，请稍后重试。")
        data = api.get("/login/qr/create", {"key": key}, auth=False).get("data") or {}
        url = data.get("qrurl")
        if not url:
            raise ApiError("无法生成登录二维码地址。")
        opened_image = False
        if qr_path:
            qr_path.parent.mkdir(parents=True, exist_ok=True)
            qrcode.make(url).save(qr_path)
            opened_image = bool(present_qr and present_qr(qr_path, url))
            if opened_image:
                show(f"二维码图片：{qr_path}")
            else:
                show(f"图片窗口未能打开，请手动打开二维码图片：{qr_path}")
        show("请使用网易云音乐 App 扫码，并在手机上确认。")
        prior = None
        for _ in range(100):
            if check_cancel:
                check_cancel()
            time.sleep(poll_seconds)
            result = api.get("/login/qr/check", {"key": key, "noCookie": "true"}, auth=False)
            if check_cancel:
                check_cancel()
            code = result.get("code")
            if code != prior:
                if code == 801:
                    show("等待扫码……")
                elif code == 802:
                    show("已扫码，等待手机确认……")
                prior = code
            if code == 803:
                cookie = result.get("cookie")
                if not cookie:
                    cookie = api.get("/login/qr/check", {"key": key}, auth=False).get("cookie")
                if not cookie:
                    raise ApiError("扫码成功，但未收到登录凭据。请重试。")
                api.cookie = cookie
                show("登录成功。")
                return api.profile()
            if code == 800:
                break
        show("二维码已过期。")
        if on_expired is not None and not on_expired():
            raise LoginBack()
