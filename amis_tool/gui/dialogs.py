"""
AMIS Dialog Windows v5.6 FULL
Classical AMIS (Mean only), with tooltips, counter, markers, and green grid lines
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib
matplotlib.use('TkAgg')


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


class ToolTip:
    """Create tooltip for widgets"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind('<Enter>', self.enter)
        widget.bind('<Leave>', self.leave)

    def enter(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Arial", 9), padx=5, pady=2)
        label.pack()

    def leave(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class DataFormatDialog(tk.Toplevel):
    """Dialog for choosing data format, scale bounds and normalization method"""
    def __init__(self, master, df, filename, value_col=""):
        super().__init__(master)

        self.title(f"Data Configuration - {os.path.basename(filename)}")
        self.geometry("500x650")
        self.df = df
        self.filename = filename
        self.result = None

        # Data for bound analysis
        self.value_col = value_col
        self.is_single_column = (len(df.columns) == 1)

        if value_col and value_col in df.columns:
            values = pd.to_numeric(df[value_col], errors='coerce').dropna().values
        elif len(df.columns) >= 2:
            values = pd.to_numeric(df.iloc[:, 1], errors='coerce').dropna().values
        elif len(df.columns) == 1:
            values = pd.to_numeric(df.iloc[:, 0], errors='coerce').dropna().values
        else:
            values = np.array([])

        self.data_min = float(np.min(values)) if len(values) > 0 else 0
        self.data_max = float(np.max(values)) if len(values) > 0 else 1

        # Variables
        self.data_type_var = tk.StringVar(value="raw")
        self.scale_mode_var = tk.StringVar(value="auto")
        self.method_var = tk.StringVar(value="mean")  # Only mean, locked

        # Check if first file is already loaded
        self.locked_method = None
        if hasattr(master, 'file1_status') and master.file1_status != "empty":
            if hasattr(master, 'settings1'):
                self.locked_method = 'mean'
                self.method_var.set('mean')

        self.scale_min_var = tk.StringVar(value="")
        self.scale_max_var = tk.StringVar(value="")

        self.create_widgets()
        center_window(self)
        self.transient(master)
        self.grab_set()

        self.after(100, lambda: self.ok_button.focus_set())

    def create_widgets(self):
        """Create dialog interface"""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame,
                 text=f"File: {os.path.basename(self.filename)}",
                 font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(0, 5))

        file_info = f"{len(self.df)} rows, {len(self.df.columns)} columns"
        ttk.Label(main_frame, text=file_info,
                 font=('Arial', 9)).pack(anchor=tk.W, pady=(0, 20))

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # === SECTION 1: DATA FORMAT ===
        format_frame = ttk.LabelFrame(main_frame, text="1. Data Format", padding="10")
        format_frame.pack(fill=tk.X, pady=(0, 15))

        rb_raw = ttk.Radiobutton(format_frame, text="● Raw data: Names/Labels + Values",
                                 variable=self.data_type_var, value="raw")
        rb_raw.pack(anchor=tk.W, pady=5)
        ToolTip(rb_raw, "First column: names/IDs, Second column: numeric values")

        if hasattr(self, 'is_single_column') and self.is_single_column:
            rb_agg = ttk.Radiobutton(format_frame, text="○ Aggregated: NOT AVAILABLE for single column",
                                     variable=self.data_type_var, value="aggregated", state=tk.DISABLED)
        else:
            rb_agg = ttk.Radiobutton(format_frame, text="○ Aggregated: Values + Counts/Frequencies",
                                     variable=self.data_type_var, value="aggregated")
        rb_agg.pack(anchor=tk.W, pady=5)
        ToolTip(rb_agg, "First column: unique values, Second column: how many times each occurs")

        if hasattr(self, 'is_single_column') and self.is_single_column:
            self.data_type_var.set("raw")

        # === SECTION 2: SCALE BOUNDS ===
        scale_frame = ttk.LabelFrame(main_frame, text="2. Scale Bounds", padding="10")
        scale_frame.pack(fill=tk.X, pady=(0, 15))

        data_info = f"Data range: {self.data_min:.4g} to {self.data_max:.4g}"
        ttk.Label(scale_frame, text=data_info,
                 font=('Arial', 9)).pack(anchor=tk.W, pady=(0, 10))

        rb_auto = ttk.Radiobutton(scale_frame, text="Auto: use data min/max",
                       variable=self.scale_mode_var, value="auto",
                       command=self.toggle_scale_mode)
        rb_auto.pack(anchor=tk.W, pady=5)
        ToolTip(rb_auto, "0 AMIS = minimum value in data, 100 AMIS = maximum value")

        rb_manual = ttk.Radiobutton(scale_frame, text="Manual: specify values",
                       variable=self.scale_mode_var, value="manual",
                       command=self.toggle_scale_mode)
        rb_manual.pack(anchor=tk.W, pady=5)
        ToolTip(rb_manual, "Manually set values for 0 and 100 AMIS")

        self.manual_frame = ttk.Frame(scale_frame)
        self.manual_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(self.manual_frame, text="0 AMIS =").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.min_entry = ttk.Entry(self.manual_frame, textvariable=self.scale_min_var,
                                  width=12, state=tk.DISABLED)
        self.min_entry.grid(row=0, column=1, padx=5, pady=5)
        ToolTip(self.min_entry, "Value that corresponds to 0 on AMIS scale")

        ttk.Label(self.manual_frame, text="100 AMIS =").grid(row=0, column=2, padx=(20, 5), sticky=tk.W)
        self.max_entry = ttk.Entry(self.manual_frame, textvariable=self.scale_max_var,
                                  width=12, state=tk.DISABLED)
        self.max_entry.grid(row=0, column=3, padx=5, pady=5)
        ToolTip(self.max_entry, "Value that corresponds to 100 on AMIS scale")

        quick_btn = ttk.Button(scale_frame, text="Use data min/max",
                              command=lambda: self.fill_with_data_bounds(self.data_min, self.data_max))
        quick_btn.pack(pady=(10, 0))
        ToolTip(quick_btn, "Auto-fill manual bounds with data min and max values")

        # === SECTION 3: NORMALIZATION METHOD (ONLY MEAN) ===
        method_frame = ttk.LabelFrame(main_frame, text="3. Normalization Method", padding="10")
        method_frame.pack(fill=tk.X, pady=(0, 15))

        rb_mean = ttk.Radiobutton(method_frame, text="Mean (classical AMIS)",
                       variable=self.method_var, value="mean")
        rb_mean.pack(anchor=tk.W, pady=5)
        ToolTip(rb_mean, "Uses arithmetic mean. Classical AMIS method.")

        info_text = "💡 Mean method is used for all normalizations"
        ttk.Label(method_frame, text=info_text,
                 font=('Arial', 8), foreground="gray").pack(anchor=tk.W, pady=(10, 0))

        # === BUTTONS ===
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        center_frame = ttk.Frame(button_frame)
        center_frame.pack(expand=True)

        self.ok_button = ttk.Button(center_frame, text="OK", width=10, command=self.ok)
        self.ok_button.pack(side=tk.LEFT, padx=5)
        ToolTip(self.ok_button, "Save configuration and load file")

        cancel_btn = ttk.Button(center_frame, text="Cancel", width=10, command=self.cancel)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(cancel_btn, "Cancel loading this file")

        help_btn = ttk.Button(center_frame, text="Help", width=10, command=self.show_help)
        help_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(help_btn, "Show help about data configuration")

    def toggle_scale_mode(self):
        if self.scale_mode_var.get() == "manual":
            self.min_entry.config(state=tk.NORMAL)
            self.max_entry.config(state=tk.NORMAL)
            if not self.scale_min_var.get():
                self.scale_min_var.set(f"{self.data_min:.4g}")
            if not self.scale_max_var.get():
                self.scale_max_var.set(f"{self.data_max:.4g}")
        else:
            self.min_entry.config(state=tk.DISABLED)
            self.max_entry.config(state=tk.DISABLED)

    def fill_with_data_bounds(self, data_min, data_max):
        self.min_entry.delete(0, tk.END)
        self.max_entry.delete(0, tk.END)
        self.min_entry.insert(0, f"{data_min:.4g}")
        self.max_entry.insert(0, f"{data_max:.4g}")

    def show_help(self):
        help_text = """📖 DATA CONFIGURATION:

DATA FORMAT:
• Raw data: First column = Labels/Names, Second column = Values
• Aggregated: First column = Values, Second column = Counts

SCALE BOUNDS:
• Auto: 0 AMIS = data minimum, 100 AMIS = data maximum
• Manual: Specify exact values

NORMALIZATION METHOD:
• Mean: Classical AMIS

MODEL AVAILABILITY:
• 3-point: 6+ points
• 5-point: 10+ points
• 9-point: 20+ points
• 17-point: 40+ points"""
        messagebox.showinfo("Help", help_text)

    def ok(self):
        data_type = self.data_type_var.get()
        method = self.method_var.get()  # Always 'mean'

        if self.scale_mode_var.get() == "auto":
            scale_min = None
            scale_max = None
        else:
            try:
                scale_min = float(self.scale_min_var.get()) if self.scale_min_var.get().strip() else None
                scale_max = float(self.scale_max_var.get()) if self.scale_max_var.get().strip() else None
                if scale_min is not None and scale_max is not None:
                    if scale_min >= scale_max:
                        messagebox.showerror("Error", "Minimum must be LESS than maximum")
                        return
                    if scale_min > self.data_min:
                        messagebox.showerror("Error", f"Minimum cannot be greater than data minimum ({self.data_min:.2f})")
                        return
                    if scale_max < self.data_max:
                        messagebox.showerror("Error", f"Maximum cannot be less than data maximum ({self.data_max:.2f})")
                        return
            except ValueError:
                messagebox.showerror("Error", "Invalid number format")
                return

        self.result = {
            'data_type': data_type,
            'scale_mode': self.scale_mode_var.get(),
            'scale_min': scale_min,
            'scale_max': scale_max,
            'method': method
        }
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()

    def get_result(self):
        self.wait_window(self)
        return self.result


class DistributionDialog(tk.Toplevel):
    """Data distribution dialog"""
    def __init__(self, parent, values, value_col, file_num, path, scale_min=None, scale_max=None):
        super().__init__(parent)

        self.title(f"Distribution - File {file_num}: {os.path.basename(path)}")
        self.geometry("700x550")

        self.values = np.array(values, dtype=float)
        self.value_col = value_col
        self.file_num = file_num
        self.scale_min = scale_min
        self.scale_max = scale_max

        self.create_widgets()
        center_window(self)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame,
                 text=f"📊 Distribution: {self.value_col}",
                 font=('Arial', 14, 'bold')).pack(pady=(0, 15))

        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 15))

        stats = [
            ("Number of points:", f"{len(self.values):,}"),
            ("Unique values:", f"{len(np.unique(self.values))}"),
            ("Minimum:", f"{np.min(self.values):.4f}"),
            ("Maximum:", f"{np.max(self.values):.4f}"),
            ("Mean:", f"{np.mean(self.values):.4f}"),
            ("Median:", f"{np.median(self.values):.4f}"),
            ("Std deviation:", f"{np.std(self.values):.4f}")
        ]

        for i, (label, value) in enumerate(stats):
            frame = ttk.Frame(stats_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=label, width=20, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(frame, text=value, font=('Arial', 9, 'bold')).pack(side=tk.LEFT)

        if self.scale_min is not None or self.scale_max is not None:
            scale_text = "Scale: "
            if self.scale_min is not None:
                scale_text += f"0 AMIS = {self.scale_min:.2f}"
            if self.scale_max is not None:
                scale_text += f", 100 AMIS = {self.scale_max:.2f}"
            ttk.Label(stats_frame, text=scale_text,
                     foreground="blue", font=('Arial', 9)).pack(pady=(10, 0))

        fig_frame = ttk.Frame(main_frame)
        fig_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)

        n_bins = min(30, max(5, int(len(self.values) / 10)))
        ax.hist(self.values, bins=n_bins, edgecolor='black', alpha=0.7, color='skyblue')

        if self.scale_min is not None:
            ax.axvline(self.scale_min, color='red', linestyle='--', linewidth=2, label=f'0 AMIS = {self.scale_min:.2f}')
        if self.scale_max is not None:
            ax.axvline(self.scale_max, color='green', linestyle='--', linewidth=2, label=f'100 AMIS = {self.scale_max:.2f}')

        ax.set_xlabel(self.value_col, fontweight='bold')
        ax.set_ylabel('Frequency', fontweight='bold')
        ax.set_title(f'Distribution of {self.value_col}', fontweight='bold')
        ax.grid(True, alpha=0.3)
        if self.scale_min is not None or self.scale_max is not None:
            ax.legend()

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=fig_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        ttk.Button(main_frame, text="Close", command=self.destroy).pack(pady=10)


class AMISComparisonDialog(tk.Toplevel):
    """AMIS methods comparison window with full features"""
    def __init__(self, master=None, file_num=1, points_coords=None,
                 value_col="", file_path="", available_models=None,
                 show_grid=True):
        super().__init__(master)

        self.title(f"AMIS Methods Comparison - File {file_num}")
        self.geometry("1100x750")
        self.file_num = file_num
        self.points_coords = points_coords or {}
        self.value_col = value_col
        self.file_path = file_path
        self.available_models = available_models or {}
        self.show_grid = show_grid

        self.method_var = tk.StringVar(value="mean")

        linear_available = "x_line" in self.points_coords
        three_available = ("x_3" in self.points_coords and "3_points" in self.available_models)
        five_available = ("x_5" in self.points_coords and "5_points" in self.available_models)
        nine_available = ("x_9" in self.points_coords and "9_points" in self.available_models)
        seventeen_available = ("x_17" in self.points_coords and "17_points" in self.available_models)

        self.var_linear = tk.BooleanVar(value=linear_available)
        self.var_3 = tk.BooleanVar(value=three_available)
        self.var_5 = tk.BooleanVar(value=five_available)
        self.var_9 = tk.BooleanVar(value=nine_available)
        self.var_17 = tk.BooleanVar(value=seventeen_available)

        self.create_widgets()
        self.update_graph()
        center_window(self)

        available_count = sum([linear_available, three_available, five_available,
                              nine_available, seventeen_available])
        self.status_label.config(text=f"Available models: {available_count}/5")

    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        control_frame = ttk.LabelFrame(main_frame, text="Control", padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        ttk.Label(control_frame, text="Select AMIS methods:",
                 font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(0, 10))

        # Linear
        self.cb_linear = ttk.Checkbutton(control_frame, text="📏 Linear",
                       variable=self.var_linear, command=self.update_graph)
        self.cb_linear.pack(anchor=tk.W, pady=5)
        ToolTip(self.cb_linear, "Linear normalization (min→0, max→100)")

        # 3-point
        self.cb_3 = ttk.Checkbutton(control_frame, text="🔵 3 points",
                       variable=self.var_3, command=self.update_graph)
        self.cb_3.pack(anchor=tk.W, pady=5)
        ToolTip(self.cb_3, "3-point AMIS model (needs 6+ data points)")

        # 5-point
        self.cb_5 = ttk.Checkbutton(control_frame, text="🟢 5 points",
                       variable=self.var_5, command=self.update_graph)
        self.cb_5.pack(anchor=tk.W, pady=5)
        ToolTip(self.cb_5, "5-point AMIS model (needs 10+ data points)")

        # 9-point
        self.cb_9 = ttk.Checkbutton(control_frame, text="🟠 9 points",
                       variable=self.var_9, command=self.update_graph)
        self.cb_9.pack(anchor=tk.W, pady=5)
        ToolTip(self.cb_9, "9-point AMIS model (needs 20+ data points)")

        # 17-point
        self.cb_17 = ttk.Checkbutton(control_frame, text="🔴 17 points",
                       variable=self.var_17, command=self.update_graph)
        self.cb_17.pack(anchor=tk.W, pady=5)
        ToolTip(self.cb_17, "17-point AMIS model (needs 40+ data points)")

        ttk.Separator(control_frame, orient='horizontal').pack(fill=tk.X, pady=15)

        # Select available button
        select_btn = ttk.Button(control_frame, text="✅ Select available",
                  command=self.select_available)
        select_btn.pack(fill=tk.X, pady=5)
        ToolTip(select_btn, "Select only models available for current data volume")

        # Hide all button
        none_btn = ttk.Button(control_frame, text="❌ Hide all",
                  command=self.select_none)
        none_btn.pack(fill=tk.X, pady=5)
        ToolTip(none_btn, "Deselect all models")

        ttk.Separator(control_frame, orient='horizontal').pack(fill=tk.X, pady=15)

        # Data volume info
        seventeen_available = ("x_17" in self.points_coords and "17_points" in self.available_models)
        nine_available = ("x_9" in self.points_coords and "9_points" in self.available_models)
        five_available = ("x_5" in self.points_coords and "5_points" in self.available_models)
        three_available = ("x_3" in self.points_coords and "3_points" in self.available_models)

        if seventeen_available:
            info_text = "≥40 points (all models)"
        elif nine_available:
            info_text = "20-39 points (9,5,3,linear)"
        elif five_available:
            info_text = "10-19 points (5,3,linear)"
        elif three_available:
            info_text = "6-9 points (3,linear)"
        else:
            info_text = "<6 points (linear only)"

        ttk.Label(control_frame, text=f"Data volume: {info_text}",
                 font=('Arial', 9), wraplength=150).pack(fill=tk.X, pady=10)

        ttk.Separator(control_frame, orient='horizontal').pack(fill=tk.X, pady=15)

        # Save buttons
        png_btn = ttk.Button(control_frame, text="💾 Save graph (PNG)",
                  command=self.save_png)
        png_btn.pack(fill=tk.X, pady=5)
        ToolTip(png_btn, "Save current graph as PNG image")

        pdf_btn = ttk.Button(control_frame, text="💾 Save graph (PDF)",
                  command=self.save_pdf)
        pdf_btn.pack(fill=tk.X, pady=5)
        ToolTip(pdf_btn, "Save current graph as PDF document")

        ttk.Separator(control_frame, orient='horizontal').pack(fill=tk.X, pady=15)

        # Close button
        close_btn = ttk.Button(control_frame, text="❌ Close", command=self.destroy)
        close_btn.pack(fill=tk.X, pady=5)
        ToolTip(close_btn, "Close this window")

        # Graph frame
        graph_frame = ttk.Frame(main_frame)
        graph_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig = Figure(figsize=(9, 7), dpi=100)
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Info panel
        info_frame = ttk.Frame(graph_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))

        self.info_label = ttk.Label(info_frame,
                                   text=f"File {self.file_num}: {os.path.basename(self.file_path)}",
                                   font=('Arial', 9, 'italic'))
        self.info_label.pack(side=tk.LEFT)

        self.status_label = ttk.Label(info_frame, text="", font=('Arial', 9))
        self.status_label.pack(side=tk.RIGHT)

    def select_available(self):
        self.var_linear.set("x_line" in self.points_coords)
        self.var_3.set("x_3" in self.points_coords and "3_points" in self.available_models)
        self.var_5.set("x_5" in self.points_coords and "5_points" in self.available_models)
        self.var_9.set("x_9" in self.points_coords and "9_points" in self.available_models)
        self.var_17.set("x_17" in self.points_coords and "17_points" in self.available_models)
        self.update_graph()

    def select_none(self):
        self.var_linear.set(False)
        self.var_3.set(False)
        self.var_5.set(False)
        self.var_9.set(False)
        self.var_17.set(False)
        self.update_graph()

    def _add_key_points_grid(self, ax, points_coords, available_models):
        """Add key points grid lines - GREEN for ALL key point Y values"""
        if not self.show_grid:
            return

        # Find best model to get Y points
        best_y_key = None
        if "y_17" in points_coords and available_models and "17_points" in available_models:
            best_y_key = "y_17"
        elif "y_9" in points_coords and available_models and "9_points" in available_models:
            best_y_key = "y_9"
        elif "y_5" in points_coords and available_models and "5_points" in available_models:
            best_y_key = "y_5"
        elif "y_3" in points_coords and available_models and "3_points" in available_models:
            best_y_key = "y_3"
        elif "y_line" in points_coords:
            best_y_key = "y_line"

        # Horizontal lines at ALL key Y values (green, thicker)
        if best_y_key and best_y_key in points_coords:
            for y_val in points_coords[best_y_key]:
                ax.axhline(y_val, color='green', linestyle=':', linewidth=1.5, alpha=0.6)

        # Also keep reference lines
        ax.axhline(50, color='orange', linestyle='-', linewidth=1.0, alpha=0.7)

        # Vertical lines at key X values (green, dashed)
        best_x_key = best_y_key.replace('y_', 'x_') if best_y_key else None
        if best_x_key and best_x_key in points_coords:
            for x_val in points_coords[best_x_key]:
                ax.axvline(x_val, color='green', linestyle='--', linewidth=1.0, alpha=0.5)

    def _add_mapping_arrows(self, ax, points_coords, available_models):
        """Add markers at key points (cyan)"""
        if not self.show_grid:
            return

        best_key = None
        if "x_17" in points_coords and available_models and "17_points" in available_models:
            best_key = "x_17"
        elif "x_9" in points_coords and available_models and "9_points" in available_models:
            best_key = "x_9"
        elif "x_5" in points_coords and available_models and "5_points" in available_models:
            best_key = "x_5"
        elif "x_3" in points_coords and available_models and "3_points" in available_models:
            best_key = "x_3"
        else:
            return

        if best_key not in points_coords:
            return

        x_points = points_coords[best_key]
        y_key = best_key.replace('x_', 'y_')
        if y_key in points_coords:
            y_points = points_coords[y_key]
            if len(x_points) == len(y_points):
                ax.scatter(x_points, y_points, c='cyan', s=40, zorder=10,
                          edgecolors='black', linewidth=0.8, alpha=0.7, label='Key points')

    def update_graph(self):
        """Update the graph with grid lines and markers"""
        self.ax.clear()

        # Add key points grid and markers
        self._add_key_points_grid(self.ax, self.points_coords, self.available_models)
        self._add_mapping_arrows(self.ax, self.points_coords, self.available_models)

        if not self.points_coords:
            self.ax.text(0.5, 0.5, "No data to plot", ha='center', va='center', transform=self.ax.transAxes)
            self.canvas.draw()
            return

        # Determine X range
        if "x_line" in self.points_coords and len(self.points_coords["x_line"]) > 0:
            x_range = np.linspace(np.min(self.points_coords["x_line"]), np.max(self.points_coords["x_line"]), 300)
        else:
            x_range = np.linspace(0, 1, 300)

        def safe_interp(x_vals, y_vals):
            if x_vals is None or y_vals is None or len(x_vals) != len(y_vals):
                return None, None
            unique_mask = np.insert(np.diff(x_vals) != 0, 0, True)
            x_unique = x_vals[unique_mask]
            y_unique = y_vals[unique_mask]
            if len(x_unique) < 2:
                return None, None
            return x_unique, y_unique

        # Linear
        if self.var_linear.get() and "x_line" in self.points_coords:
            x_clean, y_clean = safe_interp(self.points_coords["x_line"], self.points_coords["y_line"])
            if x_clean is not None:
                self.ax.plot(x_range, interp1d(x_clean, y_clean, kind="linear", fill_value="extrapolate")(x_range),
                            'k-', lw=1.5, label="Lin")

        # 3-point
        if self.var_3.get() and "x_3" in self.points_coords and "3_points" in self.available_models:
            x_clean, y_clean = safe_interp(self.points_coords["x_3"], self.points_coords["y_3"])
            if x_clean is not None:
                self.ax.plot(x_range, interp1d(x_clean, y_clean, kind="linear", fill_value="extrapolate")(x_range),
                            'm:', lw=2, label="3")
                self.ax.scatter(x_clean, y_clean, c='m', s=30, zorder=4)

        # 5-point
        if self.var_5.get() and "x_5" in self.points_coords and "5_points" in self.available_models:
            x_clean, y_clean = safe_interp(self.points_coords["x_5"], self.points_coords["y_5"])
            if x_clean is not None:
                self.ax.plot(x_range, interp1d(x_clean, y_clean, kind="linear", fill_value="extrapolate")(x_range),
                            'g--', lw=2, label="5")
                self.ax.scatter(x_clean, y_clean, c='g', s=35, zorder=4)

        # 9-point
        if self.var_9.get() and "x_9" in self.points_coords and "9_points" in self.available_models:
            x_clean, y_clean = safe_interp(self.points_coords["x_9"], self.points_coords["y_9"])
            if x_clean is not None:
                self.ax.plot(x_range, interp1d(x_clean, y_clean, kind="linear", fill_value="extrapolate")(x_range),
                            'r-.', lw=2.5, label="9")
                self.ax.scatter(x_clean, y_clean, c='r', s=40, zorder=4)

        # 17-point
        if self.var_17.get() and "x_17" in self.points_coords and "17_points" in self.available_models:
            x_clean, y_clean = safe_interp(self.points_coords["x_17"], self.points_coords["y_17"])
            if x_clean is not None:
                self.ax.plot(x_range, interp1d(x_clean, y_clean, kind="linear", fill_value="extrapolate")(x_range),
                            'b-', lw=3, label="17")
                self.ax.scatter(x_clean, y_clean, c='b', s=50, zorder=5)

        # Horizontal line at 50
        self.ax.axhline(50, color='orange', lw=2)

        self.ax.set_title(f"File {self.file_num}: {self.value_col}", fontsize=12, fontweight='bold')
        self.ax.set_xlabel(self.value_col, fontsize=10, fontweight='bold')
        self.ax.set_ylabel("AMIS", fontsize=10, fontweight='bold')

        # Right axis with key point labels
        best_y_key = None
        if "y_17" in self.points_coords and self.available_models and "17_points" in self.available_models:
            best_y_key = "y_17"
        elif "y_9" in self.points_coords and self.available_models and "9_points" in self.available_models:
            best_y_key = "y_9"
        elif "y_5" in self.points_coords and self.available_models and "5_points" in self.available_models:
            best_y_key = "y_5"
        elif "y_3" in self.points_coords and self.available_models and "3_points" in self.available_models:
            best_y_key = "y_3"

        if best_y_key and best_y_key in self.points_coords:
            # Force left axis range
            self.ax.set_ylim(0, 100)

            # Create right axis (twinx)
            ax2 = self.ax.twinx()

            # Force the SAME range
            ax2.set_ylim(0, 100)

            # Generate evenly spaced labels
            if best_y_key == "y_17":
                n_ticks = 17
                y_ticks = [i * 100 / (n_ticks - 1) for i in range(n_ticks)]
            elif best_y_key == "y_9":
                n_ticks = 9
                y_ticks = [i * 100 / (n_ticks - 1) for i in range(n_ticks)]
            elif best_y_key == "y_5":
                n_ticks = 5
                y_ticks = [i * 100 / (n_ticks - 1) for i in range(n_ticks)]
            elif best_y_key == "y_3":
                n_ticks = 3
                y_ticks = [i * 100 / (n_ticks - 1) for i in range(n_ticks)]
            else:
                n_ticks = 2
                y_ticks = [0, 100]

            y_labels = []
            for y in y_ticks:
                if y == int(y):
                    y_labels.append(f"{int(y)}")
                else:
                    y_labels.append(f"{y:.2f}")

            ax2.set_yticks(y_ticks)
            ax2.set_yticklabels(y_labels, fontsize=8, color='green')
            ax2.set_ylabel('AMIS Scale', fontsize=9, color='green', fontweight='bold')
            ax2.tick_params(axis='y', colors='green')

            ax2.grid(False)

        self.ax.legend(fontsize=8)
        self.ax.grid(True, alpha=0.3)

        self.fig.tight_layout()

        # Update status counter
        selected = sum([self.var_linear.get(), self.var_3.get(), self.var_5.get(), self.var_9.get(), self.var_17.get()])
        available = sum([
            "x_line" in self.points_coords,
            "x_3" in self.points_coords and "3_points" in self.available_models,
            "x_5" in self.points_coords and "5_points" in self.available_models,
            "x_9" in self.points_coords and "9_points" in self.available_models,
            "x_17" in self.points_coords and "17_points" in self.available_models
        ])
        self.status_label.config(text=f"Selected: {selected}/{available} models")

        self.canvas.draw()

    def save_png(self):
        try:
            base_dir = os.path.dirname(self.file_path)
            plots_dir = os.path.join(base_dir, "plots")
            os.makedirs(plots_dir, exist_ok=True)

            filename = os.path.splitext(os.path.basename(self.file_path))[0]
            method_suffix = f"_mean"
            plot_path = os.path.join(plots_dir, f"{filename}_AMIS_methods_comparison{method_suffix}.png")

            self.fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            messagebox.showinfo("Saved", f"Graph saved:\n{plot_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save graph:\n{str(e)}")

    def save_pdf(self):
        try:
            base_dir = os.path.dirname(self.file_path)
            plots_dir = os.path.join(base_dir, "plots")
            os.makedirs(plots_dir, exist_ok=True)

            filename = os.path.splitext(os.path.basename(self.file_path))[0]
            method_suffix = f"_mean"
            plot_path = os.path.join(plots_dir, f"{filename}_AMIS_methods_comparison{method_suffix}.pdf")

            self.fig.savefig(plot_path, bbox_inches='tight', format='pdf')
            messagebox.showinfo("Saved", f"Graph saved:\n{plot_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save graph:\n{str(e)}")