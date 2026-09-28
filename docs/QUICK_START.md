# 快速开始

1. **下载**：[Windows 发布页](https://github.com/rhr-jz/netease-music-insight/releases)下载 `MusicInsight-Windows-Portable.zip`，完整解压。
2. **双击**：打开解压后的文件夹，双击 `MusicInsight-Windows-Portable.exe`。
3. **扫码**：选择网易云、QQ 音乐或两个平台，用对应音乐 App 扫描自动打开的二维码并在手机确认。
4. **上传**：导出完成后，打开结果文件夹，把 `music_for_ai.json` 上传给你常用的 AI。两个平台联合分析时上传 `output/combined/music_for_ai_combined.json`。
5. **复制**：打开同一文件夹中的 `AI_ANALYSIS_GUIDE.md`，挑一个感兴趣的问题，复制该模块的完整提示词并发送。ChatGPT、Claude、Gemini 或其他支持上传文件的 AI 都可使用。

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
