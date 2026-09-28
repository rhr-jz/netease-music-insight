# NetEase Music Insight

一键导出网易云音乐听歌数据，并使用 AI 分析你的音乐品味。

## 它能做什么？

- 导出喜欢的歌曲、自建与收藏的歌单、可获取的歌单歌曲和播放记录。
- 自动生成 `music_for_ai.json`、易读概要和可直接复制的 AI 分析提示词。
- 歌单有无权限或下架内容时继续导出，并标出缺失范围。
- 数据只保存在你的电脑中；程序不要求密码，也不上传数据到作者服务器。

## 🚀 最快使用方法

### Windows 10 / 11：直接下载 EXE

1. 到 [Releases](https://github.com/rhr-jz/netease-music-insight/releases) 下载 `NetEaseMusicInsight-Windows.exe`，放进一个可写的文件夹并双击。也可下载 `NetEaseMusicInsight-Windows-Portable.zip`，完整解压后双击文件夹中的 EXE。首次运行需要联网准备本地接口组件。
2. 使用网易云音乐 App 扫描自动打开的二维码，在手机上确认。
3. 等待“完成”，按提示上传 `music_for_ai.json` 并复制 `AI_ANALYSIS_PROMPT.md` 给 ChatGPT、Claude 或 Gemini。

### Windows 10 / 11：源码运行

1. 安装 [Python 3.10+](https://www.python.org/downloads/windows/)（安装时勾选 **Add Python to PATH**），下载本仓库 ZIP 并解压。
2. 双击 `一键运行.bat`。首次启动会自动安装 Python 依赖，并在需要时准备本地 Node.js 和网易云接口组件；无需安装 Git。
3. 扫码、等待导出，按窗口提示使用结果。

### macOS：源码运行

1. 安装 [Python 3.10+](https://www.python.org/downloads/macos/) 和 [Node.js 18+](https://nodejs.org/)；推荐 Node.js LTS 版本。
2. 下载本仓库 ZIP 并完整解压，然后双击 `一键运行.command`。首次启动会建立独立 Python 环境、安装依赖并准备本地网易云接口组件。
3. 使用网易云音乐 App 扫描自动打开的二维码并确认。导出完成后，Finder 会自动打开结果目录。

如果 macOS 询问是否允许 Terminal 访问下载或文稿目录，请根据文件所在位置允许访问。无需安装 Git，也无需手动查找 Cookie。

```text
欢迎使用 NetEase Music Insight
✓ 登录成功：示例用户
喜欢音乐：601 首
✓ 歌单 88/88：示例歌单（35 首）
数据检查：喜欢 601/601；歌单 88/88；歌曲位置 3200，去重 1800；问题 0 项
完成！文件位于：output/示例用户_123456/
```

结果位于 `output/用户名_UID/`：

```text
music_for_ai.json          上传给 AI 的统一数据
music_summary.md           给人看的概要与缺失说明
AI_ANALYSIS_PROMPT.md      复制给 AI 的分析任务
raw/                       基础原始列表，便于核对
```

## 数据边界

**播放历史仅包含网易云服务端当前允许返回的记录，不等于账号完整终身播放历史。** 下架歌曲、私密歌单或接口故障也可能造成缺口，文件中的 `export_meta.status` 和 `issues` 会明确标出。程序依赖网易云未公开接口与本地开源封装，接口变化可能让部分功能失效；欢迎提交 Issue。

本地接口组件来自 [TH911/NeteaseCloudMusicApi](https://github.com/TH911/NeteaseCloudMusicApi)（MIT）。它运行在 `127.0.0.1`，只在导出期间启动。首次启动通常需要下载组件和安装依赖，因此耗时可能超过五分钟；后续运行会直接复用。

## 需要帮助？

- [快速开始](docs/QUICK_START.md) · [数据格式](docs/DATA_FORMAT.md) · [常见问题](docs/FAQ.md) · [隐私说明](PRIVACY.md)
- 若浏览器或杀毒软件拦截下载，请阅读[下载与安全说明](SECURITY.md)，不要关闭防护或强行运行。
- `python run.py --version` 查看版本；`python run.py --fresh` 忽略最近 24 小时的缓存并重新抓取。
- 开发者：`python -m unittest discover -s tests -v` 运行离线测试。

本项目为个人数据导出工具，与网易云音乐及其关联公司无官方关系。仅导出自己有权访问的数据。
