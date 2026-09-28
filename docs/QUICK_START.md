# 快速开始

1. Windows 用户从 [Releases](https://github.com/rhr-jz/netease-music-insight/releases) 下载 `NetEaseMusicInsight-Windows.exe` 并双击。源码版则先安装 Python 3.10+，解压仓库后双击 `一键运行.bat`。
2. 首次运行等待本地组件自动准备好。网易云音乐 App 扫描弹出的二维码并在手机上确认。
3. 等待导出完成。打开 `output/用户名_UID/`，将 `music_for_ai.json` 上传给支持文件分析的 AI，再复制 `AI_ANALYSIS_PROMPT.md` 的内容。

播放记录的范围由网易云服务端决定，不能视为账号完整终身历史。若某个歌单无法访问，导出会继续，并在 `music_summary.md` 中注明。
