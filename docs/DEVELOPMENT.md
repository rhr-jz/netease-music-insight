# 开发与验证

用户下载与使用步骤见 [QUICK_START.md](QUICK_START.md)；本文面向源码贡献者。

## 环境

需要 Python 3.10+。Windows 桌面版还依赖 Microsoft Edge WebView2 Runtime。网易云数据导出在 macOS、Linux 上需要 Node.js 18+；Windows 首次运行可由程序准备本地 Node 组件。QQ 音乐不需要 Node.js。

```bash
python -m venv .venv
python -m pip install -r requirements-desktop.txt
```

`requirements-desktop.txt` 包含 CLI/Core 的 `requirements.txt` 和 pywebview。只开发 CLI 或 Local Web 时可以安装 `requirements.txt`。

## 入口

```bash
python run_desktop.py
python run_web.py
python run.py --provider netease   # 也支持 qq / all
python run.py --fresh              # 忽略近期缓存
```

桌面“设置 → 启动 Web 版”会在同一进程中运行 Local Web。单独运行 `run_web.py` 时，程序启动本机服务并自动打开浏览器。两种方式都只监听 `127.0.0.1` 的随机端口。

## 测试

```bash
python -m unittest discover -s tests -v
python run_desktop.py --smoke
python run_web.py --smoke
```

自动测试使用合成账号数据，不需要真实扫码。真实平台接口可能变化；准备复现报告时，请删除或遮盖 Cookie、UID、二维码、歌单名称与私人导出内容。GitHub Actions 在 Windows、macOS 和 Linux 运行同一组单元测试；Windows Release 工作流另构建 PyInstaller 目录包。

## 修改位置

- 新平台接口：`netease_music_insight/providers/` 和 `service.py`。
- 导出字段与联合分析：`report.py`、`combined.py`，并更新 [DATA_FORMAT.md](DATA_FORMAT.md)。
- AI Prompt：集中在 `guidance.py`，Desktop 与 Web 调用同一份数据源。
- 图形界面：`desktop/assets/index.html`；桌面 Bridge 在 `desktop/bridge.py`，本地 HTTP 适配层在 `web/server.py`。
- 发行脚本：`.github/workflows/release.yml`，其中 `docs/PORTABLE_START.txt` 会复制进 Windows ZIP。

本地 `output/`、`.cache/`、`.state/`、`.qqmusic/`、`logs/` 和运行组件目录不得提交。提交前用 `git status` 检查暂存区；不要使用真实账号数据制作测试样例或截图。[架构](ARCHITECTURE.md) · [隐私](../PRIVACY.md)。
