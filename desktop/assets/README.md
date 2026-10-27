# 应用图标

来源：用户于2026-10-27在本对话提供的机器人图片，明确授权用于本应用图标。原图保存在youdu.png，未重绘、未裁剪或去背景。

youdu.ico由原图等比缩放为16/24/32/48/64/128/256像素PNG帧组成，供Windows和Qt使用。转换使用现有PySide6的QImage平滑缩放和标准ICO目录，没有新增运行依赖。悬浮AI球仍使用orb.py绘制。

启动时QApplication设置窗口图标，Windows进程设置Youdu.BankAgent.Desktop身份，避免归入通用Python程序。scripts/create-desktop-shortcut.ps1生成含本机绝对路径的Youdu.lnk（Git忽略）；移动仓库或重新创建虚拟环境后应重新生成，不修改系统Python文件关联，也不是打包exe。
