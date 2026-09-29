# Music Insight 2.0.0

Music Insight 从命令行数据导出工具升级为 Windows 图形化应用，同时保留 CLI。

- 应用内连接网易云音乐、QQ 音乐或两个平台；扫码二维码直接显示在窗口中，登录与导出进度持续更新，可取消任务。
- “我的音乐”展示已导出数据的事实统计、常见歌手与专辑、歌单规模、数据来源和更新时间，支持本地搜索与离线恢复。
- “AI 分析”提供 12 个单平台方向和 1 个跨平台方向；完整 Prompt 可直接查看、复制，同时继续写入文件。
- 新增隐私优先的 Local Web：默认只监听 `127.0.0.1` 随机端口，从桌面设置打开或源码运行，复用相同 Core 与界面。
- 重写 README，加入匿名产品截图、Windows 快速开始、Local Web 和隐私说明。

Windows 发布包仍是完整目录 ZIP，解压后运行 `MusicInsight.exe`，无需安装 Python；需要 Microsoft Edge WebView2 Runtime。网易云与 QQ 音乐数据获取依赖平台当前可用接口；网易云播放历史可能不完整，QQ 音乐完整播放历史不可用。遇到安全软件拦截时请阅读 [下载与安全说明](https://github.com/rhr-jz/netease-music-insight/blob/main/SECURITY.md)，不要关闭防护。
