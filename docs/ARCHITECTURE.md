# 项目架构

GUI / Local Web 的技术选型、共享 Core 接口、事件及后台任务方案见 [第 1 阶段架构准备](GUI_WEB_ARCHITECTURE.md)。当前正式入口仍为 CLI。

Music Insight 是本地命令行工具。平台数据读取、数据整理、终端交互和系统集成各自集中在一个位置，便于添加新平台或修复系统兼容问题。

```text
run.py / 双击脚本 / EXE
        ↓
cli.py ── ui.py ── platform_utils.py
  │
  └─ service.py ── events.py / errors.py
        ├─ providers/netease.py ── auth.py / bootstrap.py / api.py / exporter.py
        └─ providers/qqmusic.py
        ↓
report.py / combined.py ── guidance.py
        ↓
output/ 里的数据、摘要与独立 AI 提示词
```

- `cli.py` 负责平台选择、失败重试与结果展示；`service.py` 统一编排登录、单平台和联合导出，不依赖终端。
- `providers/` 负责登录和读取账号数据，向 Service 返回 `(输出文件夹, 标准化数据)`。QQ 与网易云的接口差异留在各自 Provider 内。
- `report.py` 生成单平台数据和摘要；`combined.py` 只对高置信的同一录音做跨平台合并；`guidance.py` 根据实际可用字段生成独立分析方向。
- `ui.py` 把 Core 事件翻译成用户可理解的步骤，负责终端输入和打开文件。`platform_utils.py` 是打开二维码图片与结果文件夹的系统入口：Windows 使用默认程序，macOS 使用 `open`，Linux 使用 `xdg-open`。
- `bootstrap.py` 仅在网易云导出时启动本机 `127.0.0.1` 接口。Windows 可准备便携 Node.js；macOS / Linux 需要系统安装 Node.js 18+。QQ 导出不依赖 Node.js。

Windows 双击入口是 `一键运行.bat` 或发布包中的 EXE；macOS 源码入口是 `一键运行.command`。两者最终调用同一个 `run.py`，不复制导出逻辑。

## 修改与验证

1. 新增音乐平台时，在 `providers/` 实现登录、读取与标准化，并保留实际的可用能力和时间字段，再接入 Service；CLI 只负责用户交互。
2. 新增系统集成时，优先扩展 `platform_utils.py`，不要在 Provider 中散落系统命令。
3. 用 `python -m unittest discover -s tests -v` 运行离线测试；GitHub Actions 在 Windows、macOS 和 Linux 运行同一组测试。macOS / Linux 还检查启动脚本语法。
4. 本地真实账号数据、Cookie、缓存、日志和 `output/` 不应进入提交。发布包由标签触发的 Windows 工作流构建。
