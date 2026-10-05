# Music Insight 3.0 RC1 完整本地运行包

为朋友分发时，下载对应系统的 ZIP，解压整个文件夹后打开主程序。无需安装 Python、Node 或 npm，网易云运行组件和生产依赖已包含在包内。

- Windows：`MusicInsight-Windows-x64-3.0.0rc1.zip`，Windows 10/11 x64。Windows 11 ARM 使用系统 x64 兼容层，额外经过该系统的组件与本地网页启动检查。
- Mac Intel：`MusicInsight-macOS-Intel-3.0.0rc1.zip`，原生 Intel 应用。
- Mac M 系列：`MusicInsight-macOS-AppleSilicon-3.0.0rc1.zip`，原生 Apple Silicon 应用。
- Mac 建议 macOS 14 或更新；本次分别在 macOS 14 Apple Silicon 和 macOS 15 Intel 构建并验证。32 位系统和更早的操作系统不在支持范围。

## 保留的功能

网易云、QQ、两个平台联合整理，应用内二维码登录、取消与进度、音乐 Dashboard、分页歌曲/歌单/记录浏览与搜索、13 个根据实际数据动态显示的 AI Prompt、复制与导出、离线档案浏览和 Local Web。没有音乐播放、音源下载或收费 AI API 接入。

默认双击打开桌面界面；也可以使用包中的 `Open Local Web` 入口在系统浏览器打开相同的本地界面。Windows 桌面使用系统 Edge WebView2，缺少该组件时自动回退到浏览器。Local Web 只监听 127.0.0.1。公网部署服务器另见部署文档，不需要朋友自行部署。

## 本次验证与限制

77 项自动化测试通过；Windows、Intel Mac、Apple Silicon 分别真实构建运行包；清空 PATH 后检查桌面资源、CLI、本地网页和自带网易云组件的二维码图片生成。Mac 另外验证实际 WebKit 窗口和中文系统剪贴板。Windows 11 ARM 验证 x64 兼容运行。

真实账号扫码确认需要用户手机参与。已有用户曾确认网易云和 QQ 均可导出；本次没有把自动化 Mock 测试描述成所有真实账号、所有网络的导出保证。同步需要网络，接口可用性受音乐平台影响；网易云播放记录范围有限，QQ 缺少可靠完整播放历史。

## 数据与安全

音乐数据、凭据、缓存和日志保存到当前用户的本机目录，不发送到作者服务器。应用包不包含私人导出和登录凭据。转发原始 ZIP，不要把自己的用户数据目录一起打包。已生成的档案和 Prompt 可离线浏览；数据输出目录可在设置中修改。

本版本未使用付费开发者签名或 Apple 公证，首次打开可能需要系统提供的安全确认。不要关闭防护；若检测到具体恶意软件请停止运行并提供检测名称。发布包提供 SHA256 校验文件，保留 GPL/MIT、Node 和第三方许可。

包使用系统 WebView，未捆绑 Electron、Chromium、npm、测试和开发依赖；也移除了无关的 API 演示图片和 AVIF 编解码器，以减小体积。
