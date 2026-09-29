"""Windows desktop entry point. The CLI remains available via run.py."""
from netease_music_insight.desktop.app import main


if __name__ == "__main__":
    raise SystemExit(main())
