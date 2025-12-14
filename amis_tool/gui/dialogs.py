"""
AMIS Dialog Windows (упрощенная версия - только один тип данных)
WITH ADAPTIVE MODEL SELECTION
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import numpy as np
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

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

class AMISComparisonDialog(tk.Toplevel):
    """AMIS methods comparison window with checkbox selection and ADAPTIVE models"""
    def __init__(self, master=None, file_num=1, points_coords=None,
                 value_col="", file_path="", available_models=None):
        super().__init__(master)

        self.title(f"AMIS Methods Comparison - File {file_num}")
        self.geometry("1000x750")
        self.file_num = file_num
        self.points_coords = points_coords
        self.value_col = value_col
        self.file_path = file_path
        self.available_models = available_models or {}

        # Default checkbox states based on availability
        self.var_linear = tk.BooleanVar(value="linear" in self.available_models)
        self.var_3 = tk.BooleanVar(value="3_points" in self.available_models)
        self.var_5 = tk.BooleanVar(value="5_points" in self.available_models)
        self.var_9 = tk.BooleanVar(value="9_points" in self.available_models)
        self.var_17 = tk.BooleanVar(value="17_points" in self.available_models)

        self.create_widgets()
        self.update_graph()
        center_window(self)

        # Show information about available models
        available_count = sum([self.var_linear.get(), self.var_3.get(),
                             self.var_5.get(), self.var_9.get(), self.var_17.get()])
        self.status_label.config(text=f"Available models: {available_count}/5")

    def create_widgets(self):
        """Create window widgets"""
        # Main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Control frame
        control_frame = ttk.LabelFrame(main_frame, text="Control", padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Title
        ttk.Label(control_frame, text="Select AMIS methods:",
                 font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(0, 10))

        # Checkboxes - only enable those that are available
        self.cb_linear = ttk.Checkbutton(control_frame, text="📏 Linear",
                       variable=self.var_linear,
                       command=self.update_graph)
        self.cb_linear.pack(anchor=tk.W, pady=5)
        self.cb_linear.config(state=tk.NORMAL if "linear" in self.available_models else tk.DISABLED)

        self.cb_3 = ttk.Checkbutton(control_frame, text="🔵 3 points",
                       variable=self.var_3,
                       command=self.update_graph)
        self.cb_3.pack(anchor=tk.W, pady=5)
        self.cb_3.config(state=tk.NORMAL if "3_points" in self.available_models else tk.DISABLED)

        self.cb_5 = ttk.Checkbutton(control_frame, text="🟢 5 points",
                       variable=self.var_5,
                       command=self.update_graph)
        self.cb_5.pack(anchor=tk.W, pady=5)
        self.cb_5.config(state=tk.NORMAL if "5_points" in self.available_models else tk.DISABLED)

        self.cb_9 = ttk.Checkbutton(control_frame, text="🟠 9 points",
                       variable=self.var_9,
                       command=self.update_graph)
        self.cb_9.pack(anchor=tk.W, pady=5)
        self.cb_9.config(state=tk.NORMAL if "9_points" in self.available_models else tk.DISABLED)

        self.cb_17 = ttk.Checkbutton(control_frame, text="🔴 17 points",
                       variable=self.var_17,
                       command=self.update_graph)
        self.cb_17.pack(anchor=tk.W, pady=5)
        self.cb_17.config(state=tk.NORMAL if "17_points" in self.available_models else tk.DISABLED)

        # Control buttons
        ttk.Separator(control_frame, orient='horizontal').pack(fill=tk.X, pady=15)

        ttk.Button(control_frame, text="✅ Select available",
                  command=self.select_available).pack(fill=tk.X, pady=5)
        ttk.Button(control_frame, text="❌ Hide all",
                  command=self.select_none).pack(fill=tk.X, pady=5)

        ttk.Separator(control_frame, orient='horizontal').pack(fill=tk.X, pady=15)

        # Information about data volume
        info_text = f"Data volume: "
        if "17_points" in self.available_models:
            info_text += "≥100 points (all models)"
        elif "9_points" in self.available_models:
            info_text += "50-99 points (9,5,3,linear)"
        elif "5_points" in self.available_models:
            info_text += "20-49 points (5,3,linear)"
        elif "3_points" in self.available_models:
            info_text += "10-19 points (3,linear)"

        ttk.Label(control_frame, text=info_text,
                 font=('Arial', 9), wraplength=150).pack(fill=tk.X, pady=10)

        ttk.Separator(control_frame, orient='horizontal').pack(fill=tk.X, pady=15)

        # Save buttons
        ttk.Button(control_frame, text="💾 Save graph (PNG)",
                  command=self.save_png).pack(fill=tk.X, pady=5)
        ttk.Button(control_frame, text="💾 Save graph (PDF)",
                  command=self.save_pdf).pack(fill=tk.X, pady=5)

        ttk.Separator(control_frame, orient='horizontal').pack(fill=tk.X, pady=15)

        ttk.Button(control_frame, text="❌ Close",
                  command=self.destroy).pack(fill=tk.X, pady=5)

        # Graph frame
        graph_frame = ttk.Frame(main_frame)
        graph_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Create figure
        self.fig = Figure(figsize=(9, 7), dpi=100)
        self.ax = self.fig.add_subplot(111)

        # Create canvas for graph
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Information panel
        info_frame = ttk.Frame(graph_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))

        self.info_label = ttk.Label(info_frame,
                                   text=f"File {self.file_num}: {os.path.basename(self.file_path)}",
                                   font=('Arial', 9, 'italic'))
        self.info_label.pack(side=tk.LEFT)

        self.status_label = ttk.Label(info_frame,
                                     text="",
                                     font=('Arial', 9))
        self.status_label.pack(side=tk.RIGHT)

    def select_available(self):
        """Select only available methods"""
        self.var_linear.set("linear" in self.available_models)
        self.var_3.set("3_points" in self.available_models)
        self.var_5.set("5_points" in self.available_models)
        self.var_9.set("9_points" in self.available_models)
        self.var_17.set("17_points" in self.available_models)
        self.update_graph()

    def select_none(self):
        """Deselect all methods"""
        self.var_linear.set(False)
        self.var_3.set(False)
        self.var_5.set(False)
        self.var_9.set(False)
        self.var_17.set(False)
        self.update_graph()

    def update_graph(self):
        """Update the graph"""
        # Clear the graph
        self.ax.clear()

        if not self.points_coords:
            self.ax.text(0.5, 0.5, "No data to plot",
                        ha='center', va='center', transform=self.ax.transAxes)
            self.canvas.draw()
            return

        # Determine x-range for plotting
        if "x_17" in self.points_coords and len(self.points_coords["x_17"]) > 0:
            x_range = np.linspace(np.min(self.points_coords["x_17"]),
                                np.max(self.points_coords["x_17"]), 500)
        elif "x_9" in self.points_coords and len(self.points_coords["x_9"]) > 0:
            x_range = np.linspace(np.min(self.points_coords["x_9"]),
                                np.max(self.points_coords["x_9"]), 500)
        elif "x_5" in self.points_coords and len(self.points_coords["x_5"]) > 0:
            x_range = np.linspace(np.min(self.points_coords["x_5"]),
                                np.max(self.points_coords["x_5"]), 500)
        elif "x_3" in self.points_coords and len(self.points_coords["x_3"]) > 0:
            x_range = np.linspace(np.min(self.points_coords["x_3"]),
                                np.max(self.points_coords["x_3"]), 500)
        else:
            x_range = np.linspace(np.min(self.points_coords["x_line"]),
                                np.max(self.points_coords["x_line"]), 500)

        legend_handles = []
        legend_labels = []

        # Linear
        if self.var_linear.get() and "x_line" in self.points_coords:
            line_linear, = self.ax.plot(x_range,
                interp1d(self.points_coords["x_line"], self.points_coords["y_line"],
                        kind="linear", fill_value="extrapolate")(x_range),
                'k-', lw=2, alpha=0.7)
            legend_handles.append(line_linear)
            legend_labels.append("Linear")

        # 3 points
        if self.var_3.get() and "x_3" in self.points_coords:
            line_3, = self.ax.plot(x_range,
                interp1d(self.points_coords["x_3"], self.points_coords["y_3"],
                        kind="linear", fill_value="extrapolate")(x_range),
                'm:', lw=2.5, alpha=0.8)
            self.ax.scatter(self.points_coords["x_3"], self.points_coords["y_3"],
                          c='m', s=40, marker='^', alpha=0.7)
            legend_handles.append(line_3)
            legend_labels.append("3 points")

        # 5 points
        if self.var_5.get() and "x_5" in self.points_coords:
            line_5, = self.ax.plot(x_range,
                interp1d(self.points_coords["x_5"], self.points_coords["y_5"],
                        kind="linear", fill_value="extrapolate")(x_range),
                'g--', lw=2.5, alpha=0.9)
            self.ax.scatter(self.points_coords["x_5"], self.points_coords["y_5"],
                          c='g', s=50, marker='d', alpha=0.7)
            legend_handles.append(line_5)
            legend_labels.append("5 points")

        # 9 points
        if self.var_9.get() and "x_9" in self.points_coords:
            line_9, = self.ax.plot(x_range,
                interp1d(self.points_coords["x_9"], self.points_coords["y_9"],
                        kind="linear", fill_value="extrapolate")(x_range),
                'r-.', lw=3, alpha=0.9)
            self.ax.scatter(self.points_coords["x_9"], self.points_coords["y_9"],
                          c='r', s=60, marker='s', alpha=0.7)
            legend_handles.append(line_9)
            legend_labels.append("9 points")

        # 17 points
        if self.var_17.get() and "x_17" in self.points_coords:
            line_17, = self.ax.plot(x_range,
                interp1d(self.points_coords["x_17"], self.points_coords["y_17"],
                        kind="linear", fill_value="extrapolate")(x_range),
                'b-', lw=3.5, alpha=1.0)
            self.ax.scatter(self.points_coords["x_17"], self.points_coords["y_17"],
                          c='b', s=70, marker='o', alpha=0.7)
            legend_handles.append(line_17)
            legend_labels.append("17 points")

        # Horizontal line at 50
        self.ax.axhline(50, color="orange", lw=2, alpha=0.5, linestyle='--')

        # Graph settings
        self.ax.set_xlabel(f"Original data ({self.value_col})",
                          fontsize=12, fontweight='bold')
        self.ax.set_ylabel("AMIS (0-100)", fontsize=12, fontweight='bold')
        self.ax.set_title(f"AMIS Methods Comparison - File {self.file_num}",
                         fontsize=14, fontweight='bold')

        if legend_handles:
            self.ax.legend(legend_handles, legend_labels, fontsize=10,
                          loc='upper left', framealpha=0.9)

        self.ax.grid(True, alpha=0.3)
        self.fig.tight_layout()

        # Update status
        selected = sum([self.var_linear.get(), self.var_3.get(),
                       self.var_5.get(), self.var_9.get(), self.var_17.get()])
        available = len(self.available_models)
        self.status_label.config(text=f"Selected: {selected}/{available} models")

        # Redraw canvas
        self.canvas.draw()

    def save_png(self):
        """Save graph as PNG"""
        try:
            base_dir = os.path.dirname(self.file_path)
            plots_dir = os.path.join(base_dir, "plots")
            os.makedirs(plots_dir, exist_ok=True)

            filename = os.path.splitext(os.path.basename(self.file_path))[0]
            plot_path = os.path.join(plots_dir, f"{filename}_AMIS_methods_comparison.png")

            self.fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            messagebox.showinfo("Saved", f"Graph saved:\n{plot_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save graph:\n{str(e)}")

    def save_pdf(self):
        """Save graph as PDF"""
        try:
            base_dir = os.path.dirname(self.file_path)
            plots_dir = os.path.join(base_dir, "plots")
            os.makedirs(plots_dir, exist_ok=True)

            filename = os.path.splitext(os.path.basename(self.file_path))[0]
            plot_path = os.path.join(plots_dir, f"{filename}_AMIS_methods_comparison.pdf")

            self.fig.savefig(plot_path, bbox_inches='tight', format='pdf')
            messagebox.showinfo("Saved", f"Graph saved:\n{plot_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save graph:\n{str(e)}")