# 快速开始

1. **下载**：[Windows 发布页](https://github.com/rhr-jz/netease-music-insight/releases)下载 `MusicInsight-Windows-Portable.zip`，完整解压。
2. **双击**：新版目录包中双击 `MusicInsight.exe`，旧版目录包仍使用 `MusicInsight-Windows-Portable.exe`。新版界面需要 Microsoft Edge WebView2 Runtime。
3. **扫码**：在界面选择网易云、QQ 音乐或两个平台，用对应音乐 App 扫描程序内的二维码并在手机确认。登录后点击“开始整理我的音乐”。
4. **查看**：导出完成后，“我的音乐”展示数量、常出现歌手与专辑，也可搜索本地歌曲。重新打开桌面端或断网后仍可查看已导出的数据。
5. **分析**：在“AI 分析”选择一个方向，直接阅读并复制完整 Prompt。按页面说明，把“导出”页列出的 `music_for_ai.json` 上传给你常用的 AI；两个平台联合分析时上传 `music_for_ai_combined.json`。ChatGPT、Claude、Gemini 或其他支持文件上传的 AI 都可使用。

macOS 源码版：先安装 [Python 3.10+](https://www.python.org/downloads/macos/)，下载仓库 ZIP 并完整解压，然后双击 `一键运行.command`。若导出网易云，还需安装 [Node.js 18+](https://nodejs.org/)；仅导出 QQ 音乐无需 Node.js。之后同样按第 3–5 步操作。若 macOS 询问 Terminal 的文件夹访问权限，请根据文件所在位置允许访问。

Linux 源码版：安装 Python 3.10+，在仓库目录依次执行 `python3 -m venv .venv`、`.venv/bin/python -m pip install -r requirements.txt`、`.venv/bin/python run.py`。网易云导出还需 Node.js 18+。

第一次使用建议选择 **01 音乐全景画像**。想看审美、歌手、音乐地图、谈资或八周听歌计划，也可以直接选对应模块；每段提示词都能单独使用。

## 文件在哪里？

- 网易云：`output/用户名_UID/`
- QQ 音乐：`output/qq_music/用户名_UID/`
- 两个平台的联合结果：`output/combined/`

`music_for_ai.json` 是上传给 AI 的文件；`music_summary.md` 是自己阅读的摘要；`AI_ANALYSIS_GUIDE.md` 解释每个分析方向，`prompts/` 中则按方向单独存放提示词。你不需要打开或编辑数据文件。

## 源码版与进阶用法

Windows 源码版请先安装 Python 3.10+，下载仓库并解压，双击 `一键运行.bat`。旧命令行参数仍可用：`python run.py --provider netease|qq|all`；`--fresh` 重新获取数据。

网易云播放记录的范围由服务端决定，不能视为账号完整终身历史；QQ 播放历史暂标记不可用。若某个歌单无法访问，导出会继续，并在 `music_summary.md` 中注明。仅使用实际返回的收藏与歌单时间。
