# NetEase Music Insight

Export your NetEase Cloud Music listening data and turn it into an AI-ready personal music profile.

On Windows 10/11, download the EXE from [Releases](https://github.com/rhr-jz/netease-music-insight/releases), double-click it, and scan the QR code with the NetEase Cloud Music app. Alternatively, install Python 3.10+, download this repository, and double-click `一键运行.bat`. The first run downloads local dependencies; Git is not required.

The tool exports liked songs, accessible playlists and tracks, and the playback records currently available from NetEase. It writes `output/<nickname>_<uid>/music_for_ai.json`, `music_summary.md`, and `AI_ANALYSIS_PROMPT.md`. Upload the JSON to an AI assistant and paste the prompt to explore your music preferences.

**Playback records are limited by what NetEase currently returns; they are not a complete lifetime listening history.** The exporter records inaccessible playlists and other gaps in `export_meta.issues`.

Your music data stays on your computer by default. QR credentials live only in memory during the session. The local API wrapper is [TH911/NeteaseCloudMusicApi](https://github.com/TH911/NeteaseCloudMusicApi) (MIT), bound to `127.0.0.1`. This independent project uses unofficial interfaces that can change. See [privacy](PRIVACY.md), [data format](docs/DATA_FORMAT.md), and [FAQ](docs/FAQ.md).
