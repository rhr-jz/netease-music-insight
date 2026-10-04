# Music Insight 浏览器预览

这是可部署到静态托管的浏览器版本。当前尚未发布公网网址。

## 当前能做什么

- 打开桌面版或 Local Web 已导出的网易云、QQ 音乐 JSON。
- 同时读取两个平台的数据，通过原有 Core 生成 Combined 联合数据。
- 查看收藏、歌曲、歌手、专辑、歌单规模、时间字段覆盖情况和平台对比。
- 搜索歌曲、歌手和专辑，每页显示最多 40 首歌曲。
- 浏览、复制 12 个独立 AI Prompt；两个平台都有数据时增加跨平台分析。
- 下载 JSON、Markdown 摘要、AI 使用指南，以及包含 Prompt 的 ZIP。
- 切换深浅主题，使用手机、平板和桌面布局。
- 资源缓存完成后，断网重新打开网页和本地 JSON，继续分析、复制及导出。

**当前不支持在公网网页扫码登录或重新获取平台数据。** 首次获取数据仍需桌面版或 Local Web。此预览不能称为“全部功能已迁移”。

## 与 Local Web 的区别

Local Web 由本机 Python 后端调用 Provider，提供扫码和采集功能。
此预览无需安装 Python；Pyodide 在浏览器 Worker 中执行原有 Python Core。
界面只调用浏览器适配层，统计、联合匹配、Prompt 和导出仍复用 `report.py`、`combined.py`、`guidance.py` 和 `desktop/library.py`。
站点不提供远程 Provider 代理，不运行登录后端。

GitHub Pages 是静态托管，无法运行现有 Python/Node 登录服务。
浏览器还限制跨域响应访问和 Cookie 请求头，不能直接照搬 Provider 的服务器请求。
如果将来引入远程后端，需要另外评审凭证传输、服务端处理、日志和用户同意；不能宣称这仍是同一种零上传架构。

## 隐私边界

- 文件通过浏览器 File API 进入当前标签页内存，计算在 Web Worker 中完成。
- 应用没有文件上传接口、广告、访问统计、远程图片或第三方运行时 CDN。
- 不使用 LocalStorage、IndexedDB 保存音乐数据或登录凭证。
- Service Worker 只缓存构建清单中的程序文件、许可和合成演示数据，不缓存导入文件或导出内容。
- 关闭或刷新页面后需要重新选择 JSON；“清空数据”清除当前会话引用，不删除用户原文件或已下载文件。
- 用户自行将文件交给外部 AI 时，适用该 AI 服务的隐私规则。
- GitHub Pages 会为安全目的记录访客 IP。因此准确表述是“本应用不收集音乐文件及登录凭证”，不能承诺托管商完全没有访问记录。

站点资源全部来自同一部署地址，但 GitHub 域名在中国大陆各网络的可达性仍需实际验证，不能保证始终免代理访问。
国内稳定入口需要另行确定可用的域名和静态托管账号；仅更换前端代码不能解决网络可达性。

参考：[GitHub Pages 与访问记录](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)、[浏览器禁止设置的请求头](https://developer.mozilla.org/en-US/docs/Glossary/Forbidden_request_header)。

## 本地构建

在仓库根目录执行，Python 3.10+ 即可构建，不需要安装桌面 GUI 依赖：

```bash
python scripts/build_browser.py
python -m http.server 8765 --bind 127.0.0.1 --directory _site
```

在浏览器打开 `http://127.0.0.1:8765/`。不要直接双击 HTML：Worker、Clipboard 和离线缓存需要 HTTP localhost 或 HTTPS。

构建首次下载固定版本的 Pyodide，校验 SHA256；缓存位于 `build/browser/`。
输出 `_site/` 只包含明确列出的界面、运行时、Core 和合成数据，不遍历复制工作树中的输出、缓存或凭证。
构建目录约 14 MB，首次加载后支持离线；首次访问仍然需要联网下载资源。

## 验证

```bash
python -m unittest discover -s tests -v
npm ci --prefix browser --ignore-scripts --no-audit --no-fund
cd browser
npx playwright install chromium
npm test
```

Windows 可使用已安装的 Edge，无需下载 Chromium。在仓库根目录执行：

```powershell
$env:MUSIC_BROWSER_CHANNEL = 'msedge'
node browser/tests/smoke.mjs
```

测试自动启动仅绑定回环地址的静态服务器，按 GitHub Pages 项目子目录运行，使用合成数据。
覆盖所有 Prompt 及真实 Clipboard API、导出、无数据/无效文件、HTML 注入防护、12,000 首歌曲搜索分页、离线重开、响应式布局和网络请求检查。
截图写入忽略的 `build/browser/screenshots/`。

当前本机验证：58 项 Python 测试通过，Edge 的 13 组浏览器检查通过。
这不表示已验证公网部署、国内多网络访问或公网扫码登录。

## 发布准备

`.github/workflows/browser.yml` 是手动构建与测试工作流，只上传静态站点构件，不执行部署。
确定公开版本范围后，可将生成的 `_site/` 发布到 GitHub Pages 或其他 HTTPS 静态托管。
应仅发布这个构建目录，不发布仓库根目录。无需配置远程数据库或音乐平台密钥。
上线后还必须验证真实网址、项目子路径、MIME 类型、离线更新和目标地区网络可达性。
