import argparse
import logging
import os
import sys
from pathlib import Path

from . import __version__
from .auth import LoginBack
from .service import MusicInsightService
from .ui import ConsoleUI, PLATFORM_NAMES


def app_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _configure_console():
    if os.name == "nt":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")


def _export_selected(selected, args, root, ui, interactive):
    service = MusicInsightService(root, fresh=args.fresh, emit=ui.handle_event,
                                  present_qr=ui.present_qr, on_qr_expired=ui.on_qr_expired)
    results = {}
    keys = ("netease", "qq") if selected == "all" else (selected,)
    for key in keys:
        while True:
            try:
                results[key] = service.export_provider(key)
                ui.data_check(results[key][1])
                break
            except KeyboardInterrupt:
                raise
            except LoginBack:
                return ("home" if interactive else "quit"), results
            except Exception as exc:
                logging.exception("%s export failed", key)
                ui.error(exc)
                if not interactive:
                    break
                action = ui.retry()
                if action == "":
                    continue
                if action == "h":
                    return "home", results
                return "quit", results

    combined_folder = None
    combined_data = None
    if selected == "all" and len(results) == 2:
        try:
            combined_folder, combined_data = service.combine(results["netease"][1], results["qq"][1])
        except Exception as exc:
            logging.exception("combined export failed")
            ui.error(exc)
            combined_folder = combined_data = None

    if results:
        ui.step(4, "完成")
        for key, (folder, data) in results.items():
            ui.result(PLATFORM_NAMES[key], folder, data)
        if combined_folder is not None:
            ui.line("\n两个平台的联合画像也已生成。")
            ui.line(f"  两个平台合计独立歌曲  {combined_data['statistics']['combined_unique_tracks']} 首")
            ui.files(combined_folder, combined=True)
        primary_folder, primary_data = ((combined_folder, combined_data) if combined_folder is not None
                                        else next(iter(results.values())))
        if interactive:
            ui.after_export(primary_folder, primary_data, combined=combined_folder is not None)
        else:
            ui.next_ideas()
            ui.line("打开 AI_ANALYSIS_GUIDE.md，选择一个方向并复制对应提示词。")
    ok = len(results) == len(keys) and (selected != "all" or combined_folder is not None)
    return ("done" if ok else "partial"), results


def main(argv=None):
    _configure_console()
    parser = argparse.ArgumentParser(description="Music Insight：导出网易云音乐 / QQ 音乐个人数据")
    parser.add_argument("--version", action="version", version=f"Music Insight {__version__}")
    parser.add_argument("--provider", choices=("netease", "qq", "all"), help="选择平台；省略时交互选择")
    parser.add_argument("--fresh", action="store_true", help="重新获取全部数据，不使用最近 24 小时的缓存")
    args = parser.parse_args(argv)
    ui = ConsoleUI()
    root = app_root()
    try:
        log_dir = root / "logs"
        log_dir.mkdir(exist_ok=True)
        logging.basicConfig(filename=log_dir / "error.log", level=logging.ERROR,
                            format="%(asctime)s %(levelname)s %(message)s")
        ui.welcome(__version__)
        while True:
            selected = args.provider or ui.choose_provider()
            if selected is None:
                ui.line("已退出。")
                return 0
            status, _ = _export_selected(selected, args, root, ui, interactive=args.provider is None)
            if status == "home" and args.provider is None:
                continue
            if status == "quit":
                return 1
            return 0 if status == "done" else 1
    except KeyboardInterrupt:
        ui.line("\n已取消。下次运行可继续使用最近 24 小时的缓存。")
        return 130
    except EOFError:
        ui.line("\n没有收到输入，已退出。")
        return 1
    except Exception as exc:
        logging.exception("application failed")
        ui.error(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
