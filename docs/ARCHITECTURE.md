# Music Insight v3 架构

四个入口，一套 Core。保持现有 Provider、分页、报表、联合匹配和 Prompt 逻辑，不复制平台实现。

```text
Desktop ─ pywebview ─ DesktopBridge ┐
Local Web ─ loopback HTTP ──────────┤
CLI ─ cli.py ──────────────────────┼─ MusicInsightService
Online Web ─ FastAPI ─ Session ────┘       │
                         Job/Bridge       ├─ NetEaseProvider
                         Storage          ├─ QQMusicProvider
                                          └─ report / combined / guidance
```

## 共享界面

`frontend/index.html`、`ui.css`、`app.js`、`library.js` 是 Desktop、Local Web 与 Online Web 的唯一 UI 资源。`bridge.js` 的 MusicInsightAPI 适配 pywebview、Local HTTP 与 Online API。业务数据、Prompt 和跨平台匹配来自 Python Core。

Desktop 使用内嵌资源，不依赖文件 URL 或远程 CDN；Local Web 给所有脚本加 nonce 并注入本机 CSRF 配置。Online 使用独立同源资源、严格 CSP、带 nonce 的动态布局，不给 JS 暴露平台凭据。

## 本地入口

Desktop 后台线程调用 Core，Windows 主线程只负责界面。Local Web 保留 loopback-only ThreadingHTTPServer、随机空闲端口、精确 Host/Origin 校验、独立随机 Cookie 和 CSRF。当前 Desktop 会话可与 Local Web 共用 Bridge。本机结果恢复和离线浏览不变。

`desktop/library.py` 保留历史导出发现与事实 Dashboard helper 的兼容导入；`library.py` 提供公共分页浏览。CLI 继续使用 `run.py --provider netease/qq/all`。

## Online

`online/server.py` 提供 FastAPI API；`sessions.py` 为每个安全随机 Session 创建独立 Bridge、目录和状态；`jobs.py` 限制全服务器任务容量。会话内只允许一个任务，每个平台的请求串行/受已有 Provider 限流控制。线程任务不阻塞 ASGI，SSE 失败回退查询快照。

Job 状态：pending、login、syncing、processing、completed、partial、cancelled、failed。两平台逐个登录；一个失败可保留另一个已完成结果，两者均成功才运行 Core.combine。新单平台同步使旧 Combined 失效。刷新可恢复状态，重启不恢复。

`LocalTemporaryStorage` 实现 StorageBackend。每个 Session 与 Job 使用随机独立目录，缓存、QR、QQ device 配置和输出不共享。下载只认可当前会话的 opaque manifest ID。ZIP 包含报表与独立 Prompt。退出立即撤销访问，取消与 finally 清理凭据和目录；TTL 执行相同流程。

`provider_runtime.py` 注入替代 local_api 的预构建上下文。Docker 在构建阶段下载校验固定上游和安装锁定依赖；每 Job 创建独立 loopback Node 进程和 temp 环境，禁用版本下载检查，结束时终止进程。

## 安全与扩展

Online 的 Session Cookie 为 HttpOnly / Secure / SameSite=Strict；生产 HTTPS、Host/Origin/请求头校验、请求大小限制、严格模型、Session/IP 限流、no-store 与安全响应头。日志固定字段，不格式化任意上游异常。前端没有广告、遥测或 Token LocalStorage。

当前仅支持单实例/单 Worker。未来可替换 Session Store、Job Queue 与 StorageBackend；当前不增加 Redis 或对象存储依赖。Docker 非 root、只读、tmpfs、有资源限制和健康检查。

本地与在线版本的数据边界不同：[PRIVACY](../PRIVACY.md)。[在线接口与使用](ONLINE_WEB.md) · [部署](DEPLOYMENT.md)
