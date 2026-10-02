# 第三方组件

本项目并非完全从零重写。Desktop Commander 是独立安装的上游执行引擎，版本固定为 0.2.50。

- 软件包：@wonderwhy-er/desktop-commander
- 上游：https://github.com/wonderwhy-er/DesktopCommanderMCP
- 上游顶层许可证：MIT
- Copyright (c) 2024-2025 Eduard Ruzga and Desktop Commander Contributors
- 完整文本：licenses/DesktopCommander-MIT.txt

原版运行包、登录程序、字体、模型、用户工作区与任何客户数据不包含在本仓库。
依赖由用户从公共注册表安装，Node 依赖有完整固定版本与完整性信息；Python 版本固定在 requirements.lock.txt。
本次保留原验证环境的 Python 依赖，其中 PDF 相关包存在不等于 PDF 功能已开放。
不同直接/传递依赖可能使用不同许可，不统一称作 MIT；安装后的各发行包保留其原始许可。
对全部依赖的完整商业发行合规审查和安全审计尚未完成，不将本预览视为认证安装包。

新增代码由本项目作者控制，尚未选择通用对外许可证，见 RIGHTS.md。
开源组件的原许可及 GitHub 平台规定的权利不因本项目说明而被削减。
请勿仿冒上游品牌、官方服务或声称存在官方授权合作。
