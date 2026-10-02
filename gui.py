"""Launch the local window; startup errors stay in the E-drive project."""
from pathlib import Path
import sys
import traceback
ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
if __name__=='__main__':
    try:
        from guyu.core import init_home
        init_home(ROOT)
        from guyu.ui import main
        main(ROOT)
    except Exception:
        (ROOT/'logs').mkdir(exist_ok=True)
        (ROOT/'logs/ui-error.log').write_text(traceback.format_exc(),encoding='utf-8')
        from tkinter import messagebox
        messagebox.showerror('谷雨电脑助手启动失败','请查看项目 logs/ui-error.log。没有改动现有项目。')
        raise
