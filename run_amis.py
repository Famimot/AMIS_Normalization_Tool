"""
AMIS Normalization Tool v.4.3.0
WITH SIMPLE SPLASH SCREEN

Author: Kravtsov G.
Research Center "Applied Statistics"
E-mail: 62abc@mail.ru
"""

import sys
import os
import tkinter as tk

def show_splash():
    """Display a simple splash screen without animation"""
    splash = tk.Tk()
    splash.overrideredirect(True)
    splash.geometry("600x300")

    # Background
    bg_frame = tk.Frame(splash, bg='#2c3e50')
    bg_frame.pack(fill=tk.BOTH, expand=True)

    # Title
    tk.Label(bg_frame, text="AMIS Normalization Tool",
            font=("Arial", 28, "bold"), fg="white", bg='#2c3e50').pack(pady=(40, 10))

    # Version
    tk.Label(bg_frame, text="Version 4.3",
            font=("Arial", 14), fg="#3498db", bg='#2c3e50').pack(pady=5)

    # Separator
    tk.Frame(bg_frame, height=2, bg='#3498db').pack(fill='x', padx=100, pady=15)

    # Author information
    author_info = """   
    
    
    Kravtsov G.
Research Center "Applied Statistics"
"""

    tk.Label(bg_frame, text=author_info,
            font=("Arial", 11), fg="white", bg='#2c3e50',
            justify="center").pack(pady=20)

    # Static loading text
    tk.Label(bg_frame, text="Loading program...",
            font=("Arial", 10), fg="yellow", bg='#2c3e50').pack(pady=20)

    # Center the window
    splash.update_idletasks()
    width = splash.winfo_width()
    height = splash.winfo_height()
    x = (splash.winfo_screenwidth() // 2) - (width // 2)
    y = (splash.winfo_screenheight() // 2) - (height // 2)
    splash.geometry(f"+{x}+{y}")

    return splash

def main():
    """Main function"""

    # Display splash screen
    splash = show_splash()
    splash.update()

    # Load modules
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)

    try:
        # Import main application
        from amis_tool.gui.main_window import AMISApp

        # Close splash screen
        splash.destroy()

        # Launch main application
        app = AMISApp()
        app.mainloop()

    except ImportError as e:
        # Error
        splash.destroy()

        error_win = tk.Tk()
        error_win.title("Error")

        tk.Label(error_win, text="Module loading error",
                font=("Arial", 12), fg="red").pack(pady=20)

        tk.Label(error_win, text=str(e), wraplength=400).pack(pady=10, padx=20)

        tk.Button(error_win, text="OK", command=error_win.destroy).pack(pady=20)

        error_win.mainloop()

if __name__ == "__main__":
    main()