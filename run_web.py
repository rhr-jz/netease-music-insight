"""Standalone Local Web entry point; the desktop app can launch it too."""
from netease_music_insight.web.app import main


if __name__ == "__main__":
    raise SystemExit(main())
