# Music Insight 1.3.0

接受社区 macOS 兼容性贡献：新增可双击的 `一键运行.command` 源码入口，自动准备 Python 环境，并用系统默认应用打开登录二维码和结果文件夹。仅导出 QQ 音乐无需 Node.js；macOS / Linux 导出网易云需要 Node.js 18+。

将系统文件打开操作统一放入 `platform_utils.py`，支持 Windows、macOS 与 Linux。跨系统测试扩展到三种操作系统，并新增系统打开和 Node.js 版本检查测试。保留 v1.2.0 的新手界面与模块化 AI 分析指南。

Windows 继续发布目录版 ZIP。若安全软件拦截，请勿关闭防护，提交拦截详情。许可与第三方声明见 LICENSE 与 THIRD_PARTY_LICENSES.md。
