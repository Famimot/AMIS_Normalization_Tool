"""
AMIS Tool v6.0 - Classical AMIS Only
With splash screen and two buttons (Classic Mode + Batch Processing)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys


def show_splash():
    """Splash screen for 1.5 seconds"""
    splash = tk.Tk()
    splash.overrideredirect(True)
    splash.geometry("600x385")

    # Dark background
    bg_frame = tk.Frame(splash, bg='#2c3e50')
    bg_frame.pack(fill=tk.BOTH, expand=True)

    # Title
    tk.Label(bg_frame, text="AMIS Tool",
            font=("Arial", 32, "bold"),
            fg="white", bg='#2c3e50').pack(pady=(60, 10))

    # Subtitle
    tk.Label(bg_frame,
            text="Normalization & Mapping\nfor heterogeneous data",
            font=("Arial", 14),
            fg="#3498db", bg='#2c3e50',
            justify="center").pack(pady=5)

    # Version
    tk.Label(bg_frame, text="Version 6.0",
            font=("Arial", 12),
            fg="white", bg='#2c3e50').pack(pady=5)

    # Separator
    tk.Frame(bg_frame, height=2, bg='#3498db').pack(fill='x', padx=100, pady=20)

    # Author
    author_info = """Author: Kravtsov G.
Research Center "Applied Statistics"
E-mail: 62abc@mail.ru"""

    tk.Label(bg_frame, text=author_info,
            font=("Arial", 11),
            fg="white", bg='#2c3e50',
            justify="center").pack(pady=20)

    # Loading text
    tk.Label(bg_frame, text="Loading program...",
            font=("Arial", 10),
            fg="yellow", bg='#2c3e50').pack(pady=20)

    # Center window
    splash.update_idletasks()
    width = splash.winfo_width()
    height = splash.winfo_height()
    x = (splash.winfo_screenwidth() // 2) - (width // 2)
    y = (splash.winfo_screenheight() // 2) - (height // 2)
    splash.geometry(f"+{x}+{y}")

    # Show for 1.5 seconds, then close
    splash.after(1500, splash.destroy)
    splash.mainloop()


def show_main_menu():
    """Main menu - immediate centering"""
    root = tk.Tk()
    root.title("AMIS Tool")

    # Set size and position
    width, height = 500, 430
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2

    root.geometry(f"{width}x{height}+{x}+{y}")

    # Main frame
    main_frame = ttk.Frame(root, padding="30")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Title
    ttk.Label(main_frame, text="AMIS NORMALIZATION TOOL",
             font=('Arial', 16, 'bold')).pack(pady=(0, 20))

    # Mode selection
    ttk.Label(main_frame, text="Select working mode:",
              font=('Arial', 12)).pack(pady=(0, 20))

    # Button 1: Classic mode (compare two datasets)
    btn1 = ttk.Button(main_frame,
                      text="📊 COMPARE TWO DATASETS",
                      command=lambda: launch_classic(root),
                      width=30)
    btn1.pack(pady=10)

    desc1 = ttk.Label(main_frame,
                      text="• Load 2 files (Excel/CSV)\n"
                           "• All 5 AMIS models\n"
                           "• Interactive graphs\n"
                           "• Comparison tables",
                      font=('Arial', 9),
                      justify=tk.LEFT)
    desc1.pack(pady=(0, 20))

    # Button 2: Batch mode (process multiple files)
    btn2 = ttk.Button(main_frame,
                      text="📦 BATCH PROCESSING",
                      command=lambda: launch_batch(root),
                      width=30)
    btn2.pack(pady=10)

    desc2 = ttk.Label(main_frame,
                      text="• Process multiple files\n"
                           "• 17-point AMIS model\n"
                           "• Combined table 0-100 AMIS\n"
                           "• Export to Excel",
                      font=('Arial', 9),
                      justify=tk.LEFT)
    desc2.pack(pady=(0, 30))

    # Exit button
    ttk.Button(main_frame, text="🚪 EXIT",
               command=root.quit).pack(pady=10)

    root.mainloop()


def launch_classic(parent):
    """Launch classic mode (compare two datasets)"""
    parent.destroy()
    try:
        from amis_tool.gui.main_window import AMISApp
        app = AMISApp()
        app.mainloop()
    except ImportError as e:
        messagebox.showerror("Error", f"Cannot launch classic mode:\n{str(e)}")


def launch_batch(parent):
    """Launch batch processing mode"""
    parent.destroy()
    try:
        from amis_tool.gui.batch_window import BatchAMISApp
        app = BatchAMISApp()
        app.mainloop()
    except ImportError as e:
        messagebox.showerror("Error", f"Cannot launch batch mode:\n{str(e)}")


def main():
    """Entry point for the 'amis' command (used by setup.py entry_points)"""
    show_splash()
    show_main_menu()


# Main function
if __name__ == "__main__":
    main()