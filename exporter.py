"""Compatibility entry point for users of the previous version."""
from netease_music_insight.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
