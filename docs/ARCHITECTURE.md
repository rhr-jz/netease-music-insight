# Music Insight 当前架构

Music Insight 有三个入口：Windows Desktop、Local Web 与 CLI。它们调用同一套 `MusicInsightService`、Provider、数据整理和 Prompt 代码，不复制音乐平台请求。

```text
run_desktop.py → pywebview → desktop/assets/index.html → DesktopBridge ┐
run_web.py     → 127.0.0.1 HTTP → 同一份 index.html → DesktopBridge ├→ MusicInsightService
run.py         → cli.py ───────────────────────────────────────────────┘
                                                                  │
                ┌─────────────────────────────────────────────────┘
                ▼
      providers/netease.py · providers/qqmusic.py
                ↓
      report.py · combined.py · guidance.py
                ↓
      output/ JSON · Markdown · prompts/
```

## Core 与界面

- `service.py` 负责登录、抓取与导出编排；`providers/` 处理平台差异。网易云通过本机 Node 接口访问账号数据，QQ 使用 `qqmusic-api-python`。
- `report.py` 构造单平台数据和摘要；`combined.py` 只合并高置信度的跨平台同一录音；`guidance.py` 根据真实可用字段生成 AI Prompt。
- `events.py` 向界面发送扫码、资料、歌单、播放历史、统计和导出事件；`errors.py` 统一核心错误。Core 不依赖终端打印或 GUI。
- `desktop/bridge.py` 维护线程安全的任务状态。后台 Worker 执行 `MusicInsightService`；界面只读取状态快照，取消由 `CancellationToken` 协作完成。
- `desktop/library.py` 从已有 JSON 恢复离线 Dashboard、数据来源和 AI 卡片。Desktop 与 Web 使用同一份 `desktop/assets/index.html` 和同一份 `guidance.py`。
- `cli.py` 与 `ui.py` 保留进阶命令行入口；不影响图形入口。

## Desktop

`run_desktop.py` 启动 pywebview 窗口。Windows 上使用系统 WebView2；窗口内通过 pywebview JS API 调用 Bridge，二维码由 Bridge 读取到内存并作为图片显示。数据获取在后台线程执行，不占用 UI 线程。窗口尺寸与布局在共享页面中维护。

## Local Web

`run_web.py` 启动 `web/server.py`，绑定 `127.0.0.1` 的随机空闲端口，然后自动打开默认浏览器。桌面“设置 → 启动 Web 版”也可启动服务，并与已打开的桌面窗口共享 Bridge 状态。页面通过本地 HTTP 适配层调用 Bridge；Web 不直接请求网易云或 QQ 音乐接口。

安全边界：

- 仅允许精确的 `127.0.0.1:端口` Host；修改状态的请求还要有同源 Origin、会话 Cookie 和 CSRF 标头。
- 会话 Cookie 为 HttpOnly、SameSite=Strict；页面使用严格的 CSP、禁用缓存和防嵌入标头，不载入第三方脚本。
- 浏览器只得到展示所需的二维码和状态，不得到平台 Cookie 或 Token；原始异常详情仅写入本机日志。
- 下载接口只提供当前选中结果中的 JSON、摘要和分析指南；文件名固定，并检查解析后的路径仍在当前结果目录。
- 不提供远程数据库或作者服务器。由于默认只绑定回环地址，其他设备无法直接访问电脑上的 Local Web。

## 数据与进度

两平台及联合结果仍使用原导出格式，保留收藏和歌单时间的实际可用值；缺失值不推断。成功导出的数据保存在用户指定的 `output/`，阶段缓存放在 `.cache/`。已导出的 Dashboard 与 Prompt 可离线浏览；重新同步音乐平台需要网络。缓存和输出的清理边界见 [隐私说明](../PRIVACY.md)，字段见 [数据格式](DATA_FORMAT.md)。

## 验证与发布

离线测试运行 `python -m unittest discover -s tests -v`，覆盖网易云、QQ、Combined、Desktop Bridge、Web 安全边界和导出。GitHub Actions 在 Windows、macOS、Linux 运行测试；Windows Release 工作流用 PyInstaller 生成目录版 ZIP。开发步骤见 [DEVELOPMENT.md](DEVELOPMENT.md)。最初的 GUI / Web 选型记录保留在 [legacy/](legacy/GUI_WEB_ARCHITECTURE_STAGE1.md)。
