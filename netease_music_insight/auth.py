"""QR login. Credentials are held in memory and never written by this version."""
import time
import os
from pathlib import Path

import qrcode

from .api import ApiError


def qr_login(api, show=lambda text: print(text), qr_path: Path | None = None, poll_seconds=2):
    while True:
        key = (api.get("/login/qr/key", auth=False).get("data") or {}).get("unikey")
        if not key:
            raise ApiError("无法生成登录二维码，请稍后重试。")
        data = api.get("/login/qr/create", {"key": key}, auth=False).get("data") or {}
        url = data.get("qrurl")
        if not url:
            raise ApiError("无法生成登录二维码地址。")
        if qr_path:
            qr_path.parent.mkdir(parents=True, exist_ok=True)
            qrcode.make(url).save(qr_path)
            show(f"二维码图片：{qr_path}")
            if os.name == "nt":
                os.startfile(qr_path)
        qr = qrcode.QRCode(border=2)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
        show("请使用网易云音乐 App 扫码，并在手机上确认。")
        prior = None
        for _ in range(100):
            time.sleep(poll_seconds)
            result = api.get("/login/qr/check", {"key": key, "noCookie": "true"}, auth=False)
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
        input("按 Enter 刷新二维码，或按 Ctrl+C 退出：")
