# 下载与安全

请仅从本项目的 [GitHub Releases](https://github.com/rhr-jz/netease-music-insight/releases) 获取 Windows 文件。Release 中的 `SHA256SUMS.txt` 可用于核对下载文件是否与发布文件一致；哈希一致只证明文件未在传输中变化，不代表安全认证。

本项目的 v1.0.0 初始单文件 EXE 曾被 Microsoft Defender 检测为 `Trojan:Win32/Sabsik.FL.A!ml`。我们重新在干净的 Python 环境中构建、扫描，并从 GitHub 下载核验后替换了该附件，同时提供目录版 ZIP。不同设备和安全软件的判断可能不同。

v1.1.0 起只发布完整目录版 ZIP，关闭 UPX 压缩。解压后运行其中的 EXE，勿单独移动 EXE。此调整可减少单文件自解压打包形式带来的误报，但无法保证任何安全软件均不拦截。

**如果浏览器或杀毒软件仍提示病毒，请不要关闭防护、添加排除项或强行运行。** 可以使用仓库的源码版 `一键运行.bat`，并在 Issue 中说明浏览器、安全软件、检测名称和文件 SHA-256。请勿上传 Cookie、UID 或私人导出文件。

本项目的 EXE 尚未进行商业代码签名。Windows 对未签名的新程序可能显示额外信誉警告；这与具体恶意软件检测是两回事。长期解决方式包括代码签名，以及将误检样本提交给安全厂商复核。微软提供[软件开发者样本提交通道](https://www.microsoft.com/wdsi/filesubmission)，提交需要 Microsoft 账号。
