# 部署 Online Web

## 最简单的生产部署

使用一台能运行 Docker 的常驻服务器、一个 HTTPS 域名、一个应用实例和一个 Uvicorn Worker。不需要 Redis、数据库或云对象存储。不要直接把 Local Web 的 `web/server.py` 暴露到公网。

```bash
cp .env.example .env
# 编辑 .env：PUBLIC_URL 填真实 HTTPS origin，SECRET 填随机 32 字符以上的值
docker compose up -d --build
```

SECRET 可用 `python -c "import secrets; print(secrets.token_urlsafe(32))"` 本机生成。不要提交 `.env`。`PUBLIC_URL` 不含路径，例如 `https://music.example.com`。Compose 将应用端口仅映射到服务器的 `127.0.0.1:8000`。

配置同机 Caddy（[官方 HTTPS 说明](https://caddyserver.com/docs/quick-starts/https)）：把 `deploy/Caddyfile` 中的域名换成真实域名，确保域名指向该服务器且 80/443 可达，再启动 Caddy。反向代理保留 Host，不缓存 API，不开启访问日志，不缓冲 SSE。也可使用已有 Nginx 或平台托管的 TLS。

```bash
docker compose ps
docker compose exec music-insight python -m netease_music_insight.online.healthcheck
```

通过 HTTPS 访问 `/health`，网易云与 QQ 组件应均为 `ready`。这是组件准备状态，不保证第三方平台当前可达。

## 镜像

```bash
docker build -t music-insight-online .
```

构建阶段下载固定网易云上游 commit，校验 SHA256，使用仓库中的 npm 锁文件和 `npm ci --omit=dev --ignore-scripts`。Python 依赖也在构建阶段安装。运行时不执行下载、npm install 或 pip install。每个同步 Job 启动独立的 loopback Node 辅助进程，避免跨用户缓存和登录态混用。

镜像为非 root；Compose 配置只读文件系统、清空 capabilities、禁止新增权限、进程和内存限制。临时凭据、缓存、导出与安全日志位于 `/tmp` 的 tmpfs，容器重建后消失。[Docker 官方 tmpfs 说明](https://docs.docker.com/engine/storage/tmpfs)指出宿主机 swap 可能保存内存页；若需要严格不落盘，部署者应关闭或加密 swap。

## 配置

- `MUSIC_INSIGHT_ENV=production`：要求 PUBLIC_URL 使用 HTTPS，Session Cookie 为 Secure / HttpOnly / SameSite=Strict。
- `MUSIC_INSIGHT_HOST=0.0.0.0`、`MUSIC_INSIGHT_PORT=8000`：仅用于容器内部；公网通过 TLS 反向代理进入。
- `MUSIC_INSIGHT_SECRET`：随机密钥用于限流身份 HMAC，不使用真实 IP 作为日志字段。
- `MUSIC_INSIGHT_SESSION_TTL=3600`、`MUSIC_INSIGHT_RESULT_TTL=3600`：允许 1–86400 秒。
- `MUSIC_INSIGHT_MAX_ACTIVE_JOBS=5`、`MUSIC_INSIGHT_MAX_SESSIONS=100`：任务和会话容量。
- `MUSIC_INSIGHT_NETEASE_API_DIR=/opt/netease-api`：预构建网易云组件。
- `MUSIC_INSIGHT_TEMP_ROOT=/tmp/music-insight`、`MUSIC_INSIGHT_LOG_DIR=/tmp/music-insight-logs`：临时数据与固定字段日志；不要做长期个人数据备份。

限流按连接来源与 Session 双重执行。默认不信任 `X-Forwarded-For`，避免伪造；反向代理后所有请求可能共用一个 IP 限额，应在边缘增加真实来源限流。不要开放辅助 Node 端口。

## 开发环境

```bash
python -m pip install -e ".[online,test]"
python scripts/prepare_online_api.py build/online-api
# 设置 MUSIC_INSIGHT_NETEASE_API_DIR 为 build/online-api 的绝对路径
python run_online.py
```

开发默认 `http://127.0.0.1:8000`，禁止开发模式绑定公网。网易云准备命令需要 Node/npm，且在使用前执行。QQ 不需要 Node。

## 托管选择与国内访问

面向中国大陆用户，优先选择可直连且音乐平台出站可用的 VPS，加自有 HTTPS 域名。资源和出站 IP 是否被音乐平台限制，应在目标服务器实测。这里没有保证任意运营商均可访问的承诺。

Railway、Render、Fly.io 的持续运行 Docker 服务可作为选项，使用一个实例且关闭自动扩容。Render 的免费服务会休眠并丢失临时文件，不适合需要稳定扫码会话的生产环境（[官方限制](https://render.com/docs/free)）。不推荐 Serverless 处理长同步任务。

GitHub 用于源码与 CI；[GitHub Pages 只提供静态托管](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)，不能运行本应用的 FastAPI/Node 后端。可选的 `browser/` JSON 导入预览不提供平台扫码，不能替代 Online Web。

## 清理与扩展

退出和 TTL 清理 Session-owned 目录；下载清单立即撤销。单实例 tmpfs 部署避免重启遗留文件。源码开发若异常终止进程，可能留下 OS 临时目录，应停服后清理 `music-insight-session-*`，不要在服务运行时删除目录。

v3 不支持多个 Worker/实例之间共享 Session。未来可以替换 SessionStore、JobQueue 和 StorageBackend，当前不依赖 Redis/S3。`WEB_CONCURRENCY` 必须为 1。反向代理及服务器应及时安装安全更新。
