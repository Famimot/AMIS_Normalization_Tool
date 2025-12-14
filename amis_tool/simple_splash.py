"""
Simple Splash Screen for AMIS Tool
"""

import tkinter as tk
import time
import threading


def show_simple_splash():
    """Simple splash screen for 3 seconds"""
    splash = tk.Tk()
    splash.title("AMIS Normalization Tool")
    splash.geometry("500x300")
    splash.resizable(False, False)

    # Center
    splash.update_idletasks()
    width = splash.winfo_width()
    height = splash.winfo_height()
    x = (splash.winfo_screenwidth() // 2) - (width // 2)
    y = (splash.winfo_screenheight() // 2) - (height // 2)
    splash.geometry(f"{width}x{height}+{x}+{y}")

    # Content
    tk.Label(splash, text="AMIS Normalization Tool",
             font=("Arial", 24, "bold")).pack(pady=30)

    tk.Label(splash, text="Version 4.3 - Modular optimization",
             font=("Arial", 14), fg="blue").pack()

    tk.Label(splash, text="\nAuthor: Kravtsov G.\nResearch Center \"Applied Statistics\"",
             font=("Arial", 11)).pack()

    tk.Label(splash, text="\nLoading...",
             font=("Arial", 10), fg="green").pack()

    # Function to close after 3 seconds
    def close_after_3s():
        time.sleep(3)
        splash.destroy()

    # Start in separate thread
    thread = threading.Thread(target=close_after_3s, daemon=True)
    thread.start()

    splash.mainloop()


def show_splash_then_run(main_func):
    """Show splash screen and run main program"""
    # Show splash screen
    show_simple_splash()
    # Run main program
    main_func()