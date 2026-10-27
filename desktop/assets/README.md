# 应用图标

来源：用户于2026-10-27在本对话提供的机器人图片，明确授权用于本应用图标。原图保存在youdu.png，未重绘、未裁剪或去背景。

youdu-app.ico由原图等比缩放为16/24/32/48/64/128/256像素帧组成（小尺寸为Windows原生DIB，256像素为PNG），供Windows和Qt使用。转换使用现有PySide6的QImage平滑缩放和标准ICO目录，没有新增运行依赖。悬浮AI球仍使用orb.py绘制。

启动时QApplication设置窗口图标，Windows进程设置Youdu.BankAgent.Desktop身份，避免归入通用Python程序。scripts/create-desktop-shortcut.ps1生成含本机绝对路径的Youdu.lnk（Git忽略）；移动仓库或重新创建虚拟环境后应重新生成，不修改系统Python文件关联，也不是打包exe。

## 资源管理器兼容入口

本机.lnk文件列表仍空白，而图标选择器能显示机器人；重建图标缓存的自动操作被策略阻止，用户手动重启Explorer后仍未恢复。因此提供Youdu.exe直接入口，由desktop/Launcher.cs和scripts/build-desktop-launcher.ps1生成，内嵌同一ICO。exe为本机构建产物，不提交Git；它按自身目录查找.venv/Scripts/pythonw.exe和desktop/app.py，继承配置、设置项目工作目录且不显示控制台。缺少环境时显示明确错误；不读取或改写账本。

2026-10-27实际Windows资源管理器验证：Youdu.exe显示蓝色机器人，旁边旧Youdu.lnk仍是空白。启动器专项用真实pythonw与探针app.py验证含空格路径、唯一脚本参数、工作目录和BANKAGENT_DB_PATH继承；不是实际银行窗口点击。首次以C#临时替身编译探针时遇到写文件拒绝，未计为通过；改用真实Python验证启动路径成功。银行实际main入口沿用现有启动重开回归，HTTP smoke通过。本轮不再重复真实模型验收。
