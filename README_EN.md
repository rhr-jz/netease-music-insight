# Music Insight

Export your NetEase Cloud Music or QQ Music account metadata and turn it into an AI-ready personal music profile.

On Windows 10/11, download the portable ZIP from [Releases](https://github.com/rhr-jz/netease-music-insight/releases), extract it, run the EXE, select a platform, and scan its QR code. Alternatively, install Python 3.10+, download this repository, and double-click `一键运行.bat`. If security software reports a threat, do not bypass the block; see [download security](SECURITY.md).

The tool exports liked songs and accessible playlists and tracks from either platform. It also exports playback records currently available from NetEase. It writes `music_for_ai.json`, `music_summary.md`, and `AI_ANALYSIS_PROMPT.md`. NetEase keeps its original `output/<nickname>_<uid>/` path; QQ uses `output/qq_music/<nickname>_<uid>/`. A joint profile is written to `output/combined/` when both platforms succeed.

**NetEase playback records are limited by what its service returns; QQ playback history has no verified reliable endpoint and is marked unavailable.** Collection and playlist timestamps are included only when the API actually returns a usable value. QQ's favorite-playlist order time is labeled separately because it may differ from the original subscription date. The exporter records inaccessible playlists and other gaps in `export_meta.issues`.

Your music data stays on your computer by default. QR credentials live only in memory during the session. This independent project uses unofficial interfaces that can change. QQ support uses [QQMusicApi](https://github.com/L-1124/QQMusicApi) (GPL-3.0-or-later); see [licenses](THIRD_PARTY_LICENSES.md), [privacy](PRIVACY.md), [data format](docs/DATA_FORMAT.md), and [FAQ](docs/FAQ.md).
