import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path

from . import __version__
from .api import ApiError, LoginExpired, MusicApi
from .auth import qr_login
from .bootstrap import SetupError, local_api
from .exporter import ExportService
from .platform_utils import open_path


def app_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def main(argv=None):
    if os.name == "nt":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="网易云音乐数据与 AI 提示词一键导出")
    parser.add_argument("--version", action="version", version=f"NetEase Music Insight {__version__}")
    parser.add_argument("--fresh", action="store_true", help="重新获取全部数据，不使用最近 24 小时的缓存")
    args = parser.parse_args(argv)
    root = app_root()
    log_dir = root / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(filename=log_dir / "error.log", level=logging.ERROR,
                        format="%(asctime)s %(levelname)s %(message)s")
    print(f"欢迎使用 NetEase Music Insight {__version__}\n")
    api = None
    try:
        print("[1/5] 检查运行环境……")
        with local_api(root) as base:
            print("✓ 本地组件已就绪\n[2/5] 登录网易云音乐……")
            api = MusicApi(base)
            legacy = root / ".state" / "cookie.txt"
            profile = None
            if legacy.exists():
                try:
                    api.cookie = legacy.read_text(encoding="utf-8").strip()
                    profile = api.profile()
                    print("✓ 已迁移旧版登录状态")
                except (ApiError, OSError):
                    api.cookie = ""
                finally:
                    try:
                        legacy.unlink()
                    except OSError:
                        pass
            if profile is None:
                with tempfile.TemporaryDirectory() as temp:
                    qr_file = Path(temp) / "netease-login-qr.png"
                    profile = qr_login(api, qr_path=qr_file)
            print(f"✓ 登录成功：{profile.get('nickname', '网易云用户')}\n[3/5] 获取音乐数据……")
            folder, data = ExportService(api, root, fresh=args.fresh).run(profile)
        print("\n[4/5] 文件已生成")
        for name in ("music_for_ai.json", "music_summary.md", "AI_ANALYSIS_PROMPT.md"):
            print(f"✓ {name}")
        print(f"\n[5/5] 完成！文件位于：{folder}")
        if data["export_meta"]["issues"]:
            print(f"本次有 {len(data['export_meta']['issues'])} 项数据可能不完整，详情见 music_summary.md。")
        print("下一步：打开 ChatGPT / Claude / Gemini，上传 music_for_ai.json，"
              "再复制 AI_ANALYSIS_PROMPT.md 的内容。")
        open_path(folder)
        return 0
    except KeyboardInterrupt:
        print("\n已取消。下次运行可继续使用最近 24 小时的缓存。")
        return 130
    except (SetupError, ApiError, OSError, ValueError) as exc:
        message = str(exc)
        if api and api.cookie:
            message = message.replace(api.cookie, "[已隐藏]")
        logging.error("%s: %s", type(exc).__name__, message)
        print(f"\n操作未完成：{message}")
        if isinstance(exc, LoginExpired):
            print("请重新运行并扫码登录。")
        else:
            print("请检查网络与文件夹写入权限后重试。已完成的歌单会保留在本地缓存中。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
