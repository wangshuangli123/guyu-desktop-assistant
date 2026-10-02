"""Additional MCP tools for verified versioned text editing."""
from mcp import types
from .versions import Versions

NAMES={'preview_text','save_text_with_backup','list_backups','restore_backup'}

def tool_definitions():
    string={'type':'string'}
    definitions=[
        ('preview_text','读取授权工作区文本及 SHA256，供安全编辑和恢复时核对。',{'path':string},True),
        ('save_text_with_backup','核对原文件 SHA256 后保存文本并记录可恢复备份。',
            {'path':string,'text':string,'expected_sha256':string,'request_id':string},False),
        ('list_backups','列出本项目新记录的文件备份；旧版无索引备份不在此列表。',{},True),
        ('restore_backup','恢复指定备份；必须提供当前文件 SHA256，并再次备份当前版。',
            {'backup_id':string,'expected_sha256':string,'request_id':string},False)]
    return [types.Tool(name=name,description=description,
        inputSchema={'type':'object','properties':properties,'required':list(properties),'additionalProperties':False},
        annotations=types.ToolAnnotations(readOnlyHint=read,destructiveHint=not read,idempotentHint=True,openWorldHint=False))
        for name,description,properties,read in definitions]

class LocalExtensions:
    def __init__(self,app,policy): self.versions=Versions(app,policy)
    def call(self,name,args):
        if name=='preview_text': return self.versions.read_text(args['path'])
        if name=='list_backups': return self.versions.list_backups()
        if name=='save_text_with_backup': return self.versions.save_text(args['path'],args['text'],args['expected_sha256'],args['request_id'])
        if name=='restore_backup': return self.versions.restore(args['backup_id'],args['expected_sha256'],args['request_id'])
        raise ValueError('Unknown local extension')
