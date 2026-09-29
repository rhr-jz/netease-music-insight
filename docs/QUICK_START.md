# 快速开始

## Windows 桌面版

1. 在 [最新 GitHub Release](https://github.com/rhr-jz/netease-music-insight/releases/latest) 下载带图形界面的 `MusicInsight-Windows-Portable.zip`，完整解压。
2. 双击文件夹中的 `MusicInsight.exe`。不要把 EXE 单独移出解压目录。
3. 选择网易云音乐、QQ 音乐或“两个平台”，用对应 App 扫描程序内二维码并在手机上确认。
4. 点击“开始整理我的音乐”。完成后，在“我的音乐”查看 Dashboard，在“AI 分析”选择方向并复制 Prompt。
5. 在“导出”页找到 JSON、摘要和分析指南。联合分析时将 `music_for_ai_combined.json` 上传给 AI；单平台使用 `music_for_ai.json`。

系统要求：Windows 10/11、Microsoft Edge WebView2 Runtime。首次获取网易云数据需要联网准备本地组件，可能耗时较长。若下载时被安全软件拦截，请阅读 [下载与安全说明](../SECURITY.md)，不要关闭防护或强行运行。

## Local Web

在包含 Web 功能的桌面版“设置”页点击“启动 Web 版”，系统默认浏览器会自动打开。源码用户也可运行 `python run_web.py`。网页只在本机 `127.0.0.1` 的随机端口开放，不是云端账户或公网服务；手机无法直接通过局域网访问电脑页面。请在电脑上打开页面，再用手机扫码。

Local Web 与桌面版共用扫码、导出、Dashboard 和 AI Prompt。网页“导出”页可下载当前文件，已有数据断网后仍可阅读。

## macOS / Linux 源码版

macOS：安装 Python 3.10+，若使用网易云再安装 Node.js 18+。下载并解压仓库 ZIP，双击 `一键运行.command` 进入 CLI。Linux：安装相同依赖后，在仓库目录建立虚拟环境、安装 `requirements.txt`，运行 `python run.py`。QQ 音乐不依赖 Node.js。

源码及测试命令见 [DEVELOPMENT.md](DEVELOPMENT.md)。

## 结果文件

- 网易云：`output/用户名_UID/`
- QQ 音乐：`output/qq_music/用户名_UID/`
- 联合结果：`output/combined/`

`music_summary.md` 供自己阅读；`AI_ANALYSIS_GUIDE.md` 和 `prompts/` 保存可独立使用的分析方向。你也可以直接在程序中阅读和复制 Prompt。[AI 分析说明](AI_ANALYSIS.md) · [数据格式](DATA_FORMAT.md)。
