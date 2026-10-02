# 谷雨电脑助手 · Guyu Desktop Assistant

Windows 本地 MCP 文件助手，带中文控制窗口、操作暂停、文本预览及版本备份。

**发布候选：0.5.0 开发预览版。不是完整桌面遥控产品，不是可直接商用的独立 EXE。**
本项目在 Desktop Commander 0.2.50 开源核心外增加本地协调、权限检查和中文界面；不是官方分支或官方服务。

## 已实现范围

| 模块 | 当前能力 |
|---|---|
| 文件 | 工作区内读取、写入、批量读取、创建目录、移动和局部修改 |
| 搜索 | 文件名及内容搜索、分批获取结果、停止搜索 |
| 版本 | 修改前备份、SHA256 并发检查、恢复前保留当前版本 |
| 界面 | 中文状态、文本/图片预览、备份列表、暂停和恢复 |
| 文档 | 基础 Word/Excel 读写用例；不保证任意复杂格式无损 |
| 进程 | 本地开启后执行任务与读取输出；默认关闭终端 |

尚未实现：原生键鼠、浏览器自动化、任意额外目录授权、PDF 生成、ChatGPT 网页直连、云端设备中转。
**文件工具的目录限制不是操作系统沙箱。开启终端后，命令拥有当前账户的权限。**

## 适合谁

适合愿意审阅源码、安装依赖、用资料副本测试的 Windows 用户与开发者。
当前不适合无人值守、生产财务数据、密码库、硬件烧录或对重要原件直接批量操作。
先用虚构数据验证，再决定是否在自己的场景采用。

## 环境

Windows 11 x64；已验证开发环境为 Python 3.14 与 Node.js 24。
本项目不分发 Python、Node、Codex、模型账号或系统字体。

## 从源码安装

先自行安装带 Tkinter 的 Python 3.14 和 Node.js 24，再在项目目录执行：

```powershell
py -3.14 -m venv runtime/venv
$env:PIP_CACHE_DIR = "$PWD/cache/pip"
$env:PUPPETEER_SKIP_DOWNLOAD = 'true'
$env:DESKTOP_COMMANDER_DISABLE_TELEMETRY = '1'
./runtime/venv/Scripts/python.exe -B scripts/prepare_lock.py
./runtime/venv/Scripts/python.exe -m pip install --only-binary=:all: -r requirements.lock.txt
npm ci --prefix vendor/desktop-commander --ignore-scripts --no-audit --no-fund --cache ./cache/npm
./runtime/venv/Scripts/python.exe -B tests/run_all.py
```

Node 锁文件以 gzip 原样保存；prepare_lock.py 校验 SHA256 后在本机还原标准 package-lock.json，不下载或执行代码。
依赖从 PyPI/npm 下载，网络下载不是模型调用。`--ignore-scripts` 避免执行依赖安装脚本；不要直接运行上游 remote/install 入口。
不要复制另一台电脑的虚拟环境。不要放在需要管理员权限的系统目录，不要求关闭杀毒软件。
如果依赖安装或测试失败，先停止，不降低权限来强行继续。
测试通过后双击 `START.cmd`。默认文件工作区是项目目录内的 `workspace`，测试必须使用副本。

## 连接本地模型客户端

模型服务与本程序是不同产品。需要使用自己有权限的账号、地区和额度；不包含无限模型服务。
本地控制不需要我们自己的云服务器，但使用云模型时，授权返回的文件片段会传给所用模型服务。
现有 `CONNECT_CODEX.cmd` 面向已安装官方 Windows Codex 应用且自行登录的用户；会保留人工写入审批。
其他支持 stdio MCP 的客户端可按 `docs/CLIENT_SETUP.md` 手动接入。
本项目不读取或上传账号凭据，不修改用户全局 MCP 配置。请不要将账号文件复制进本仓库。
**当前浏览器里的普通 ChatGPT 对话不会因为运行本程序就自动获得控制权。**

## 验证与反馈

验证范围与已知不足见 `docs/VALIDATION.md`，权限和数据说明见 `SECURITY.md`。
请先提交不含真实业务数据的复现步骤；不要在公开 Issue 中附带密钥、浏览器会话、完整日志或客户文件。
对定制流程的需求，可以用 Issue 描述任务、样例类型、期望结果和使用环境；不要直接提供私密材料。
本预览版不承诺服务期限、终身维护或任意格式无损处理；尚未推出收费成品。

## 第三方与权利

上游 Desktop Commander 使用 MIT 许可，完整文本见 `licenses/DesktopCommander-MIT.txt`。
本仓库只公开本项目选定源码与依赖清单，不打包第三方二进制、字体或用户运行数据。
本项目新增代码的对外许可证尚未由作者指定；**不要将本仓库整体称为 MIT 或已经开放商业再分发权**。
详见 `RIGHTS.md` 与 `THIRD_PARTY_NOTICES.md`。当前安装说明面向作者及已取得授权的测试者。

## English summary

A Windows-only, local stdio MCP file-workflow preview with a Chinese control panel,
optimistic-concurrency checks and versioned backups. Built around the separately installed
Desktop Commander 0.2.50 engine. No hosted relay or model subscription is provided.
This is not a full desktop/browser-control product, security sandbox or standalone installer.
Public source preview; licensing of original additions is pending the author's choice.
