import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from . import __version__
from .api import ApiError
from .bootstrap import SetupError, local_api
from .combined import build_combined, write_combined
from .providers.netease import NetEaseProvider


def app_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _choice():
    print("请选择数据来源：\n[1] 网易云音乐\n[2] QQ 音乐\n[3] 同时导出网易云 + QQ 音乐")
    while True:
        value = input("请输入 1 / 2 / 3：").strip()
        if value in {"1", "2", "3"}:
            return {"1": "netease", "2": "qq", "3": "all"}[value]
        print("请输入 1、2 或 3。")


def _netease(root, fresh):
    print("\n正在准备网易云音乐……")
    with local_api(root) as base:
        provider = NetEaseProvider(base, root, fresh=fresh)
        try:
            return provider.export(provider.login())
        finally:
            provider.logout()


async def _qq(root, fresh):
    from .providers.qqmusic import QQMusicProvider
    print("\n正在准备 QQ 音乐……")
    provider = QQMusicProvider(root, fresh=fresh)
    try:
        profile = await provider.login()
        print(f"✓ 登录成功：{profile['nickname']}（QQ 音乐 ID {profile['userId']}）")
        return await provider.export(profile)
    finally:
        await provider.logout()


def main(argv=None):
    if os.name == "nt":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Music Insight：网易云音乐 / QQ 音乐个人数据导出")
    parser.add_argument("--version", action="version", version=f"Music Insight {__version__}")
    parser.add_argument("--provider", choices=("netease", "qq", "all"), help="选择平台；省略时交互选择")
    parser.add_argument("--fresh", action="store_true", help="重新获取全部数据，不使用最近 24 小时的缓存")
    args = parser.parse_args(argv)
    root = app_root()
    log_dir = root / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(filename=log_dir / "error.log", level=logging.ERROR,
                        format="%(asctime)s %(levelname)s %(message)s")
    print(f"🎧 Music Insight {__version__}\n分析属于你的音乐世界\n")
    results = {}
    try:
        selected = args.provider or _choice()
        for key in (("netease", "qq") if selected == "all" else (selected,)):
            try:
                results[key] = _netease(root, args.fresh) if key == "netease" else asyncio.run(_qq(root, args.fresh))
            except (ApiError, SetupError, OSError, ValueError) as exc:
                logging.error("%s export failed: %s", key, type(exc).__name__)
                print(f"{key} 导出未完成：{exc}")
                if selected != "all":
                    return 1
        if selected == "all" and len(results) == 2:
            answer = input("\n是否生成跨平台联合音乐画像？[Y/n] ").strip().lower()
            if answer not in {"n", "no"}:
                folder = root / "output" / "combined"
                write_combined(folder, build_combined(results["netease"][1], results["qq"][1]))
                print(f"✓ 联合画像：{folder}")
        for key, (folder, data) in results.items():
            print(f"\n✓ {key}：{folder}")
            print("  music_for_ai.json、music_summary.md、AI_ANALYSIS_PROMPT.md")
            if data["export_meta"]["issues"]:
                print(f"  数据问题 {len(data['export_meta']['issues'])} 项，详见 music_summary.md")
        if results:
            print("\n下一步：向 ChatGPT / Claude / Gemini 上传 JSON，并复制对应的 AI 提示词。")
            if os.name == "nt" and len(results) == 1:
                os.startfile(next(iter(results.values()))[0])
        return 0 if len(results) == (2 if selected == "all" else 1) else 1
    except KeyboardInterrupt:
        print("\n已取消。下次运行可继续使用最近 24 小时的缓存。")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
