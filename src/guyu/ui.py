"""Native local control panel. No cloud, account login or model invocation."""
from pathlib import Path
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from .core import Assistant, VERSION
from .commander_policy import CommanderPolicy
from .safety import atomic_json
from .preview import TextPreview, ImagePreview, BackupBrowser

class Panel(ttk.Frame):
    def __init__(self, root, home):
        super().__init__(root,padding=24)
        self.home = Path(home)
        self.app = Assistant(self.home,source='control-panel')
        self.root = root
        self.policy = CommanderPolicy(self.app)
        self.terminal_var = tk.StringVar()
        self.model_var = tk.StringVar()
        self.pack(fill='both',expand=True)
        self.columnconfigure(0,weight=1)
        self.rowconfigure(8,weight=1)
        self.status_var = tk.StringVar()
        ttk.Label(self,text='谷雨电脑助手',font=('Microsoft YaHei UI',22,'bold')).grid(row=0,column=0,sticky='w')
        ttk.Label(self,text=f'本地文件与版本管理版 0.5.0  ·  无云中转  ·  无付费 API',font=('Microsoft YaHei UI',10)).grid(row=1,column=0,sticky='w',pady=(4,18))
        state = ttk.LabelFrame(self,text='运行与连接状态',padding=14)
        state.grid(row=2,column=0,sticky='ew')
        ttk.Label(state,textvariable=self.status_var,font=('Microsoft YaHei UI',12,'bold')).pack(anchor='w')
        self.protocol_var = tk.StringVar()
        ttk.Label(state,textvariable=self.protocol_var).pack(anchor='w',pady=(8,3))
        ttk.Label(state,textvariable=self.model_var).pack(anchor='w')
        ttk.Label(state,textvariable=self.terminal_var).pack(anchor='w',pady=(3,0))
        ttk.Label(state,text='原生键鼠控制 / 浏览器自动化：未实现；当前仅对齐文件、搜索、文档和进程核心').pack(anchor='w',pady=(3,0))
        self._workspace_row()
        self._buttons()
        ttk.Label(self,text='27 个接口：文件 / 搜索 / 文档 / 进程 / 文本预览 / 版本恢复；PDF 生成未开放',font=('Microsoft YaHei UI',10)).grid(row=5,column=0,sticky='w',pady=(15,4))
        ttk.Label(self,text='暂停阻止后续操作，不撤销已完成的动作。文件白名单不是操作系统沙箱。',wraplength=790).grid(row=6,column=0,sticky='w',pady=(0,14))
        ttk.Label(self,text='最近操作记录',font=('Microsoft YaHei UI',12,'bold')).grid(row=7,column=0,sticky='w',pady=(0,7))
        self._events_table()
        ttk.Label(self,text='基于 Desktop Commander MIT 开源核心独立接入；项目、依赖、缓存与日志在本地项目目录。').grid(row=9,column=0,sticky='w',pady=(12,0))
        self.refresh()

    def _workspace_row(self):
        row = ttk.LabelFrame(self,text='当前授权的文件工作区',padding=12)
        row.grid(row=3,column=0,sticky='ew',pady=(14,0))
        self.workspace_var = tk.StringVar(value=str(self.home/'workspace'))
        ttk.Entry(row,textvariable=self.workspace_var,state='readonly',width=90).pack(fill='x')
        ttk.Label(row,text='新接口支持代码、文本、Excel、Word 等；所有文件工具仅限本工作区。').pack(anchor='w',pady=(6,0))

    def _buttons(self):
        box=ttk.Frame(self); box.grid(row=4,column=0,sticky='w',pady=(12,0))
        first=ttk.Frame(box); first.pack(anchor='w')
        actions=[('立即暂停',self.pause),('恢复工具',self.resume),('终端权限',self.configure_terminal),
            ('连接 GPT',self.open_connection),('打开工作区',self.open_workspace),('使用说明',self.open_guide),('刷新记录',self.refresh)]
        for title,action in actions:
            ttk.Button(first,text=title,command=lambda f=action:self.safe_action(f)).pack(side='left',padx=(0,8))
        second=ttk.Frame(box); second.pack(anchor='w',pady=(8,0))
        self.preview_button=ttk.Button(second,text='文件预览与编辑',command=lambda:self.safe_action(self.open_preview))
        self.preview_button.pack(side='left',padx=(0,8))
        self.backup_button=ttk.Button(second,text='备份与恢复',command=lambda:self.safe_action(self.open_backups))
        self.backup_button.pack(side='left',padx=(0,8))
        ttk.Label(second,text='仍仅开放原工作区；新增目录授权尚未完成。').pack(side='left')

    def _events_table(self):
        frame = ttk.Frame(self)
        frame.grid(row=8,column=0,sticky='nsew')
        columns = ('time','source','action','status')
        self.events = ttk.Treeview(frame,columns=columns,show='headings',height=10)
        for key,title,width in [('time','时间（UTC）',190),('source','来源',140),('action','动作',230),('status','结果',110)]:
            self.events.heading(key,text=title)
            self.events.column(key,width=width,minwidth=70)
        scroll = ttk.Scrollbar(frame,orient='vertical',command=self.events.yview)
        self.events.configure(yscrollcommand=scroll.set)
        self.events.pack(side='left',fill='both',expand=True)
        scroll.pack(side='right',fill='y')

    def safe_action(self,action):
        try:
            action()
        except Exception as exc:
            messagebox.showerror('操作未完成',str(exc),parent=self.root)

    def pause(self):
        self.app.pause()
        self.refresh()

    def resume(self):
        self.app.resume_local()
        self.refresh()

    def configure_terminal(self):
        enabled = self.policy.terminal_enabled()
        if not enabled:
            approved = messagebox.askyesno('开启终端权限',
                '开启后，GPT 可通过本地工具执行终端命令。\n终端拥有当前 Windows 账户权限，不受文件工作区白名单约束。\n请在客户端逐次审核写操作；不要授权陌生任务。\n现在明确开启吗？',parent=self.root)
            if not approved:
                return
        atomic_json(self.policy.control,{'version':1,'terminal_enabled':not enabled})
        self.app._event('terminal_permission_local','enabled' if not enabled else 'disabled')
        self.refresh()

    def open_preview(self):
        self.app._enabled()
        path=filedialog.askopenfilename(parent=self.root,title='选择工作区内的文本或图片',initialdir=str(self.app.workspace))
        if not path: return
        self.policy.path(path)
        window=tk.Toplevel(self.root); window.title('谷雨文件预览'); window.geometry('1000x760')
        try:
            cls=ImagePreview if Path(path).suffix.lower() in {'.png','.jpg','.jpeg','.bmp','.webp','.gif'} else TextPreview
            view=cls(window,self.app,self.policy,path)
            if isinstance(view,TextPreview): window.protocol('WM_DELETE_WINDOW',view.close_requested)
        except Exception:
            window.destroy(); raise

    def open_backups(self):
        self.app._enabled()
        window=tk.Toplevel(self.root); window.title('谷雨文件备份与恢复'); window.geometry('1000x650')
        try: BackupBrowser(window,self.app,self.policy)
        except Exception:
            window.destroy(); raise

    def open_connection(self):
        os.startfile(self.home/'CONNECT_CODEX.cmd')

    def open_workspace(self):
        os.startfile(self.home/'workspace')

    def open_guide(self):
        os.startfile(self.home/'START_HERE.txt')

    def refresh(self):
        try:
            model = json.loads((self.home/'evidence/model-read-report.json').read_text(encoding='utf-8')).get('result')
        except (OSError,ValueError,AttributeError):
            model = 'NOT_TESTED'
        state = {'MODEL_READ_E2E_VERIFIED':'只读已通过，写操作待验收',
            'BLOCKED_ACCOUNT_USAGE_LIMIT':'账号额度限制，未充值'}.get(model,'尚未完成')
        try:
            write_state=json.loads((self.home/'evidence/model-write-report.json').read_text(encoding='utf-8')).get('result')
        except (OSError,ValueError,AttributeError):
            write_state='NOT_TESTED'
        if write_state=='MODEL_FILE_E2E_VERIFIED': state='文件读写已通过；限本地客户端'
        elif write_state=='BLOCKED_CLIENT_APPROVAL_REQUIRED' and model=='MODEL_READ_E2E_VERIFIED': state='只读已通过，写入待本机确认'
        self.model_var.set('上次 GPT 模型验收：'+state+'    |    当前网页：未验证')
        self.terminal_var.set('终端：已开启；具有当前账户权限，不受文件白名单约束' if self.policy.terminal_enabled() else '终端：默认关闭；须在本机点击终端权限明确开启')
        self.status_var.set('已暂停：新文件、搜索和命令操作将被拦截' if self.app.status()['paused'] else '工具可用：文件仅限工作区；终端权限独立控制')
        report = self.home/'evidence/r04-protocol.json'
        try:
            passed = json.loads(report.read_text(encoding='utf-8')).get('result')=='R04_LOCAL_PROTOCOL_VERIFIED'
        except (OSError,ValueError,AttributeError):
            passed = False
        self.protocol_var.set('开源核心 MCP 协议自测：已通过（不消耗模型额度）' if passed else '开源核心 MCP 协议自测：暂无通过记录')
        for item in self.events.get_children():
            self.events.delete(item)
        for event in self.app.recent_events():
            self.events.insert('', 'end',values=tuple(event[key] for key in ('time','source','action','status')))


def main(home):
    root = tk.Tk()
    root.title('谷雨电脑助手 | 本地开发测试版')
    root.geometry('1080x800')
    root.minsize(940,690)
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.',font=('Microsoft YaHei UI',10))
    style.configure('Treeview',rowheight=28)
    panel = Panel(root,home)
    def close():
        panel.app.pause()
        root.destroy()
    def tick():
        panel.safe_action(panel.refresh)
        root.after(2000,tick)
    root.protocol('WM_DELETE_WINDOW',close)
    root.after(2000,tick)
    root.mainloop()
