"""Local text previews do not execute files or render active HTML."""
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from .versions import Versions

class TextPreview(ttk.Frame):
    def __init__(self,root,app,policy,path):
        super().__init__(root,padding=14)
        self.root=root; self.store=Versions(app,policy); self.path=str(path)
        self.info=self.store.read_text(self.path)
        self.pack(fill='both',expand=True)
        ttk.Label(self,text=self.path,wraplength=800).pack(anchor='w')
        ttk.Label(self,text='纯文本预览：不会执行脚本或 HTML；保存前核对文件并保留原版。').pack(anchor='w',pady=6)
        self.text=scrolledtext.ScrolledText(self,wrap='none',font=('Microsoft YaHei UI',11),undo=True)
        self.text.pack(fill='both',expand=True)
        self.text.insert('1.0',self.info['text'])
        row=ttk.Frame(self); row.pack(fill='x',pady=(10,0))
        ttk.Button(row,text='保存并备份',command=self.save_clicked).pack(side='left')
        ttk.Button(row,text='重新载入',command=self.reload_clicked).pack(side='left',padx=8)
        self.status=tk.StringVar(value='已读取；未保存修改。')
        ttk.Label(row,textvariable=self.status).pack(side='left',padx=12)
    def save(self):
        result=self.store.save_text(self.path,self.text.get('1.0','end-1c'),self.info['sha256'],uuid.uuid4().hex)
        self.info=self.store.read_text(self.path)
        self.status.set('保存完成，已保留修改前备份。')
        return result
    def is_dirty(self):
        return self.text.get('1.0','end-1c')!=self.info['text']
    def reload(self):
        self.info=self.store.read_text(self.path)
        self.text.delete('1.0','end'); self.text.insert('1.0',self.info['text'])
        self.status.set('已重新载入磁盘上的最新版本。')
    def reload_clicked(self):
        if self.is_dirty() and not messagebox.askyesno('丢弃未保存修改？','重新载入会丢弃此窗口中未保存的修改。',parent=self.root): return
        try: self.reload()
        except Exception as exc: messagebox.showerror('无法载入',str(exc),parent=self.root)
    def close_requested(self):
        if self.is_dirty() and not messagebox.askyesno('关闭预览？','还有未保存修改，仍然关闭吗？',parent=self.root): return
        self.root.destroy()

    def save_clicked(self):
        try: self.save()
        except Exception as exc: messagebox.showerror('未保存',str(exc),parent=self.root)

class ImagePreview(ttk.Frame):
    def __init__(self,root,app,policy,path):
        super().__init__(root,padding=14)
        from io import BytesIO
        from PIL import Image, ImageTk
        from .safety import AppError
        store=Versions(app,policy); app._enabled()
        p=store._path(path)
        if p.suffix.lower() not in {'.png','.jpg','.jpeg','.bmp','.webp','.gif'}:
            raise AppError('IMAGE_PREVIEW_UNSUPPORTED','Use a supported raster image.')
        data=store._bytes(p)
        with Image.open(BytesIO(data)) as image:
            if image.width*image.height>25000000: raise AppError('IMAGE_TOO_LARGE','Preview limit: 25 million pixels.')
            picture=image.convert('RGB'); picture.thumbnail((900,600))
        self.display_size=picture.size
        self.photo=ImageTk.PhotoImage(picture,master=root)
        self.pack(fill='both',expand=True)
        ttk.Label(self,text=str(p),wraplength=900).pack(anchor='w')
        ttk.Label(self,text='本地静态预览；动图仅显示第一帧。').pack(anchor='w',pady=8)
        ttk.Label(self,image=self.photo).pack(fill='both',expand=True)

class BackupBrowser(ttk.Frame):
    def __init__(self,root,app,policy):
        super().__init__(root,padding=14)
        self.root=root; self.store=Versions(app,policy)
        self.pack(fill='both',expand=True)
        ttk.Label(self,text='恢复前再次备份当前文件；只显示 0.5 版起登记的备份。').pack(anchor='w',pady=8)
        columns=('time','path','action','bytes')
        self.tree=ttk.Treeview(self,columns=columns,show='headings',height=15)
        for key,title,width in [('time','时间',170),('path','原文件',440),('action','操作',140),('bytes','字节',90)]:
            self.tree.heading(key,text=title); self.tree.column(key,width=width)
        self.tree.pack(fill='both',expand=True)
        row=ttk.Frame(self); row.pack(fill='x',pady=8)
        ttk.Button(row,text='恢复所选备份',command=self.restore_clicked).pack(side='left')
        ttk.Button(row,text='刷新',command=self.refresh).pack(side='left',padx=8)
        self.status=tk.StringVar(); ttk.Label(self,textvariable=self.status).pack(anchor='w')
        self.refresh()
    def refresh(self):
        report=self.store.list_backups()
        for key in self.tree.get_children(): self.tree.delete(key)
        for item in report['backups']:
            self.tree.insert('', 'end',iid=item['id'],values=[item[k] for k in ('time','path','action','bytes')])
        self.status.set(f"显示 {len(report['backups'])} 个备份；不可读取 {report['unreadable']} 个。")
    def restore_clicked(self):
        from .safety import digest
        selected=self.tree.selection()
        if not selected: return
        try:
            key=selected[0]; item,path,data=self.store._load(key)
            current=digest(self.store._bytes(path))
            if not messagebox.askyesno('确认恢复',f'将恢复此文件：\n{path}\n\n当前文件会先保留一份备份。确认继续？',parent=self.root): return
            self.store.restore(key,current,uuid.uuid4().hex)
            self.refresh(); self.status.set('恢复完成；恢复前版本也已保留。')
        except Exception as exc: messagebox.showerror('未恢复',str(exc),parent=self.root)
