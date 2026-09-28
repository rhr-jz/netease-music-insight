# 🎧 Music Insight

一键导出网易云音乐 / QQ 音乐账户数据，并使用 AI 分析你的音乐品味。

## 它能做什么？

- 扫码导出喜欢的歌曲、自建与收藏的歌单、歌单歌曲；网易云还会尝试获取服务端可返回的播放记录。
- 选择两个平台时生成联合报告，仅自动合并高置信的同一首录音。
- 保留接口实际提供的歌曲收藏时间、歌单创建时间与 QQ 收藏歌单排序时间；缺失的时间标记未知。
- 自动生成 `music_for_ai.json`、易读概要和可直接复制的 AI 分析提示词。
- 歌单有无权限或下架内容时继续导出，并标出缺失范围。
- 数据只保存在你的电脑中；程序不要求密码，也不上传数据到作者服务器。

## 🚀 最快使用方法（Windows 10 / 11）

### 方法一：直接下载 EXE

1. 到 [Releases](https://github.com/rhr-jz/netease-music-insight/releases) 下载 `MusicInsight-Windows-Portable.zip`，完整解压后双击其中的 EXE。首次使用网易云时需要联网准备本地接口组件。
2. 选择平台，使用相应手机 App 扫描自动打开的二维码并确认。
3. 等待“完成”，按提示上传 `music_for_ai.json` 并复制 `AI_ANALYSIS_PROMPT.md` 给 ChatGPT、Claude 或 Gemini。

### 方法二：源码运行

1. 安装 [Python 3.10+](https://www.python.org/downloads/windows/)（安装时勾选 **Add Python to PATH**），下载本仓库 ZIP 并解压。
2. 双击 `一键运行.bat`。首次启动会自动安装 Python 依赖；仅网易云需要准备本地 Node.js 和接口组件。无需安装 Git。
3. 扫码、等待导出，按窗口提示使用结果。

```text
🎧 Music Insight
请选择数据来源：
[1] 网易云音乐
[2] QQ 音乐
[3] 同时导出网易云 + QQ 音乐
✓ 登录成功：示例用户
喜欢音乐：601 首
✓ 歌单 88/88：示例歌单（35 首）
数据检查：喜欢 601/601；歌单 88/88；歌曲位置 3200，去重 1800；问题 0 项
完成！文件位于：output/示例用户_123456/
```

QQ 音乐示例（虚构账号）：

```text
✓ 登录成功：示例用户
✓ 我喜欢：42 首
✓ 自建歌单：3；收藏歌单：2
数据检查：我喜欢 42/42；歌单 5/5；歌曲位置 180；问题 0 项
✓ qq：output/qq_music/示例用户_123456/
```

网易云结果仍位于 `output/用户名_UID/`；QQ 结果位于 `output/qq_music/用户名_UID/`，联合结果位于 `output/combined/`。

```text
music_for_ai.json          上传给 AI 的统一数据
music_summary.md           给人看的概要与缺失说明
AI_ANALYSIS_PROMPT.md      复制给 AI 的分析任务
raw/                       基础原始列表，便于核对
```

## 数据边界

**网易云播放历史仅包含服务端当前允许返回的记录，不等于账号完整终身播放历史。QQ 音乐播放历史没有经过验证的可靠接口，目前标记不可用；不会伪造或估算。** 下架歌曲、私密歌单或接口故障可能造成缺口，文件中的 `export_meta.status` 和 `issues` 会标出。真实账号测试未返回逐首 QQ 喜欢时间，因此显示未知。QQ 收藏歌单的 `orderTime` 是收藏排序时间，不保证等于首次收藏日期。

两个平台的个人数据功能依赖非公开接口，可能随平台更新而变化。本项目只读取用户本人有权访问的账户元数据，不绕过付费限制、不下载音乐文件。

本地接口组件来自 [TH911/NeteaseCloudMusicApi](https://github.com/TH911/NeteaseCloudMusicApi)（MIT）。它运行在 `127.0.0.1`，只在导出期间启动。首次启动通常需要下载组件和安装依赖，因此耗时可能超过五分钟；后续运行会直接复用。

QQ 音乐使用 [QQMusicApi 0.7.3](https://github.com/L-1124/QQMusicApi/releases/tag/v0.7.3)（GPL-3.0-or-later）。项目 1.1 的许可及第三方声明见 [LICENSE](LICENSE) 和 [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)。

## 需要帮助？

- [快速开始](docs/QUICK_START.md) · [数据格式](docs/DATA_FORMAT.md) · [常见问题](docs/FAQ.md) · [隐私说明](PRIVACY.md)
- 若浏览器或杀毒软件拦截下载，请阅读[下载与安全说明](SECURITY.md)，不要关闭防护或强行运行。
- `python run.py --version` 查看版本；`python run.py --provider netease|qq|all` 可免交互选择；`--fresh` 忽略最近 24 小时的缓存。
- 开发者：`python -m unittest discover -s tests -v` 运行离线测试。

本项目为个人数据导出工具，与网易云音乐及其关联公司无官方关系。仅导出自己有权访问的数据。
