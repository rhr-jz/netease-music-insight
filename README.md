# 🎧 Music Insight

双击、扫码、等待导出，再从分析指南中挑一个感兴趣的问题。无需了解 Python、数据格式或提示词写法。

## 导出之后能做什么？

了解自己的音乐审美、找到真正喜欢的歌手、发现可能喜欢的新音乐、建立音乐地图、整理歌单、准备和同龄人聊音乐的话题，或制定轻松的八周听歌计划。导出结果按主题提供独立提示词；你只需上传文件并复制其中一段。

```text
网易云音乐 / QQ 音乐
        ↓ 扫码
  Music Insight 整理数据
        ↓
music_for_ai.json（两个平台时也有 music_for_ai_combined.json）
        ↓ 上传并选择一个问题
ChatGPT / Claude / Gemini / 其他支持文件上传的 AI
        ↓
个人音乐画像与探索建议
```

## 它能做什么？

- 扫码导出喜欢的歌曲、自建与收藏的歌单、歌单歌曲；网易云还会尝试获取服务端可返回的播放记录。
- 选择两个平台时生成联合报告，仅自动合并高置信的同一首录音。
- 保留接口实际提供的歌曲收藏时间、歌单创建时间与 QQ 收藏歌单排序时间；缺失的时间标记未知。
- 自动生成 `music_for_ai.json`、易读概要、分领域 AI 指南和可单独复制的提示词。
- 歌单有无权限或下架内容时继续导出，并标出缺失范围。
- 数据只保存在你的电脑中；程序不要求密码，也不上传数据到作者服务器。

## 🚀 最快使用方法

### Windows 10 / 11：下载目录版

1. 到 [Releases](https://github.com/rhr-jz/netease-music-insight/releases) 下载包含桌面界面的新版 `MusicInsight-Windows-Portable.zip`，完整解压后双击 `MusicInsight.exe`。需要 Windows 10/11 和 Microsoft Edge WebView2 Runtime；首次使用网易云时需要联网准备本地接口组件。
2. 在界面中选择平台，使用相应手机 App 扫描程序内显示的二维码并确认，再点“开始整理我的音乐”。
3. 在“我的音乐”查看概况，在“导出”打开结果文件夹。把 `music_for_ai.json` 上传给支持文件分析的 AI，再从 `AI_ANALYSIS_GUIDE.md` 选择一个问题复制提示词。选两个平台时，优先上传联合结果中的 `music_for_ai_combined.json`。旧版 Release 仍是命令行界面。

### Windows 10 / 11：源码运行

1. 安装 [Python 3.10+](https://www.python.org/downloads/windows/)（安装时勾选 **Add Python to PATH**），下载本仓库 ZIP 并解压。
2. 双击 `一键运行.bat`。首次启动会自动安装 Python 依赖；仅网易云需要准备本地 Node.js 和接口组件。无需安装 Git。
3. 扫码、等待导出，按窗口提示使用结果。

### macOS：源码运行

1. 安装 [Python 3.10+](https://www.python.org/downloads/macos/)；若要导出网易云音乐，还需安装 [Node.js 18+](https://nodejs.org/)。
2. 下载本仓库 ZIP 并完整解压，然后双击 `一键运行.command`。首次启动会建立独立 Python 环境并安装依赖；网易云首次使用还会准备本地接口组件。
3. 选择平台，用对应音乐 App 扫描自动打开的二维码并确认。导出后可在菜单中选择用 Finder 打开结果目录。

如果 macOS 询问是否允许 Terminal 访问下载或文稿目录，请根据文件所在位置允许访问。无需安装 Git，也无需手动查找 Cookie。

### Linux：源码运行

安装 Python 3.10+；导出网易云还需 Node.js 18+。在仓库目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

程序会尝试用系统的 `xdg-open` 打开二维码和结果文件夹；若桌面环境不支持，可按终端提示手动打开二维码图片。

```text
Music Insight
看见属于你的音乐世界
请选择音乐平台
  1 网易云音乐   2 QQ 音乐   3 两个平台
步骤 1 / 4 · 登录账号
二维码已在新窗口打开。请用对应的音乐 App 扫码。
步骤 2 / 4 · 获取音乐数据
步骤 3 / 4 · 整理 AI 数据
步骤 4 / 4 · 完成
网易云音乐：数据已准备好
  music_for_ai.json  ← 上传给 AI 的主要文件
  AI_ANALYSIS_GUIDE.md  ← 选择一个问题和对应提示词
```

网易云结果仍位于 `output/用户名_UID/`；QQ 结果位于 `output/qq_music/用户名_UID/`，联合结果位于 `output/combined/`。

```text
music_for_ai.json          上传给 AI 的统一数据
music_summary.md           给人看的概要与缺失说明
AI_ANALYSIS_GUIDE.md       按兴趣挑选分析方向与完整提示词
prompts/                   每个方向单独一个文件
AI_ANALYSIS_PROMPT.md      兼容旧版的一份综合提示词
raw/                       基础原始列表，便于核对
```

指南按实际数据展示最多 13 个方向：全景画像、真实审美、核心歌手、听歌习惯、成长轨迹、音乐地图、音乐盲区、音乐谈资、系统听歌计划、歌单整理、情绪音乐、年度总结和跨平台对比。缺少可靠时间时隐藏成长轨迹与年度总结；只导出一个平台时不显示跨平台对比。不同方向均可单独复制，不必依次执行。

## 数据边界

**网易云播放历史仅包含服务端当前允许返回的记录，不等于账号完整终身播放历史。QQ 音乐播放历史没有经过验证的可靠接口，目前标记不可用；不会伪造或估算。** 下架歌曲、私密歌单或接口故障可能造成缺口，文件中的 `export_meta.status` 和 `issues` 会标出。真实账号测试未返回逐首 QQ 喜欢时间，因此显示未知。QQ 收藏歌单的 `orderTime` 是收藏排序时间，不保证等于首次收藏日期。

两个平台的个人数据功能依赖非公开接口，可能随平台更新而变化。本项目只读取用户本人有权访问的账户元数据，不绕过付费限制、不下载音乐文件。

本地接口组件来自 [TH911/NeteaseCloudMusicApi](https://github.com/TH911/NeteaseCloudMusicApi)（MIT）。它运行在 `127.0.0.1`，只在导出期间启动。首次启动通常需要下载组件和安装依赖，因此耗时可能超过五分钟；后续运行会直接复用。

QQ 音乐使用 [QQMusicApi 0.7.3](https://github.com/L-1124/QQMusicApi/releases/tag/v0.7.3)（GPL-3.0-or-later）。许可及第三方声明见 [LICENSE](LICENSE) 和 [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)。

## 需要帮助？

- [快速开始](docs/QUICK_START.md) · [数据格式](docs/DATA_FORMAT.md) · [常见问题](docs/FAQ.md) · [隐私说明](PRIVACY.md) · [项目架构](docs/ARCHITECTURE.md)
- 若浏览器或杀毒软件拦截下载，请阅读[下载与安全说明](SECURITY.md)，不要关闭防护或强行运行。
- `python run.py --version` 查看版本；`python run.py --provider netease|qq|all` 可免交互选择；`--fresh` 忽略最近 24 小时的缓存。
- 开发者：`python -m unittest discover -s tests -v` 运行离线测试。
- Windows 桌面 GUI 源码入口为 `python run_desktop.py`，安装依赖用 `pip install -r requirements-desktop.txt`；CLI 继续使用 `python run.py`。架构与技术选型见[架构准备文档](docs/GUI_WEB_ARCHITECTURE.md)。

本项目为个人数据导出工具，与网易云音乐及其关联公司无官方关系。仅导出自己有权访问的数据。
