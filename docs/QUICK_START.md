# 快速上手

## 1. 下载对应系统的完整运行包

从 [Music Insight 3.0 RC1 下载页面](https://github.com/rhr-jz/netease-music-insight/releases/tag/portable-v3.0.0-rc.1) 选择：

- Windows 10/11 x64：`MusicInsight-Windows-x64-3.0.0rc1.zip`。Windows 11 ARM 使用系统 x64 兼容层。
- Mac M 系列：`MusicInsight-macOS-AppleSilicon-3.0.0rc1.zip`。
- Mac Intel：`MusicInsight-macOS-Intel-3.0.0rc1.zip`。

这是预发布版本。运行组件已包含在包内，不需要安装 Python、Node、npm 或填写 AI API Key。Mac 建议 macOS 14 及以上；32 位和更早系统不在支持范围。Mac 包未 Apple 公证，首次打开可能需要系统安全确认。[下载与安全说明](../SECURITY.md)

## 2. 打开并扫码

完整解压 ZIP，再双击 `MusicInsight.exe` 或 `MusicInsight.app`。不要只移动 EXE；Mac 可移动整个 `.app` 到“应用程序”。

选择网易云、QQ 或两个平台，用对应音乐 App 扫描程序中的二维码并在手机确认，点击“开始整理我的音乐”。二维码过期可直接重新生成。同步需要网络。

## 3. 浏览与 AI 分析

- “我的音乐”：查看 Dashboard，搜索歌曲、歌手和专辑，浏览喜欢歌曲、歌单与可用记录。
- “AI 分析”：选择方向，复制完整 Prompt。
- “导出”：打开数据文件夹，查看 JSON、摘要和指南；本地网页端还可下载全部文件 ZIP。

把 `music_for_ai.json` 和 Prompt 交给你选择的 AI；联合分析使用 `music_for_ai_combined.json`。无需 API Key；Music Insight 不会自动向 AI 上传文件。[AI 分析说明](AI_ANALYSIS.md)

## 想在浏览器使用

在“设置”点击“启动 Web 版”，或打开包中的 `Open Local Web.cmd` / `Open Local Web.command`。浏览器会自动打开本机页面，数据仍在自己的电脑上，只监听 `127.0.0.1`。

Windows 桌面使用系统 Edge WebView2，缺少该组件时会回退到系统浏览器。Local Web 地址不能直接通过局域网在另一台手机上打开；扫码时在电脑显示二维码，用手机扫描。

## 我的文件在哪里

3.0 RC1 完整包默认保存到当前用户目录，也可在设置中更改输出路径：

- Windows：`%LOCALAPPDATA%\MusicInsight\output`
- Mac：`~/Library/Application Support/MusicInsight/output`

使用“打开数据文件夹”最方便。已有档案和 Prompt 可离线浏览。转发原始 ZIP 给朋友，不要附带自己的导出、缓存或凭据。

旧版本和源码版可能使用仓库下的 `output/`；以设置中的实际路径为准。[常见问题](FAQ.md) · [开发者运行方式](DEVELOPMENT.md)
