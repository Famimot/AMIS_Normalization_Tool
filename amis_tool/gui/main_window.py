"""
Main AMIS Application Window v5.2
Classical AMIS (Mean only) - Stable version
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from amis_tool.core.amis_calculations import amis_conversion, safe_aggregated_to_raw
from amis_tool.gui.dialogs import DataFormatDialog, DistributionDialog, AMISComparisonDialog
from amis_tool.gui.widgets import TableViewer
from amis_tool.utils.helpers import center_window


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


class AMISApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # Main window configuration
        self.title("AMIS Normalization Tool v6")
        self.geometry("1250x900")
        self.minsize(1100, 800)

        # Exception handler
        self.report_callback_exception = self._handle_exception

        # Logging initialization
        self.setup_logging()

        # Data variables
        self.data1 = None
        self.data2 = None
        self.path1 = None
        self.path2 = None
        self.df_raw1 = None
        self.df_raw2 = None
        self.value_col1 = None
        self.value_col2 = None
        self.converted1 = None
        self.converted2 = None
        self.points_coords1 = None
        self.points_coords2 = None
        self.available_models1 = None
        self.available_models2 = None

        # Settings storage (method is always 'mean')
        self.settings1 = {
            'data_type': 'raw',
            'scale_mode': 'auto',
            'scale_min': None,
            'scale_max': None,
            'method': 'mean'
        }

        self.settings2 = {
            'data_type': 'raw',
            'scale_mode': 'auto',
            'scale_min': None,
            'scale_max': None,
            'method': 'mean'
        }

        # File statuses
        self.file1_status = "empty"
        self.file2_status = "empty"

        # Grid lines toggle flag
        self.show_grid_lines = tk.BooleanVar(value=True)

        self.create_menu()
        self.create_widgets()
        center_window(self)
        self.update_ui_state()

    def setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('amis_log.txt', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _handle_exception(self, exc, val, tb):
        """Global exception handler"""
        error_msg = f"{str(val)}\n\nDetails in log: amis_log.txt"
        self.after(100, lambda: messagebox.showerror("Error", error_msg))
        self.logger.exception("Global exception")

    def update_ui_state(self):
        """Update button states based on file status"""
        style_mapping = {
            "empty": "StatusEmpty.TFrame",
            "loaded": "StatusLoaded.TFrame",
            "normalized": "StatusNormalized.TFrame",
            "ready": "StatusReady.TFrame"
        }

        if self.file1_status in style_mapping:
            self.file1_status_frame.config(style=style_mapping[self.file1_status])
        if self.file2_status in style_mapping:
            self.file2_status_frame.config(style=style_mapping[self.file2_status])

        status_texts = {
            "empty": "File not loaded",
            "loaded": "File loaded",
            "normalized": "File normalized",
            "ready": "Ready for comparison"
        }
        self.file1_status_label.config(text=status_texts.get(self.file1_status, ""))
        self.file2_status_label.config(text=status_texts.get(self.file2_status, ""))

        file1_loaded = self.file1_status != "empty"
        file2_loaded = self.file2_status != "empty"
        file1_normalized = self.file1_status in ["normalized", "ready"]
        file2_normalized = self.file2_status in ["normalized", "ready"]
        both_normalized = file1_normalized and file2_normalized

        self.norm1_btn.config(state=tk.NORMAL if (file1_loaded and self.file1_status == "loaded") else tk.DISABLED)
        self.norm2_btn.config(state=tk.NORMAL if (file2_loaded and self.file2_status == "loaded") else tk.DISABLED)
        self.view_norm1_btn.config(state=tk.NORMAL if file1_normalized else tk.DISABLED)
        self.view_norm2_btn.config(state=tk.NORMAL if file2_normalized else tk.DISABLED)
        self.compare_btn.config(state=tk.NORMAL if both_normalized else tk.DISABLED)
        self.all_graphs_btn.config(state=tk.NORMAL if both_normalized else tk.DISABLED)
        self.amis_comp1_btn.config(state=tk.NORMAL if file1_normalized else tk.DISABLED)
        self.amis_comp2_btn.config(state=tk.NORMAL if file2_normalized else tk.DISABLED)
        self.dist1_btn.config(state=tk.NORMAL if file1_loaded else tk.DISABLED)
        self.dist2_btn.config(state=tk.NORMAL if file2_loaded else tk.DISABLED)

    def create_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="📁 Load File 1", command=lambda: self.load_first_file())
        file_menu.add_command(label="📁 Load File 2", command=lambda: self.load_second_file())
        file_menu.add_separator()
        file_menu.add_command(label="📊 View Table 1", command=lambda: self.show_table(1))
        file_menu.add_command(label="📊 View Table 2", command=lambda: self.show_table(2))
        file_menu.add_command(label="📊 Show Normalized 1", command=lambda: self.show_normalized_table(1))
        file_menu.add_command(label="📊 Show Normalized 2", command=lambda: self.show_normalized_table(2))
        file_menu.add_separator()
        file_menu.add_command(label="🗑️ Clear All", command=lambda: self.clear_all())
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Exit", command=self.quit)

        process_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Processing", menu=process_menu)
        process_menu.add_command(label="⚙️ Normalize File 1", command=lambda: self.normalize_first())
        process_menu.add_command(label="⚙️ Normalize File 2", command=lambda: self.normalize_second())
        process_menu.add_separator()
        process_menu.add_command(label="📊 Compare Files", command=lambda: self.compare_files())

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Visualization", menu=view_menu)
        view_menu.add_command(label="📈 Graph (File 1)", command=lambda: self.show_amis_comparison(1))
        view_menu.add_command(label="📈 Graph (File 2)", command=lambda: self.show_amis_comparison(2))
        view_menu.add_separator()
        view_menu.add_command(label="📊 Distribution (File 1)", command=lambda: self.show_distribution(1))
        view_menu.add_command(label="📊 Distribution (File 2)", command=lambda: self.show_distribution(2))
        view_menu.add_separator()
        view_menu.add_command(label="📊 All Comparison Graphs", command=lambda: self.plot_comparison_graphs())
        view_menu.add_separator()
        view_menu.add_checkbutton(label="🔲 Show Grid Lines (Key Points)",
                                 variable=self.show_grid_lines,
                                 command=self.update_ui_state)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="📖 About", command=lambda: self.show_about())
        help_menu.add_command(label="❓ How to Use", command=lambda: self.show_help())

    def create_widgets(self):
        """Create interface widgets with tooltips"""
        main_container = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_panel = ttk.Frame(main_container)
        main_container.add(left_panel, weight=3)

        right_panel = ttk.Frame(main_container)
        main_container.add(right_panel, weight=1)

        # Left panel - tables
        self.table1 = TableViewer(left_panel, title="File 1:")
        self.table1.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))

        self.file1_status_frame = ttk.Frame(left_panel, relief=tk.RIDGE, borderwidth=1)
        self.file1_status_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.file1_status_label = ttk.Label(self.file1_status_frame, text="File not loaded", font=('Arial', 10))
        self.file1_status_label.pack(pady=3)

        self.table2 = TableViewer(left_panel, title="File 2:")
        self.table2.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))

        self.file2_status_frame = ttk.Frame(left_panel, relief=tk.RIDGE, borderwidth=1)
        self.file2_status_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.file2_status_label = ttk.Label(self.file2_status_frame, text="File not loaded", font=('Arial', 10))
        self.file2_status_label.pack(pady=3)

        # Right panel - controls
        control_frame = ttk.LabelFrame(right_panel, text="Control Panel", padding="10")
        control_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # File loading group
        load_frame = ttk.LabelFrame(control_frame, text="📁 File Loading", padding="10")
        load_frame.pack(fill=tk.X, pady=(0, 10))

        btn_load1 = ttk.Button(load_frame, text="📁 LOAD FILE 1", command=lambda: self.load_first_file())
        btn_load1.pack(fill=tk.X, pady=3)
        ToolTip(btn_load1, "Load Excel/CSV file. Configure format, bounds and method in dialog")

        btn_load2 = ttk.Button(load_frame, text="📁 LOAD FILE 2", command=lambda: self.load_second_file())
        btn_load2.pack(fill=tk.X, pady=3)
        ToolTip(btn_load2, "Load second file for comparison")

        # Processing group
        process_frame = ttk.LabelFrame(control_frame, text="⚙️ Data Processing", padding="10")
        process_frame.pack(fill=tk.X, pady=(0, 10))

        self.norm1_btn = ttk.Button(process_frame, text="⚙️ NORMALIZE FILE 1",
                                   command=lambda: self.normalize_first(), state=tk.DISABLED)
        self.norm1_btn.pack(fill=tk.X, pady=3)
        ToolTip(self.norm1_btn, "Transform data to AMIS scale 0-100 using Mean method")

        self.norm2_btn = ttk.Button(process_frame, text="⚙️ NORMALIZE FILE 2",
                                   command=lambda: self.normalize_second(), state=tk.DISABLED)
        self.norm2_btn.pack(fill=tk.X, pady=3)
        ToolTip(self.norm2_btn, "Transform second file to AMIS scale 0-100 using Mean method")

        self.view_norm1_btn = ttk.Button(process_frame, text="📊 SHOW NORMALIZED 1",
                                        command=lambda: self.show_normalized_table(1), state=tk.DISABLED)
        self.view_norm1_btn.pack(fill=tk.X, pady=3)
        ToolTip(self.view_norm1_btn, "Display normalized values table (0-100 AMIS scale)")

        self.view_norm2_btn = ttk.Button(process_frame, text="📊 SHOW NORMALIZED 2",
                                        command=lambda: self.show_normalized_table(2), state=tk.DISABLED)
        self.view_norm2_btn.pack(fill=tk.X, pady=3)
        ToolTip(self.view_norm2_btn, "Display normalized values for second file")

        self.compare_btn = ttk.Button(process_frame, text="📊 COMPARE FILES",
                                     command=lambda: self.compare_files(), state=tk.DISABLED)
        self.compare_btn.pack(fill=tk.X, pady=3)
        ToolTip(self.compare_btn, "Create correspondence table between two normalized files")

        # Visualization group
        viz_frame = ttk.LabelFrame(control_frame, text="📈 Visualization", padding="10")
        viz_frame.pack(fill=tk.X, pady=(0, 10))

        self.amis_comp1_btn = ttk.Button(viz_frame, text="📈 GRAPH (File 1)",
                                        command=lambda: self.show_amis_comparison(1), state=tk.DISABLED)
        self.amis_comp1_btn.pack(fill=tk.X, pady=3)
        ToolTip(self.amis_comp1_btn, "Interactive graph with all AMIS models")

        self.amis_comp2_btn = ttk.Button(viz_frame, text="📈 GRAPH (File 2)",
                                        command=lambda: self.show_amis_comparison(2), state=tk.DISABLED)
        self.amis_comp2_btn.pack(fill=tk.X, pady=3)
        ToolTip(self.amis_comp2_btn, "Interactive graph for second file")

        self.dist1_btn = ttk.Button(viz_frame, text="📊 DISTRIBUTION (File 1)",
                                   command=lambda: self.show_distribution(1), state=tk.DISABLED)
        self.dist1_btn.pack(fill=tk.X, pady=3)
        ToolTip(self.dist1_btn, "Show histogram and statistics of original data")

        self.dist2_btn = ttk.Button(viz_frame, text="📊 DISTRIBUTION (File 2)",
                                   command=lambda: self.show_distribution(2), state=tk.DISABLED)
        self.dist2_btn.pack(fill=tk.X, pady=3)
        ToolTip(self.dist2_btn, "Show histogram for second file")

        self.all_graphs_btn = ttk.Button(viz_frame, text="📊 ALL COMPARISON GRAPHS",
                                        command=lambda: self.plot_comparison_graphs(), state=tk.DISABLED)
        self.all_graphs_btn.pack(fill=tk.X, pady=3)
        ToolTip(self.all_graphs_btn, "Generate 4 comparison plots")

        # Management group
        manage_frame = ttk.LabelFrame(control_frame, text="⚙️ Management", padding="10")
        manage_frame.pack(fill=tk.X)

        clear_btn = ttk.Button(manage_frame, text="🗑️ CLEAR ALL", command=lambda: self.clear_all())
        clear_btn.pack(fill=tk.X, pady=3)
        ToolTip(clear_btn, "Remove all loaded data and reset application")

        exit_btn = ttk.Button(manage_frame, text="🚪 EXIT", command=self.quit)
        exit_btn.pack(fill=tk.X, pady=3)
        ToolTip(exit_btn, "Close application")

        # Bottom panel - log
        bottom_panel = ttk.Frame(self)
        bottom_panel.pack(fill=tk.X, padx=5, pady=(0, 5))

        log_frame = ttk.LabelFrame(bottom_panel, text="📝 Work Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD, font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.status_var = tk.StringVar(value="Ready to work")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, font=('Arial', 9))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)

        style = ttk.Style()
        style.configure("StatusEmpty.TFrame", background="#f0f0f0")
        style.configure("StatusLoaded.TFrame", background="#e8f5e8")
        style.configure("StatusNormalized.TFrame", background="#e3f2fd")
        style.configure("StatusReady.TFrame", background="#f3e5f5")

    def log_action(self, message, level="info"):
        """Log action to text field"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if level == "error":
            prefix = f"[{timestamp}] ❌ "
            tag = "error"
        elif level == "warning":
            prefix = f"[{timestamp}] ⚠️ "
            tag = "warning"
        elif level == "success":
            prefix = f"[{timestamp}] ✅ "
            tag = "success"
        else:
            prefix = f"[{timestamp}] ℹ️ "
            tag = "info"

        self.log_text.insert(tk.END, prefix + message + "\n", tag)
        self.log_text.see(tk.END)
        self.status_var.set(message)

        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("info", foreground="blue")

        if level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)

    def get_output_paths(self, file_path, suffix=""):
        """Get paths for saving results"""
        base_dir = os.path.dirname(file_path)
        filename = os.path.splitext(os.path.basename(file_path))[0]

        tables_dir = os.path.join(base_dir, "converted_tables")
        plots_dir = os.path.join(base_dir, "plots")

        os.makedirs(tables_dir, exist_ok=True)
        os.makedirs(plots_dir, exist_ok=True)

        if suffix:
            filename = f"{filename}_{suffix}"

        table_path = os.path.join(tables_dir, f"{filename}.xlsx")
        plot_path = os.path.join(plots_dir, f"{filename}.png")

        return tables_dir, plots_dir, table_path, plot_path, filename

    def load_first_file(self):
        self._load_file(1)

    def load_second_file(self):
        self._load_file(2)

    def _load_file(self, file_num):
        # Both files must use mean method (no choice)
        try:
            file_path = filedialog.askopenfilename(
                title=f"Select File {file_num}",
                filetypes=[("Excel files", "*.xlsx"), ("Excel old", "*.xls"), ("CSV files", "*.csv"),
                           ("All files", "*.*")]
            )

            if not file_path:
                return

            self.log_action(f"Loading file {file_num}: {os.path.basename(file_path)}")

            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            if df.empty:
                raise ValueError("File is empty")

            # Determine value column
            if len(df.columns) >= 2:
                value_col = df.columns[1]
            elif len(df.columns) == 1:
                value_col = df.columns[0]
                if file_num == 1:
                    self.settings1['data_type'] = 'raw'
                else:
                    self.settings2['data_type'] = 'raw'
            else:
                value_col = "Values"

            dialog = DataFormatDialog(self, df, file_path, value_col)
            result = dialog.get_result()

            if result is None:
                self.log_action(f"⚠️ File {file_num} loading cancelled", "warning")
                return

            # Force method to 'mean' regardless of dialog result
            result['method'] = 'mean'

            if file_num == 1:
                self.settings1 = result
                self.data1 = df
                self.path1 = file_path
                self.file1_status = "loaded"
                self.table1.set_original_data(df, "raw data")
            else:
                self.settings2 = result
                self.data2 = df
                self.path2 = file_path
                self.file2_status = "loaded"
                self.table2.set_original_data(df, "raw data")

            self.log_action(f"✅ Loaded: {len(df)} rows, {len(df.columns)} columns (using Mean method)", "success")
            self.update_ui_state()

        except Exception as e:
            self.log_action(f"❌ File loading error: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")

    def normalize_first(self):
        if self.data1 is None:
            messagebox.showwarning("Warning", "First load file 1")
            return
        self._normalize_file(1)

    def normalize_second(self):
        if self.data2 is None:
            messagebox.showwarning("Warning", "First load file 2")
            return
        self._normalize_file(2)

    def _normalize_file(self, file_num):
        try:
            self.log_action(f"🔄 Starting normalization of file {file_num}...")

            if file_num == 1:
                settings = self.settings1
                data = self.data1
                path = self.path1
            else:
                settings = self.settings2
                data = self.data2
                path = self.path2

            # Always use mean method
            method = 'mean'
            self.log_action(f"📊 Using method: Mean (classical AMIS)", "info")

            data_type = settings['data_type']

            if settings['scale_mode'] == 'auto':
                fixed_min = None
                fixed_max = None
            else:
                fixed_min = settings['scale_min']
                fixed_max = settings['scale_max']

            raw_data, value_col = safe_aggregated_to_raw(data, data_type)

            if data_type == "raw" and len(data.columns) >= 1:
                labels = data.iloc[:, 0].values[:len(raw_data)]
            else:
                labels = np.arange(len(raw_data))

            converted, points_coords, available_models = amis_conversion(
                raw_data, fixed_min, fixed_max, method=method
            )

            n = len(raw_data)
            unique_n = len(np.unique(raw_data))
            available_count = len(available_models)
            self.log_action(f"📊 Data: {n} points, {unique_n} unique values, {available_count}/5 models available")

            method_suffix = f"AMIS_{file_num}_mean"
            tables_dir, plots_dir, table_path, _, _ = self.get_output_paths(path, method_suffix)

            result_dict = {}

            # For single column file, create ID column
            if len(data.columns) == 1:
                result_dict["ID"] = np.arange(1, len(raw_data) + 1)
            elif len(labels) == len(raw_data):
                result_dict["Label"] = labels

            result_dict[f"{value_col}_raw"] = raw_data

            if "linear" in converted:
                result_dict["Linear"] = converted["linear"]
            if "3_points" in converted:
                result_dict["AMIS_3"] = converted["3_points"]
            if "5_points" in converted:
                result_dict["AMIS_5"] = converted["5_points"]
            if "9_points" in converted:
                result_dict["AMIS_9"] = converted["9_points"]
            if "17_points" in converted:
                result_dict["AMIS_17"] = converted["17_points"]

            df_result = pd.DataFrame(result_dict)

            try:
                df_result.to_excel(table_path, index=False)
            except PermissionError:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name, ext = os.path.splitext(table_path)
                table_path = f"{name}_{timestamp}{ext}"
                df_result.to_excel(table_path, index=False)

            if file_num == 1:
                self.df_raw1 = raw_data
                self.value_col1 = value_col
                self.converted1 = converted
                self.points_coords1 = points_coords
                self.available_models1 = available_models
                self.file1_status = "normalized"
                self.table1.set_normalized_data(df_result)
            else:
                self.df_raw2 = raw_data
                self.value_col2 = value_col
                self.converted2 = converted
                self.points_coords2 = points_coords
                self.available_models2 = available_models
                self.file2_status = "normalized"
                self.table2.set_normalized_data(df_result)

            self.log_action(f"✅ File {file_num} successfully normalized", "success")
            self.update_ui_state()

            messagebox.showinfo("Done",
                f"File {file_num} normalized!\n\n"
                f"Method: Mean (classical AMIS)\n"
                f"Data: {n} points\n"
                f"Results saved in:\n{table_path}")

        except Exception as e:
            self.log_action(f"❌ Normalization error: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to normalize file:\n{str(e)}")

    def show_distribution(self, file_num):
        try:
            if file_num == 1:
                if self.data1 is None:
                    messagebox.showwarning("Warning", "First load file 1")
                    return
                data = self.data1
                path = self.path1
                settings = self.settings1
                value_col = self.value_col1 if hasattr(self, 'value_col1') else ""
            else:
                if self.data2 is None:
                    messagebox.showwarning("Warning", "First load file 2")
                    return
                data = self.data2
                path = self.path2
                settings = self.settings2
                value_col = self.value_col2 if hasattr(self, 'value_col2') else ""

            # For single column file and raw data
            if len(data.columns) == 1:
                values_series = pd.to_numeric(data.iloc[:, 0], errors='coerce')
                values = values_series.dropna().values
                value_col = data.columns[0]
            elif settings['data_type'] == "raw" and len(data.columns) >= 2:
                values_series = pd.to_numeric(data.iloc[:, 1], errors='coerce')
                values = values_series.dropna().values
                if not value_col and len(data.columns) >= 2:
                    value_col = data.columns[1]
            else:
                values_series = pd.to_numeric(data.iloc[:, 0], errors='coerce')
                values = values_series.dropna().values
                if not value_col and len(data.columns) >= 1:
                    value_col = data.columns[0]

            if len(values) == 0:
                messagebox.showerror("Error", "No valid numeric data found")
                return

            scale_min = settings.get('scale_min')
            scale_max = settings.get('scale_max')

            dialog = DistributionDialog(self, values, value_col, file_num, path, scale_min, scale_max)
            dialog.transient(self)
            dialog.grab_set()

            def on_close():
                self.lift()
                self.focus_force()
                dialog.destroy()

            dialog.protocol("WM_DELETE_WINDOW", on_close)
            self.wait_window(dialog)
            self.lift()
            self.focus_force()

        except Exception as e:
            self.log_action(f"❌ Error opening distribution: {str(e)}", "error")
            messagebox.showerror("Error", f"Cannot open distribution view:\n{str(e)}")

    def show_normalized_table(self, file_num):
        if file_num == 1:
            if not self.converted1:
                messagebox.showwarning("Warning", "First normalize file 1")
                return
            self.table1.showing_normalized = True
            self.table1.mode_btn.config(text="Normalized")
            if self.table1.normalized_data is not None:
                self.table1.update_data(self.table1.normalized_data, "normalized")
        else:
            if not self.converted2:
                messagebox.showwarning("Warning", "First normalize file 2")
                return
            self.table2.showing_normalized = True
            self.table2.mode_btn.config(text="Normalized")
            if self.table2.normalized_data is not None:
                self.table2.update_data(self.table2.normalized_data, "normalized")

    def compare_files(self):
        if not all([self.converted1, self.converted2]):
            messagebox.showwarning("Warning", "First normalize both files")
            return

        # Both files always use mean method
        try:
            y_amis = np.linspace(0, 100, 101)

            if "y_17" in self.points_coords1 and "y_17" in self.points_coords2:
                y_points = self.points_coords1['y_17']
                inv1 = interp1d(y_points, self.points_coords1['x_17'], kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_17'], kind='linear', fill_value='extrapolate', bounds_error=False)
            elif "y_9" in self.points_coords1 and "y_9" in self.points_coords2:
                y_points = self.points_coords1['y_9']
                inv1 = interp1d(y_points, self.points_coords1['x_9'], kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_9'], kind='linear', fill_value='extrapolate', bounds_error=False)
            elif "y_5" in self.points_coords1 and "y_5" in self.points_coords2:
                y_points = self.points_coords1['y_5']
                inv1 = interp1d(y_points, self.points_coords1['x_5'], kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_5'], kind='linear', fill_value='extrapolate', bounds_error=False)
            elif "y_3" in self.points_coords1 and "y_3" in self.points_coords2:
                y_points = self.points_coords1['y_3']
                inv1 = interp1d(y_points, self.points_coords1['x_3'], kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_3'], kind='linear', fill_value='extrapolate', bounds_error=False)
            else:
                y_points = self.points_coords1['y_line']
                inv1 = interp1d(y_points, self.points_coords1['x_line'], kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_line'], kind='linear', fill_value='extrapolate', bounds_error=False)

            df_comp = pd.DataFrame({
                "AMIS": y_amis,
                self.value_col1: inv1(y_amis),
                self.value_col2: inv2(y_amis)
            })

            base_dir = os.path.dirname(self.path1)
            tables_dir = os.path.join(base_dir, "converted_tables")
            os.makedirs(tables_dir, exist_ok=True)

            out_file = os.path.join(tables_dir, "AMIS_comparison_mean.xlsx")
            df_comp.to_excel(out_file, index=False)

            self.log_action("✅ Comparison completed", "success")
            messagebox.showinfo("Done", f"Comparison table saved:\n{out_file}")

        except Exception as e:
            self.log_action(f"❌ Comparison error: {str(e)}", "error")

    def show_amis_comparison(self, file_num):
        try:
            if file_num == 1:
                if not self.points_coords1:
                    messagebox.showwarning("Warning", "First normalize file 1")
                    return
                dialog = AMISComparisonDialog(self, file_num, self.points_coords1, self.value_col1, self.path1, self.available_models1, show_grid=self.show_grid_lines.get())
            else:
                if not self.points_coords2:
                    messagebox.showwarning("Warning", "First normalize file 2")
                    return
                dialog = AMISComparisonDialog(self, file_num, self.points_coords2, self.value_col2, self.path2, self.available_models2, show_grid=self.show_grid_lines.get())

            dialog.transient(self)
            dialog.grab_set()
            self.wait_window(dialog)

        except Exception as e:
            self.log_action(f"❌ Error: {str(e)}", "error")

    def _add_key_points_grid(self, ax, points_coords, available_models):
        """Add key points grid lines - GREEN for vertical lines"""
        if not self.show_grid_lines.get():
            return

        # Horizontal lines - GREEN for 25 and 75
        for y_val in [0, 100]:
            ax.axhline(y_val, color='gray', linestyle=':', linewidth=0.8, alpha=0.5)
        for y_val in [25, 75]:
            ax.axhline(y_val, color='green', linestyle=':', linewidth=0.8, alpha=0.5)
        ax.axhline(50, color='orange', linestyle='-', linewidth=1.0, alpha=0.7)

        # Vertical lines - GREEN
        best_key = None
        if "x_17" in points_coords and available_models and "17_points" in available_models:
            best_key = "x_17"
        elif "x_9" in points_coords and available_models and "9_points" in available_models:
            best_key = "x_9"
        elif "x_5" in points_coords and available_models and "5_points" in available_models:
            best_key = "x_5"
        elif "x_3" in points_coords and available_models and "3_points" in available_models:
            best_key = "x_3"
        elif "x_line" in points_coords:
            best_key = "x_line"

        if best_key and best_key in points_coords:
            for x_val in points_coords[best_key]:
                ax.axvline(x_val, color='green', linestyle='--', linewidth=0.6, alpha=0.4)

    def _add_mapping_arrows(self, ax, points_coords, available_models, value_col):
        """Add markers at key points"""
        if not self.show_grid_lines.get():
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
                ax.scatter(x_points, y_points, c='cyan', s=40, zorder=10, edgecolors='black', linewidth=0.8, alpha=0.7)

    def plot_comparison_graphs(self):
        """Plot all comparison graphs"""
        if not all([self.points_coords1, self.points_coords2]):
            messagebox.showwarning("Warning", "First normalize both files")
            return

        # Both files always use mean method
        try:
            base_dir = os.path.dirname(self.path1)
            plots_dir = os.path.join(base_dir, "plots")
            os.makedirs(plots_dir, exist_ok=True)

            graphs_window = tk.Toplevel(self)
            graphs_window.title("AMIS - File Comparison")
            graphs_window.geometry("1250x1000")
            graphs_window.transient(self)
            graphs_window.grab_set()

            main_container = ttk.Frame(graphs_window)
            main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            fig = Figure(figsize=(11, 8), dpi=100)

            def safe_interp(x_vals, y_vals):
                if x_vals is None or y_vals is None or len(x_vals) != len(y_vals):
                    return None, None
                unique_mask = np.insert(np.diff(x_vals) != 0, 0, True)
                x_unique = x_vals[unique_mask]
                y_unique = y_vals[unique_mask]
                if len(x_unique) < 2:
                    return None, None
                return x_unique, y_unique

            # Graph 1
            ax1 = fig.add_subplot(221)
            if "x_line" in self.points_coords1 and len(self.points_coords1["x_line"]) > 0:
                x1_range = np.linspace(np.min(self.points_coords1["x_line"]), np.max(self.points_coords1["x_line"]), 300)
            else:
                x1_range = np.linspace(0, 1, 300)

            models = [
                ("x_line", "y_line", "k-", 1.5, "Lin", None),
                ("x_3", "y_3", "m:", 2, "3", "3_points"),
                ("x_5", "y_5", "g--", 2, "5", "5_points"),
                ("x_9", "y_9", "r-.", 2.5, "9", "9_points"),
                ("x_17", "y_17", "b-", 3, "17", "17_points")
            ]

            for x_key, y_key, style, lw, label, req_model in models:
                if x_key in self.points_coords1:
                    if req_model is None or (self.available_models1 and req_model in self.available_models1):
                        x_clean, y_clean = safe_interp(self.points_coords1[x_key], self.points_coords1[y_key])
                        if x_clean is not None:
                            ax1.plot(x1_range, interp1d(x_clean, y_clean, kind="linear", fill_value="extrapolate")(x1_range), style, lw=lw, label=label)
                            ax1.scatter(x_clean, y_clean, s=30, zorder=4)

            self._add_key_points_grid(ax1, self.points_coords1, self.available_models1)
            ax1.set_title(f"File 1: {self.value_col1} (MEAN)")
            ax1.set_xlabel(self.value_col1)
            ax1.set_ylabel("AMIS")
            ax1.legend(fontsize=8)
            ax1.grid(True, alpha=0.3)
            ax1.axhline(50, color='orange', lw=2)

            # Graph 2
            ax2 = fig.add_subplot(222)
            if "x_line" in self.points_coords2 and len(self.points_coords2["x_line"]) > 0:
                x2_range = np.linspace(np.min(self.points_coords2["x_line"]), np.max(self.points_coords2["x_line"]), 300)
            else:
                x2_range = np.linspace(0, 1, 300)

            for x_key, y_key, style, lw, label, req_model in models:
                if x_key in self.points_coords2:
                    if req_model is None or (self.available_models2 and req_model in self.available_models2):
                        x_clean, y_clean = safe_interp(self.points_coords2[x_key], self.points_coords2[y_key])
                        if x_clean is not None:
                            ax2.plot(x2_range, interp1d(x_clean, y_clean, kind="linear", fill_value="extrapolate")(x2_range), style, lw=lw, label=label)
                            ax2.scatter(x_clean, y_clean, s=30, zorder=4)

            self._add_key_points_grid(ax2, self.points_coords2, self.available_models2)
            ax2.set_title(f"File 2: {self.value_col2} (MEAN)")
            ax2.set_xlabel(self.value_col2)
            ax2.set_ylabel("AMIS")
            ax2.legend(fontsize=8)
            ax2.grid(True, alpha=0.3)
            ax2.axhline(50, color='orange', lw=2)

            # Graph 3: Correspondence
            ax3 = fig.add_subplot(223)
            y_amis = np.linspace(0, 100, 101)

            for model_key in ["y_17", "y_9", "y_5", "y_3", "y_line"]:
                if model_key in self.points_coords1 and model_key in self.points_coords2:
                    x1_clean, y1_clean = safe_interp(self.points_coords1[model_key.replace('y', 'x')], self.points_coords1[model_key])
                    x2_clean, y2_clean = safe_interp(self.points_coords2[model_key.replace('y', 'x')], self.points_coords2[model_key])
                    if x1_clean is not None and x2_clean is not None:
                        inv1 = interp1d(y1_clean, x1_clean, kind='linear', fill_value='extrapolate', bounds_error=False)
                        inv2 = interp1d(y2_clean, x2_clean, kind='linear', fill_value='extrapolate', bounds_error=False)
                        nom1 = inv1(y_amis)
                        nom2 = inv2(y_amis)
                        ax3.plot(nom1, nom2, 'darkgreen', marker='o', markersize=4, linewidth=3)
                        break

            ax3.set_title(f"AMIS Correspondence (MEAN)")
            ax3.set_xlabel(self.value_col1)
            ax3.set_ylabel(self.value_col2)
            ax3.grid(True, alpha=0.3)

            # Graph 4: Double Y
            ax4 = fig.add_subplot(224)
            ax4.plot(y_amis, nom1, 'blue', marker='o', markersize=5, linewidth=2.5, label=self.value_col1)
            ax4.set_xlabel("AMIS (0-100)")
            ax4.set_ylabel(self.value_col1, color='blue')
            ax4.tick_params(axis='y', labelcolor='blue')

            ax4_2 = ax4.twinx()
            ax4_2.plot(y_amis, nom2, 'red', marker='s', markersize=5, linewidth=2.5, label=self.value_col2)
            ax4_2.set_ylabel(self.value_col2, color='red')
            ax4_2.tick_params(axis='y', labelcolor='red')

            if self.show_grid_lines.get():
                for y_val in [0, 25, 50, 75, 100]:
                    ax4.axvline(y_val, color='gray', linestyle=':', linewidth=0.6, alpha=0.4)

            ax4.set_title(f"Comparison by AMIS Scale (MEAN)")
            ax4.legend(loc='upper left', fontsize=8)
            ax4_2.legend(loc='upper right', fontsize=8)
            ax4.grid(True, alpha=0.3)

            fig.tight_layout()

            plot_path = os.path.join(plots_dir, "AMIS_comparison_graphs_mean.png")
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            self.log_action(f"💾 Graphs saved: {plot_path}", "success")

            canvas = FigureCanvasTkAgg(fig, main_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            button_frame = ttk.Frame(graphs_window)
            button_frame.pack(fill=tk.X, padx=10, pady=5)

            save_btn = ttk.Button(button_frame, text="💾 Save All Graphs",
                                  command=lambda: self.save_comparison_figure(fig, self.path1, "AMIS_comparison_graphs_mean"))
            save_btn.pack(side=tk.LEFT, padx=5)
            ToolTip(save_btn, "Save all graphs as PNG and PDF")

            close_btn = ttk.Button(button_frame, text="❌ Close", command=graphs_window.destroy)
            close_btn.pack(side=tk.RIGHT, padx=5)
            ToolTip(close_btn, "Close comparison window")

            graphs_window.protocol("WM_DELETE_WINDOW", graphs_window.destroy)

            center_window(graphs_window)

        except Exception as e:
            self.log_action(f"❌ Graph error: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to plot graphs:\n{str(e)}")

    def save_comparison_figure(self, fig, file_path, suffix):
        try:
            _, _, _, plot_path, _ = self.get_output_paths(file_path, suffix)
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            pdf_path = plot_path.replace('.png', '.pdf')
            fig.savefig(pdf_path, bbox_inches='tight')
            self.log_action(f"💾 Graphs saved", "success")

        except Exception as e:
            self.log_action(f"❌ Save error: {str(e)}", "error")

    def show_table(self, num):
        if num == 1 and self.data1 is None:
            messagebox.showwarning("Warning", "First load file 1")
            return
        elif num == 2 and self.data2 is None:
            messagebox.showwarning("Warning", "First load file 2")
            return

        data = self.data1 if num == 1 else self.data2
        path = self.path1 if num == 1 else self.path2

        table_window = tk.Toplevel(self)
        table_window.title(f"Data Table - File {num}: {os.path.basename(path)}")
        table_window.geometry("900x600")

        table_frame = TableViewer(table_window, title=f"File {num}: data")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        table_frame.set_original_data(data, "raw data")
        center_window(table_window)

    def clear_all(self):
        if messagebox.askyesno("Confirmation", "Clear all data?"):
            self.data1 = None
            self.data2 = None
            self.path1 = None
            self.path2 = None
            self.df_raw1 = None
            self.df_raw2 = None
            self.value_col1 = None
            self.value_col2 = None
            self.converted1 = None
            self.converted2 = None
            self.points_coords1 = None
            self.points_coords2 = None
            self.available_models1 = None
            self.available_models2 = None
            self.settings1 = {'data_type': 'raw', 'scale_mode': 'auto', 'scale_min': None, 'scale_max': None, 'method': 'mean'}
            self.settings2 = {'data_type': 'raw', 'scale_mode': 'auto', 'scale_min': None, 'scale_max': None, 'method': 'mean'}
            self.file1_status = "empty"
            self.file2_status = "empty"

            self.table1.clear()
            self.table2.clear()
            self.log_text.delete(1.0, tk.END)
            self.log_action("🗑️ All data cleared", "info")
            self.update_ui_state()

    def show_about(self):
        about_text = """
AMIS Normalization Tool v6

Author: Kravtsov G.
Research Center "Applied Statistics"

Features:
- Mean normalization method only
- Key points grid lines (green for 25/75)
- Adaptive model selection (3/5/9/17 points)
- File comparison and correspondence tables
"""
        messagebox.showinfo("About", about_text)

    def show_help(self):
        help_text = """
HOW TO USE:

1. Load File 1 and File 2 (Excel/CSV)
2. Normalize each file (always uses Mean method)
3. Click "All Comparison Graphs" to see results

GRID LINES:
- Green horizontal/vertical lines at Y = 25 and 75
- Orange line at Y = 50 (center)
- Gray lines at Y = 0 and 100
- Green vertical lines at control points
"""
        messagebox.showinfo("Help", help_text)


if __name__ == "__main__":
    app = AMISApp()
    app.mainloop()