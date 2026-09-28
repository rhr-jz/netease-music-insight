# 隐私说明

NetEase Music Insight 默认只把音乐数据写在你自己的电脑上。程序不向作者服务器发送账号、Cookie、歌单或听歌记录，不保存密码，也不会自动上传数据给 AI 平台或 GitHub。只有在你主动把 `music_for_ai.json` 上传给 AI 时，该平台才会收到文件；请先阅读该平台的隐私政策。

扫码登录凭据仅保存在本次程序进程的内存中，结束时消失。为了迁移旧版，本程序若发现 `.state/cookie.txt`，会尝试使用一次并删除该文件。后续运行通常需要重新扫码。

本地文件位置：

- `output/用户名_UID/`：导出数据、概要、AI 提示词和基础原始列表。
- `.cache/UID/`：最近 24 小时的阶段性数据，用于中断后继续；运行 `--fresh` 可忽略缓存。缓存文件不会自动上传。
- `api/`、`.runtime/`：首次运行下载的开源接口与 Node.js 本地组件。
- `logs/error.log`：不包含登录凭据的简短错误信息。

本地接口只监听 `127.0.0.1`，程序结束时关闭。该组件会直接与网易云音乐服务通信以完成登录和数据请求。它来自 [TH911/NeteaseCloudMusicApi](https://github.com/TH911/NeteaseCloudMusicApi)，遵循 MIT 许可，不是作者运营的在线服务。

如需清除本工具保留的个人数据，关闭程序后删除 `output/`、`.cache/`、`.state/` 和 `logs/`。旧版 `exports/` 也可能包含私人数据，请自行检查并清理。仓库的 `.gitignore` 默认排除这些路径，但发布前仍应检查 Git 暂存文件。
