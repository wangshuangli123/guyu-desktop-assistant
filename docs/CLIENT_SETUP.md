# 本地 MCP 客户端接入

先完成 README 的源码安装和本地复测，再运行 START.cmd。
程序只开放项目内的 workspace；控制窗口可暂停/恢复。关闭控制窗口会暂停后续操作。

## 已有 Codex Windows 应用

自行通过官方方式安装、登录后运行 CONNECT_CODEX.cmd。
这个入口仅识别 LOCALAPPDATA/OpenAI/Codex/bin 下的既有 Codex 应用，不自动安装或登录。
保留写工具人工审批与原生命令只读沙箱，不修改全局配置。
遇到登录、地区、额度、审批、联网问题时停止，不要求升级或换成付费 API。

## 其他 stdio MCP 客户端

将下面 YOUR_PROJECT 替换为本机项目完整路径；这是示例，不是已安装配置：

```json
{"mcpServers":{"guyu_local":{
  "command":"YOUR_PROJECT/runtime/venv/Scripts/python.exe",
  "args":["-B","YOUR_PROJECT/commander_server.py"],
  "env":{"PYTHONUTF8":"1","PYTHONDONTWRITEBYTECODE":"1"}
}}}
```

目录路径应使用客户端支持的格式；Windows JSON 路径可用正斜杠。
首次只调用 device_status，检查 workspace、暂停状态和终端是否关闭。
用新建测试文件完成读写验收，不要直接使用重要原件。每次批准前核对路径和实际操作。
此路径使用本机 stdio 管道，无需搭建公网服务器；并不使 ChatGPT 网页自动接通。
模型账号、供应商可用地区和使用额度由用户自行确认。

官方参考：https://developers.openai.com/codex/mcp
