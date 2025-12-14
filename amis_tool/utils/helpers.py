import tkinter as tk

def center_window(window):
    """Center window on screen"""
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"+{x}+{y}")

class CenteredToplevel(tk.Toplevel):
    """Base class for centered dialog windows"""
    def __init__(self, master=None, title="", width=400, height=200):
        super().__init__(master)
        self.title(title)
        self.geometry(f"{width}x{height}")
        if master:
            self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        center_window(self)