# 快速开始

## Windows

1. 从 [Releases](https://github.com/rhr-jz/netease-music-insight/releases) 下载 `NetEaseMusicInsight-Windows.exe` 并双击。源码版则先安装 Python 3.10+，解压仓库后双击 `一键运行.bat`。
2. 首次运行等待本地组件自动准备好。使用网易云音乐 App 扫描弹出的二维码并在手机上确认。

## macOS

1. 安装 [Python 3.10+](https://www.python.org/downloads/macos/) 和 [Node.js 18+](https://nodejs.org/)，推荐 Node.js LTS 版本。
2. 下载仓库 ZIP 并完整解压，双击 `一键运行.command`。脚本会在首次运行时创建 `.venv`、安装 Python 依赖并准备本地接口组件。
3. 使用网易云音乐 App 扫描自动打开的二维码并确认。若系统询问 Terminal 的文件夹访问权限，请根据仓库所在位置允许访问。

## 导出结果

等待导出完成。程序会打开 `output/用户名_UID/`，将其中的 `music_for_ai.json` 上传给支持文件分析的 AI，再复制 `AI_ANALYSIS_PROMPT.md` 的内容。

播放记录的范围由网易云服务端决定，不能视为账号完整终身历史。若某个歌单无法访问，导出会继续，并在 `music_summary.md` 中注明。
