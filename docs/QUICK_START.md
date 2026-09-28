# 快速开始

1. Windows 用户从 [Releases](https://github.com/rhr-jz/netease-music-insight/releases) 下载 `MusicInsight-Windows-Portable.zip`，完整解压后双击其中的 EXE。源码版则先安装 Python 3.10+，解压仓库后双击 `一键运行.bat`。
2. 选择网易云音乐、QQ 音乐或两个平台。用相应 App 扫描弹出的二维码并在手机上确认。
3. 等待导出完成。网易云结果在 `output/用户名_UID/`，QQ 在 `output/qq_music/用户名_UID/`；选择两个平台还可得到 `output/combined/`。将 JSON 上传给支持文件分析的 AI，再复制对应提示词。

网易云播放记录的范围由服务端决定，不能视为账号完整终身历史；QQ 播放历史暂标记不可用。若某个歌单无法访问，导出会继续，并在 `music_summary.md` 中注明。仅使用实际返回的收藏与歌单时间。
