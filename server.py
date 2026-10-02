"""Local MCP entry point. Uses stdio only; no HTTP server or model API."""
import argparse
from pathlib import Path
import sys
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from guyu.core import Assistant
parser = argparse.ArgumentParser()
parser.add_argument('--home',type=Path,default=ROOT)
args = parser.parse_args()
app = Assistant(args.home,source='mcp')
mcp = FastMCP('Guyu Local Assistant',instructions='Local workspace-only file tools. Read files before editing. Never claim desktop or web connectivity. Reuse request IDs only for identical retries. If a result is unknown, inspect it instead of retrying.',log_level='WARNING')
READ = ToolAnnotations(readOnlyHint=True,destructiveHint=False,idempotentHint=True,openWorldHint=False)
WRITE = ToolAnnotations(readOnlyHint=False,destructiveHint=False,idempotentHint=True,openWorldHint=False)
EDIT = ToolAnnotations(readOnlyHint=False,destructiveHint=True,idempotentHint=True,openWorldHint=False)

@mcp.tool(annotations=READ)
def device_status() -> dict:
    """查看本地状态；不代表 GPT 或网页已经接通。"""
    app._event('device_status','succeeded')
    return app.status()

@mcp.tool(annotations=READ)
def list_files(path: str='.') -> dict:
    """列出工作区指定相对目录，最多200项；不会扫描整块磁盘。"""
    return app.list_files(path)

@mcp.tool(annotations=READ)
def search_files(query: str) -> dict:
    """按名称搜索工作区顶层文件，不递归；截断时明确提示。"""
    return app.search_files(query)

@mcp.tool(annotations=READ)
def read_text(path: str) -> dict:
    """读取相对路径文本并返回SHA256，单文件最大256KiB。"""
    return app.read_text(path)

@mcp.tool(annotations=WRITE)
def create_text(path: str, text: str, request_id: str) -> dict:
    """新建文本；拒绝覆盖。request_id须6-80位字母、数字、下划线或连字符。"""
    return app.create_text(path,text,request_id)

@mcp.tool(annotations=EDIT)
def replace_text(path: str, text: str, expected_sha256: str, request_id: str) -> dict:
    """仅当原文件SHA256匹配时替换文本，先备份；路径仅限工作区。"""
    return app.replace_text(path,text,expected_sha256,request_id)

@mcp.tool(annotations=READ)
def get_job(request_id: str) -> dict:
    """查询写操作实际记录，结果未知时不要盲目重试。"""
    return app.get_job(request_id)

@mcp.tool(annotations=WRITE)
def pause_session() -> dict:
    """暂停后续操作；恢复只能在本机控制台进行，不能撤销已完成操作。"""
    return app.pause()

if __name__=='__main__':
    mcp.run(transport='stdio')
