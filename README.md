# 🎧 Music Insight

## 听见自己。

**整理网易云音乐 / QQ 音乐的收藏与歌单，用数据和 AI 重新认识自己的音乐审美。**

应用内扫码登录，查看音乐 Dashboard，导出数据，一键复制 AI 分析 Prompt。支持单平台与两平台联合分析。

## ⬇ 下载即用

- **[Windows 下载 · 68.3 MiB](https://github.com/rhr-jz/netease-music-insight/releases/download/portable-v3.0.0-rc.1/MusicInsight-Windows-x64-3.0.0rc1.zip)**
- **[Mac M 系列下载 · 73.6 MiB](https://github.com/rhr-jz/netease-music-insight/releases/download/portable-v3.0.0-rc.1/MusicInsight-macOS-AppleSilicon-3.0.0rc1.zip)**
- **[Mac Intel 下载 · 74.7 MiB](https://github.com/rhr-jz/netease-music-insight/releases/download/portable-v3.0.0-rc.1/MusicInsight-macOS-Intel-3.0.0rc1.zip)**

[全部下载与版本说明](https://github.com/rhr-jz/netease-music-insight/releases/tag/portable-v3.0.0-rc.1) · [快速上手](docs/QUICK_START.md) · [English](README_EN.md)

当前完整运行包为 **3.0 RC1 预发布版**，已包含运行组件，无需安装 Python、Node 或配置 API Key。Windows 10/11 x64；Windows 11 ARM 使用 x64 兼容层；Mac 建议 macOS 14 及以上。Mac 包未 Apple 公证，首次打开可能需要系统安全确认。

## 你可以做什么

- **整理音乐收藏**：喜欢歌曲、自建与收藏歌单、可访问的歌单歌曲和平台提供的播放记录。
- **看见自己的音乐档案**：歌曲、歌手、专辑、歌单统计，搜索歌曲，比较两个平台的音乐收藏。
- **探索音乐审美**：13 个按数据能力显示的 AI 分析方向，包含音乐画像、核心歌手、成长轨迹、音乐地图、听歌计划和跨平台比较。
- **带走自己的数据**：导出 JSON、音乐摘要和 Prompt；本地网页可打包 ZIP，已有档案可离线浏览。

## 三步开始

1. **完整解压**对应系统的 ZIP，双击 `MusicInsight.exe` 或 `MusicInsight.app`。
2. 选择网易云、QQ 或两个平台，用对应音乐 App 扫码确认，再点击“开始整理我的音乐”。
3. 查看“我的音乐”；在“AI 分析”复制 Prompt，把导出的 JSON 和 Prompt 交给你选择的 AI。

支持 ChatGPT、Claude、Gemini 等可上传文件的 AI，**无需 API Key，也不会自动把你的数据发给 AI**。

想在浏览器使用？在“设置”点击“启动 Web 版”，或打开包内的 `Open Local Web` 入口。网页运行在自己的电脑上。

## 看看界面

以下截图使用合成演示数据。

![Music Insight 音乐 Dashboard](assets/screenshots/dashboard.png)

<details>
<summary>展开：首页与 AI 分析中心</summary>

![Music Insight 首页](assets/screenshots/home.png)

![Music Insight AI 分析中心](assets/screenshots/ai-center.png)

</details>

## 🔒 数据留在本机

上述运行包在自己的电脑上处理音乐数据，项目不会把你的歌单或登录凭据上传到作者服务器。默认只整理音乐元数据。

播放记录与收藏时间以平台实际返回为准；QQ 缺少可靠完整播放历史，缺失数据不会被推测。[隐私说明](PRIVACY.md) · [常见问题](docs/FAQ.md) · [下载与安全](SECURITY.md)

## 更多信息

- [AI 分析使用说明](docs/AI_ANALYSIS.md) · [数据格式](docs/DATA_FORMAT.md)
- [反馈问题](https://github.com/rhr-jz/netease-music-insight/issues)：请提供系统、版本和复现步骤，避免附上私人数据。
- [开发者文档](docs/DEVELOPMENT.md) · [项目架构](docs/ARCHITECTURE.md) · [3.0 RC1 对应源码](https://github.com/rhr-jz/netease-music-insight/tree/portable-v3.0.0-rc.1)

[GPL-3.0-or-later](LICENSE) · [第三方许可](THIRD_PARTY_LICENSES.md)。Music Insight 是非官方开源项目，与网易云音乐、QQ 音乐无官方关系。仓库名称保留最初的网易云项目名称。
