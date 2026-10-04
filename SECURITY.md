# 下载与安全

请仅从本项目的 [GitHub Releases](https://github.com/rhr-jz/netease-music-insight/releases) 获取 Windows 文件。Release 中的 `SHA256SUMS.txt` 可用于核对下载文件是否与发布文件一致；哈希一致只证明文件未在传输中变化，不代表安全认证。

本项目的 v1.0.0 初始单文件 EXE 曾被 Microsoft Defender 检测为 `Trojan:Win32/Sabsik.FL.A!ml`。我们重新在干净的 Python 环境中构建、扫描，并从 GitHub 下载核验后替换了该附件，同时提供目录版 ZIP。不同设备和安全软件的判断可能不同。

v1.1.0 起只发布完整目录版 ZIP，关闭 UPX 压缩。解压后运行其中的 EXE，勿单独移动 EXE。此调整可减少单文件自解压打包形式带来的误报，但无法保证任何安全软件均不拦截。

**如果浏览器或杀毒软件仍提示病毒，请不要关闭防护、添加排除项或强行运行。** 可以使用仓库的源码版 `一键运行.bat`，并在 Issue 中说明浏览器、安全软件、检测名称和文件 SHA-256。请勿上传 Cookie、UID 或私人导出文件。

本项目的 EXE 尚未进行商业代码签名。Windows 对未签名的新程序可能显示额外信誉警告；这与具体恶意软件检测是两回事。长期解决方式包括代码签名，以及将误检样本提交给安全厂商复核。微软提供[软件开发者样本提交通道](https://www.microsoft.com/wdsi/filesubmission)，提交需要 Microsoft 账号。


## Online Web v3

生产环境要求 HTTPS；使用 HttpOnly / Secure / SameSite=Strict Session Cookie。平台 Cookie 和 CSRF secret 不提供给浏览器 JavaScript。写操作须精确同源 Origin、自定义请求头，且不配置跨域 CORS。Host 必须与 PUBLIC_URL 一致。禁止 iframe 嵌入；响应 no-store，脚本仅允许同源资源，动态布局样式使用每次响应的 nonce，无 unsafe-inline 脚本。

公网接口使用严格输入模型、16 KiB 请求体上限、双重限流、最大会话与 Job 容量。下载采用 Session-owned manifest 的随机 ID，禁止任意 path 下载。Worker、平台缓存和 Node 辅助进程按 Session/Job 隔离。日志只记录固定阶段和错误类别，关闭 HTTP 访问日志和第三方异常日志。部署者也应关闭反向代理敏感访问日志。

退出立即撤销凭据和下载访问，协作取消完成后删除临时目录。已经发给浏览器或用户下载的字节无法撤回。TTL 默认最多一小时；单实例容器使用 tmpfs，重启不恢复账号。

防护并不保证第三方接口永远稳定，也不替代部署者的系统维护。仅部署一个实例、一个 Worker；不要直接向公网开放 Local Web 或辅助 Node 服务。[部署安全说明](docs/DEPLOYMENT.md)。安全问题通过仓库安全报告渠道提交，避免附带真实凭据或导出数据。
