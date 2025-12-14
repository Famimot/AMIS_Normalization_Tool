"""
Main AMIS Application Window
Simplified version - single data type support
WITH ADAPTIVE MODEL SELECTION
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

from amis_tool.core.amis_calculations import amis_safe_conversion, load_data_to_array
from amis_tool.gui.dialogs import AMISComparisonDialog
from amis_tool.gui.widgets import TableViewer
from amis_tool.utils.helpers import center_window


class AMISApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # Main window configuration
        self.title("AMIS Normalization Tool v4.3")
        self.geometry("1250x900")
        self.minsize(1100, 800)

        # Exception handler
        self.report_callback_exception = self._handle_exception

        # Logging initialization
        self.setup_logging()

        # Data variables
        self.data1 = None          # Full DataFrame for file 1
        self.data2 = None          # Full DataFrame for file 2
        self.path1 = None
        self.path2 = None
        self.df_raw1 = None        # Raw values array for file 1
        self.df_raw2 = None        # Raw values array for file 2
        self.value_col1 = None
        self.value_col2 = None
        self.converted1 = None
        self.converted2 = None
        self.points_coords1 = None
        self.points_coords2 = None

        # Adaptive models selection variables
        self.available_models1 = None  # Available models for file 1
        self.available_models2 = None  # Available models for file 2

        # File statuses
        self.file1_status = "empty"
        self.file2_status = "empty"

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
        # Update status colors
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

        # Update status texts
        status_texts = {
            "empty": "File not loaded",
            "loaded": "File loaded",
            "normalized": "File normalized",
            "ready": "Ready for comparison"
        }
        self.file1_status_label.config(text=status_texts.get(self.file1_status, ""))
        self.file2_status_label.config(text=status_texts.get(self.file2_status, ""))

        # Update buttons
        file1_loaded = self.file1_status != "empty"
        file2_loaded = self.file2_status != "empty"
        file1_normalized = self.file1_status in ["normalized", "ready"]
        file2_normalized = self.file2_status in ["normalized", "ready"]
        both_normalized = file1_normalized and file2_normalized

        # Normalization buttons
        self.norm1_btn.config(state=tk.NORMAL if (file1_loaded and self.file1_status == "loaded") else tk.DISABLED)
        self.norm2_btn.config(state=tk.NORMAL if (file2_loaded and self.file2_status == "loaded") else tk.DISABLED)

        # View normalized data buttons
        self.view_norm1_btn.config(state=tk.NORMAL if file1_normalized else tk.DISABLED)
        self.view_norm2_btn.config(state=tk.NORMAL if file2_normalized else tk.DISABLED)

        self.compare_btn.config(state=tk.NORMAL if both_normalized else tk.DISABLED)
        self.all_graphs_btn.config(state=tk.NORMAL if both_normalized else tk.DISABLED)

        # AMIS comparison buttons (renamed to "Graph" for clarity)
        self.amis_comp1_btn.config(state=tk.NORMAL if file1_normalized else tk.DISABLED)
        self.amis_comp2_btn.config(state=tk.NORMAL if file2_normalized else tk.DISABLED)

    def create_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="📁 Load File 1", command=lambda: self.load_first_file())
        file_menu.add_command(label="📁 Load File 2", command=lambda: self.load_second_file())
        file_menu.add_separator()
        file_menu.add_command(label="📊 View Table 1", command=lambda: self.show_table(1))
        file_menu.add_command(label="📊 View Table 2", command=lambda: self.show_table(2))
        file_menu.add_command(label="📊 Show Normalized 1",
                            command=lambda: self.show_normalized_table(1))
        file_menu.add_command(label="📊 Show Normalized 2",
                            command=lambda: self.show_normalized_table(2))
        file_menu.add_separator()
        file_menu.add_command(label="🗑️ Clear All", command=lambda: self.clear_all())
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Exit", command=self.quit)

        # Processing menu
        process_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Processing", menu=process_menu)
        process_menu.add_command(label="⚙️ Normalize File 1", command=lambda: self.normalize_first())
        process_menu.add_command(label="⚙️ Normalize File 2", command=lambda: self.normalize_second())
        process_menu.add_separator()
        process_menu.add_command(label="📊 Compare Files", command=lambda: self.compare_files())

        # Visualization menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Visualization", menu=view_menu)
        # Order changed: method comparison first, then all graphs
        view_menu.add_command(label="📈 Graph (File 1)",
                            command=lambda: self.show_amis_comparison(1))
        view_menu.add_command(label="📈 Graph (File 2)",
                            command=lambda: self.show_amis_comparison(2))
        view_menu.add_separator()
        view_menu.add_command(label="📊 All Graphs", command=lambda: self.plot_comparison_graphs())

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="📖 About", command=lambda: self.show_about())
        help_menu.add_command(label="❓ How to Use", command=lambda: self.show_help())

    def create_widgets(self):
        """Create interface widgets"""
        # Main container
        main_container = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - data tables
        left_panel = ttk.Frame(main_container)
        main_container.add(left_panel, weight=3)

        # Right panel - controls
        right_panel = ttk.Frame(main_container)
        main_container.add(right_panel, weight=1)

        # === LEFT PANEL: Data Tables ===
        # Top table - file 1
        self.table1 = TableViewer(left_panel, title="File 1:")
        self.table1.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))

        # File 1 status
        self.file1_status_frame = ttk.Frame(left_panel, relief=tk.RIDGE, borderwidth=1)
        self.file1_status_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.file1_status_label = ttk.Label(self.file1_status_frame, text="File not loaded",
                                          font=('Arial', 10))
        self.file1_status_label.pack(pady=3)

        # Bottom table - file 2
        self.table2 = TableViewer(left_panel, title="File 2:")
        self.table2.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))

        # File 2 status
        self.file2_status_frame = ttk.Frame(left_panel, relief=tk.RIDGE, borderwidth=1)
        self.file2_status_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.file2_status_label = ttk.Label(self.file2_status_frame, text="File not loaded",
                                          font=('Arial', 10))
        self.file2_status_label.pack(pady=3)

        # === RIGHT PANEL: Controls ===
        control_frame = ttk.LabelFrame(right_panel, text="Control", padding="10")
        control_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # File loading group
        load_frame = ttk.LabelFrame(control_frame, text="📁 File Loading", padding="10")
        load_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(load_frame, text="📁 LOAD FILE 1",
                  command=lambda: self.load_first_file()).pack(fill=tk.X, pady=3)
        ttk.Button(load_frame, text="📁 LOAD FILE 2",
                  command=lambda: self.load_second_file()).pack(fill=tk.X, pady=3)

        # Processing group
        process_frame = ttk.LabelFrame(control_frame, text="⚙️ Data Processing", padding="10")
        process_frame.pack(fill=tk.X, pady=(0, 10))

        self.norm1_btn = ttk.Button(process_frame, text="⚙️ NORMALIZE FILE 1",
                                   command=lambda: self.normalize_first(), state=tk.DISABLED)
        self.norm1_btn.pack(fill=tk.X, pady=3)

        self.norm2_btn = ttk.Button(process_frame, text="⚙️ NORMALIZE FILE 2",
                                   command=lambda: self.normalize_second(), state=tk.DISABLED)
        self.norm2_btn.pack(fill=tk.X, pady=3)

        # View normalized data buttons
        self.view_norm1_btn = ttk.Button(process_frame, text="📊 SHOW NORMALIZED 1",
                                        command=lambda: self.show_normalized_table(1),
                                        state=tk.DISABLED)
        self.view_norm1_btn.pack(fill=tk.X, pady=3)

        self.view_norm2_btn = ttk.Button(process_frame, text="📊 SHOW NORMALIZED 2",
                                        command=lambda: self.show_normalized_table(2),
                                        state=tk.DISABLED)
        self.view_norm2_btn.pack(fill=tk.X, pady=3)

        self.compare_btn = ttk.Button(process_frame, text="📊 COMPARE FILES",
                                     command=lambda: self.compare_files(), state=tk.DISABLED)
        self.compare_btn.pack(fill=tk.X, pady=3)

        # AMIS methods comparison (moved up)
        amis_comp_frame = ttk.LabelFrame(control_frame, text="📈 AMIS Graphs", padding="10")
        amis_comp_frame.pack(fill=tk.X, pady=(0, 10))

        self.amis_comp1_btn = ttk.Button(amis_comp_frame, text="📈 GRAPH (File 1)",
                                        command=lambda: self.show_amis_comparison(1), state=tk.DISABLED)
        self.amis_comp1_btn.pack(fill=tk.X, pady=3)

        self.amis_comp2_btn = ttk.Button(amis_comp_frame, text="📈 GRAPH (File 2)",
                                        command=lambda: self.show_amis_comparison(2), state=tk.DISABLED)
        self.amis_comp2_btn.pack(fill=tk.X, pady=3)

        # Visualization group
        viz_frame = ttk.LabelFrame(control_frame, text="📈 Visualization", padding="10")
        viz_frame.pack(fill=tk.X, pady=(0, 10))

        self.all_graphs_btn = ttk.Button(viz_frame, text="📊 ALL GRAPHS",
                                        command=lambda: self.plot_comparison_graphs(), state=tk.DISABLED)
        self.all_graphs_btn.pack(fill=tk.X, pady=3)

        # Management group
        manage_frame = ttk.LabelFrame(control_frame, text="⚙️ Management", padding="10")
        manage_frame.pack(fill=tk.X)

        ttk.Button(manage_frame, text="🗑️ CLEAR ALL",
                  command=lambda: self.clear_all()).pack(fill=tk.X, pady=3)
        ttk.Button(manage_frame, text="🚪 EXIT",
                  command=self.quit).pack(fill=tk.X, pady=3)

        # === BOTTOM PANEL: Work Log ===
        bottom_panel = ttk.Frame(self)
        bottom_panel.pack(fill=tk.X, padx=5, pady=(0, 5))

        log_frame = ttk.LabelFrame(bottom_panel, text="📝 Work Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Text field for log
        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD, font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Status bar
        self.status_var = tk.StringVar(value="Ready to work")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN,
                              font=('Arial', 9))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)

        # Style configuration for statuses
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

        # Color formatting
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("info", foreground="blue")

        # Write to log file
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

        # Result folders
        tables_dir = os.path.join(base_dir, "converted_tables")
        plots_dir = os.path.join(base_dir, "plots")

        # Create folders if they don't exist
        os.makedirs(tables_dir, exist_ok=True)
        os.makedirs(plots_dir, exist_ok=True)

        # Form file names
        if suffix:
            filename = f"{filename}_{suffix}"

        table_path = os.path.join(tables_dir, f"{filename}.xlsx")
        plot_path = os.path.join(plots_dir, f"{filename}.png")

        return tables_dir, plots_dir, table_path, plot_path, filename

    def load_first_file(self):
        """Load first file"""
        self._load_file(1)

    def load_second_file(self):
        """Load second file"""
        self._load_file(2)

    def _load_file(self, file_num):
        """General file loading function - simplified version"""
        try:
            file_path = filedialog.askopenfilename(
                title=f"Select File {file_num}",
                filetypes=[("Excel/CSV", "*.xlsx *.xls *.csv"),
                          ("All files", "*.*")]
            )

            if not file_path:
                return

            self.log_action(f"Loading file {file_num}: {os.path.basename(file_path)}")

            # Read file
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            if df.empty:
                raise ValueError("File is empty")

            self.log_action(f"✅ Loaded: {len(df)} rows, {len(df.columns)} columns")

            # Save data - PASS FULL DATAFRAME, not just first 100 rows
            if file_num == 1:
                self.data1 = df  # Store full DataFrame
                self.path1 = file_path
                self.file1_status = "loaded"
                self.table1.set_original_data(df, "raw data")  # Pass full DataFrame
            else:
                self.data2 = df  # Store full DataFrame
                self.path2 = file_path
                self.file2_status = "loaded"
                self.table2.set_original_data(df, "raw data")  # Pass full DataFrame

            self.log_action(f"✅ File {file_num} successfully loaded", "success")
            self.update_ui_state()

        except Exception as e:
            self.log_action(f"❌ File loading error: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")

    def normalize_first(self):
        """Normalize first file"""
        if self.data1 is None:
            messagebox.showwarning("Warning", "First load file 1")
            return

        self._normalize_file(1)

    def normalize_second(self):
        """Normalize second file"""
        if self.data2 is None:
            messagebox.showwarning("Warning", "First load file 2")
            return

        self._normalize_file(2)

    def _normalize_file(self, file_num):
        """General normalization function - simplified version WITH ADAPTIVE MODELS"""
        try:
            self.log_action(f"🔄 Starting normalization of file {file_num}...")

            # Get data
            if file_num == 1:
                data = self.data1
                path = self.path1
            else:
                data = self.data2
                path = self.path2

            # Load data to array (second column contains values)
            raw_data, value_col, labels = load_data_to_array(data)

            # AMIS conversion with automatic bounds and ADAPTIVE MODEL SELECTION
            # Returns THREE values: converted, points_coords, available_models
            converted, points_coords, available_models = amis_safe_conversion(raw_data, None, None)

            # Log information about available models
            n = len(raw_data)
            available_count = len(available_models)

            # Show information about available models
            model_info = self.get_model_availability_info(n, available_models)
            self.show_model_info_dialog(file_num, n, available_count, model_info)

            self.log_action(f"📊 Data volume: {n} points → {available_count} models available", "info")

            # Show available models in log
            if available_models:
                model_names = ", ".join([available_models[key] for key in available_models])
                self.log_action(f"✅ Available models: {model_names}", "success")

            # Save results
            tables_dir, plots_dir, table_path, _, _ = self.get_output_paths(
                path, f"AMIS_{file_num}"
            )

            # Create DataFrame with normalized data (only available models)
            # FIRST COLUMN: Keep original labels (country names, IDs, etc.)
            result_dict = {
                data.columns[0]: labels[:len(raw_data)],  # Original first column
                f"{value_col}_raw": raw_data
            }

            # Add only available models
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
            df_result.to_excel(table_path, index=False)

            # Save results in object
            if file_num == 1:
                self.df_raw1 = raw_data
                self.value_col1 = value_col
                self.converted1 = converted
                self.points_coords1 = points_coords
                self.available_models1 = available_models  # Save available models
                self.file1_status = "normalized"
                # Pass complete DataFrame to table
                self.table1.set_normalized_data(df_result)
            else:
                self.df_raw2 = raw_data
                self.value_col2 = value_col
                self.converted2 = converted
                self.points_coords2 = points_coords
                self.available_models2 = available_models  # Save available models
                self.file2_status = "normalized"
                # Pass complete DataFrame to table
                self.table2.set_normalized_data(df_result)

            self.log_action(f"✅ File {file_num} successfully normalized", "success")
            self.log_action(f"💾 Results saved in: {tables_dir}")

            # If both files normalized, change status
            if (file_num == 1 and self.file2_status == "normalized") or \
                    (file_num == 2 and self.file1_status == "normalized"):
                self.file1_status = "ready"
                self.file2_status = "ready"

            self.update_ui_state()

            # Show info about adaptive models
            info_message = f"File {file_num} normalized!\n\n"
            info_message += f"Data volume: {n} points\n"
            info_message += f"Available models: {available_count}/5\n"
            info_message += f"\nResults saved in:\n{table_path}\n\n"
            info_message += f"Tables folder: {tables_dir}\n"
            info_message += f"Plots folder: {plots_dir}"

            messagebox.showinfo("Done", info_message)

        except Exception as e:
            self.log_action(f"❌ Normalization error: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to normalize file:\n{str(e)}")

    def get_model_availability_info(self, n, available_models):
        """Get detailed information about model availability"""
        models = {
            "linear": {"name": "Linear", "min_points": 10},
            "3_points": {"name": "3-point", "min_points": 10},
            "5_points": {"name": "5-point", "min_points": 20},
            "9_points": {"name": "9-point", "min_points": 50},
            "17_points": {"name": "17-point", "min_points": 100}
        }

        info = {
            "available": [],
            "unavailable": [],
            "requirements": []
        }

        for model_key, model_data in models.items():
            if model_key in available_models:
                info["available"].append(model_data["name"])
            else:
                info["unavailable"].append(model_data["name"])
                needed = model_data["min_points"] - n
                if needed > 0:
                    info["requirements"].append(
                        f"{model_data['name']}: add {needed} more point{'s' if needed > 1 else ''}"
                    )

        return info

    def show_model_info_dialog(self, file_num, n, available_count, model_info):
        """Show dialog with model availability information - Elegant table version"""
        dialog = tk.Toplevel(self)
        dialog.title("Adaptive Model Selection")
        dialog.geometry("750x400")  # Compact and elegant
        dialog.transient(self)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding="25")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header with information
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 25))

        ttk.Label(header_frame, text="Adaptive Model Selection",
                  font=('Arial', 16, 'bold')).pack(side=tk.LEFT)

        info_text = f"• File {file_num} • {n} points • {available_count}/5 models"
        ttk.Label(header_frame, text=info_text,
                  font=('Arial', 10), foreground="gray").pack(side=tk.RIGHT)

        # Model table
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Table headers
        headers = ["Model", "Min Points", "Status", "Your Data", "Action"]
        for col, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=('Arial', 11, 'bold'),
                      relief=tk.RIDGE, padding=5).grid(row=0, column=col, sticky="nsew", padx=1, pady=1)

        # Model data
        models = [
            ("Linear", 10, "linear"),
            ("3-point", 10, "3_points"),
            ("5-point", 20, "5_points"),
            ("9-point", 50, "9_points"),
            ("17-point", 100, "17_points")
        ]

        for row, (name, min_points, key) in enumerate(models, 1):
            # Model
            ttk.Label(table_frame, text=name, padding=5).grid(
                row=row, column=0, sticky="nsew", padx=1, pady=1)

            # Minimum points
            ttk.Label(table_frame, text=f"{min_points}+", padding=5).grid(
                row=row, column=1, sticky="nsew", padx=1, pady=1)

            # Status
            if min_points <= n:
                status_label = ttk.Label(table_frame, text="✓ AVAILABLE",
                                         foreground="green", padding=5)
            else:
                status_label = ttk.Label(table_frame, text="✗ LOCKED",
                                         foreground="red", padding=5)
            status_label.grid(row=row, column=2, sticky="nsew", padx=1, pady=1)

            # Your data
            if min_points <= n:
                data_text = f"✓ You have {n} points"
                fg_color = "green"
            else:
                data_text = f"✗ You have {n}/{min_points}"
                fg_color = "orange"
            ttk.Label(table_frame, text=data_text, foreground=fg_color,
                      padding=5).grid(row=row, column=3, sticky="nsew", padx=1, pady=1)

            # Action
            if min_points <= n:
                action_text = "Ready to use"
                fg_color = "green"
            else:
                needed = min_points - n
                action_text = f"Add {needed} points"
                fg_color = "blue"
            ttk.Label(table_frame, text=action_text, foreground=fg_color,
                      padding=5).grid(row=row, column=4, sticky="nsew", padx=1, pady=1)

        # Column weight configuration
        for col in range(5):
            table_frame.columnconfigure(col, weight=1)

        # Separator
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Brief information
        if available_count < 5:
            note_text = f"📈 To unlock all 5 models, you need {max(0, 100 - n)} more data points."
            note_label = ttk.Label(main_frame, text=note_text,
                                   font=('Arial', 9), wraplength=650)
            note_label.pack(pady=(0, 15))

        # Button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Continue with Available Models",
                   command=dialog.destroy).pack()

        center_window(dialog)
        self.wait_window(dialog)

    def show_normalized_table(self, file_num):
        """Show normalized data table"""
        if file_num == 1:
            if not self.converted1:
                messagebox.showwarning("Warning", "First normalize file 1")
                return

            # Switch table to normalized data mode
            self.table1.showing_normalized = True
            self.table1.mode_btn.config(text="Normalized")
            if self.table1.normalized_data is not None:
                self.table1.update_data(self.table1.normalized_data, "normalized")

            self.log_action("📊 Showing normalized data for file 1", "info")

        else:
            if not self.converted2:
                messagebox.showwarning("Warning", "First normalize file 2")
                return

            # Switch table to normalized data mode
            self.table2.showing_normalized = True
            self.table2.mode_btn.config(text="Normalized")
            if self.table2.normalized_data is not None:
                self.table2.update_data(self.table2.normalized_data, "normalized")

            self.log_action("📊 Showing normalized data for file 2", "info")

    def compare_files(self):
        """Compare files"""
        if not all([self.converted1, self.converted2]):
            self.log_action("❌ Both files must be normalized", "warning")
            messagebox.showwarning("Warning", "First normalize both files")
            return

        try:
            self.log_action("📊 Starting file comparison...")

            # Prepare comparison data - FIXED POINT SELECTION LOGIC
            y_amis = np.linspace(0, 100, 101)

            # Determine which model to use for comparison
            # Use maximum available model that exists in both files
            if "y_17" in self.points_coords1 and "y_17" in self.points_coords2:
                y_points = self.points_coords1['y_17']
                inv1 = interp1d(y_points, self.points_coords1['x_17'],
                              kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_17'],
                              kind='linear', fill_value='extrapolate', bounds_error=False)
            elif "y_9" in self.points_coords1 and "y_9" in self.points_coords2:
                y_points = self.points_coords1['y_9']
                inv1 = interp1d(y_points, self.points_coords1['x_9'],
                              kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_9'],
                              kind='linear', fill_value='extrapolate', bounds_error=False)
            elif "y_5" in self.points_coords1 and "y_5" in self.points_coords2:
                y_points = self.points_coords1['y_5']
                inv1 = interp1d(y_points, self.points_coords1['x_5'],
                              kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_5'],
                              kind='linear', fill_value='extrapolate', bounds_error=False)
            elif "y_3" in self.points_coords1 and "y_3" in self.points_coords2:
                y_points = self.points_coords1['y_3']
                inv1 = interp1d(y_points, self.points_coords1['x_3'],
                              kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_3'],
                              kind='linear', fill_value='extrapolate', bounds_error=False)
            else:
                # Use linear if nothing else is available
                y_points = self.points_coords1['y_line']
                inv1 = interp1d(y_points, self.points_coords1['x_line'],
                              kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_line'],
                              kind='linear', fill_value='extrapolate', bounds_error=False)

            df_comp = pd.DataFrame({
                "AMIS": y_amis,
                self.value_col1: inv1(y_amis),
                self.value_col2: inv2(y_amis)
            })

            # Save comparison table
            base_dir = os.path.dirname(self.path1)
            tables_dir = os.path.join(base_dir, "converted_tables")
            os.makedirs(tables_dir, exist_ok=True)
            out_file = os.path.join(tables_dir, "AMIS_comparison.xlsx")
            df_comp.to_excel(out_file, index=False)

            self.log_action("✅ Comparison completed", "success")
            self.log_action(f"💾 Comparison table saved: {out_file}")

            messagebox.showinfo("Done", f"Comparison table saved:\n{out_file}")

        except Exception as e:
            self.log_action(f"❌ Comparison error: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to compare files:\n{str(e)}")

    def show_amis_comparison(self, file_num):
        """Show AMIS methods comparison window WITH ADAPTIVE MODELS"""
        try:
            if file_num == 1:
                if not self.points_coords1 or self.path1 is None:
                    messagebox.showwarning("Warning", "First normalize file 1")
                    return
                dialog = AMISComparisonDialog(self, file_num,
                                             self.points_coords1,
                                             self.value_col1,
                                             self.path1,
                                             self.available_models1)  # Pass available models
            else:
                if not self.points_coords2 or self.path2 is None:
                    messagebox.showwarning("Warning", "First normalize file 2")
                    return
                dialog = AMISComparisonDialog(self, file_num,
                                             self.points_coords2,
                                             self.value_col2,
                                             self.path2,
                                             self.available_models2)  # Pass available models

            # === FIX: Make dialog modal and manage focus ===
            dialog.transient(self)  # Make window dependent on main window
            dialog.grab_set()  # Capture focus

            # Set close handler
            def on_close():
                self.lift()
                self.focus_force()
                dialog.destroy()

            dialog.protocol("WM_DELETE_WINDOW", on_close)

            self.log_action(f"🎯 Opened AMIS methods comparison for file {file_num}", "info")

            # Wait for dialog to close
            self.wait_window(dialog)
            self.lift()  # Raise main window after dialog closes
            self.focus_force()

        except Exception as e:
            self.log_action(f"❌ Error opening AMIS comparison: {str(e)}", "error")
            messagebox.showerror("Error", f"Cannot open AMIS comparison:\n{str(e)}")

    def plot_comparison_graphs(self):
        """Plot all comparison graphs WITH ADAPTIVE MODELS"""
        if not all([self.points_coords1, self.points_coords2]):
            messagebox.showwarning("Warning", "First normalize both files")
            return

        try:
            # Get saving paths
            base_dir = os.path.dirname(self.path1)
            tables_dir = os.path.join(base_dir, "converted_tables")
            plots_dir = os.path.join(base_dir, "plots")
            os.makedirs(plots_dir, exist_ok=True)

            # Create Tkinter window for graphs
            graphs_window = tk.Toplevel(self)
            graphs_window.title("AMIS - File Comparison")
            graphs_window.geometry("1250x1000")

            # === FIX: Make window dependent and manage focus ===
            graphs_window.transient(self)  # Make window dependent on main window
            graphs_window.grab_set()  # Capture focus

            # Create main container
            main_container = ttk.Frame(graphs_window)
            main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Create Matplotlib figure
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            fig = Figure(figsize=(11, 8), dpi=100)

            # Graph 1: File 1
            ax1 = fig.add_subplot(221)
            if "x_line" in self.points_coords1 and len(self.points_coords1["x_line"]) > 0:
                x1_range = np.linspace(np.min(self.points_coords1["x_line"]),
                                      np.max(self.points_coords1["x_line"]), 300)
            else:
                x1_range = np.linspace(0, 1, 300)

            # Plot available models for file 1
            if "x_line" in self.points_coords1:
                ax1.plot(x1_range, interp1d(self.points_coords1["x_line"],
                                            self.points_coords1["y_line"], kind="linear",
                                            fill_value="extrapolate")(x1_range),
                         'k-', lw=1.5, label="Lin")

            if "x_3" in self.points_coords1 and "3_points" in self.available_models1:
                ax1.plot(x1_range, interp1d(self.points_coords1["x_3"],
                                            self.points_coords1["y_3"], kind="linear",
                                            fill_value="extrapolate")(x1_range),
                         'm:', lw=2, label="3")
                ax1.scatter(self.points_coords1["x_3"], self.points_coords1["y_3"],
                            c='m', s=30, zorder=4)

            if "x_5" in self.points_coords1 and "5_points" in self.available_models1:
                ax1.plot(x1_range, interp1d(self.points_coords1["x_5"],
                                            self.points_coords1["y_5"], kind="linear",
                                            fill_value="extrapolate")(x1_range),
                         'g--', lw=2, label="5")
                ax1.scatter(self.points_coords1["x_5"], self.points_coords1["y_5"],
                            c='g', s=35, zorder=4)

            if "x_9" in self.points_coords1 and "9_points" in self.available_models1:
                ax1.plot(x1_range, interp1d(self.points_coords1["x_9"],
                                            self.points_coords1["y_9"], kind="linear",
                                            fill_value="extrapolate")(x1_range),
                         'r-.', lw=2.5, label="9")
                ax1.scatter(self.points_coords1["x_9"], self.points_coords1["y_9"],
                            c='r', s=40, zorder=4)

            if "x_17" in self.points_coords1 and "17_points" in self.available_models1:
                ax1.plot(x1_range, interp1d(self.points_coords1["x_17"],
                                            self.points_coords1["y_17"], kind="linear",
                                            fill_value="extrapolate")(x1_range),
                         'b-', lw=3, label="17")
                ax1.scatter(self.points_coords1["x_17"], self.points_coords1["y_17"],
                            c='b', s=50, zorder=5)

            ax1.set_title(f"File 1: {self.value_col1}", fontsize=12, fontweight='bold')
            ax1.set_xlabel(self.value_col1, fontsize=10, fontweight='bold')
            ax1.set_ylabel("AMIS", fontsize=10, fontweight='bold')
            ax1.legend(fontsize=8)
            ax1.grid(True, alpha=0.3)
            ax1.axhline(50, color='orange', lw=2)

            # Graph 2: File 2
            ax2 = fig.add_subplot(222)
            if "x_line" in self.points_coords2 and len(self.points_coords2["x_line"]) > 0:
                x2_range = np.linspace(np.min(self.points_coords2["x_line"]),
                                      np.max(self.points_coords2["x_line"]), 300)
            else:
                x2_range = np.linspace(0, 1, 300)

            # Plot available models for file 2
            if "x_line" in self.points_coords2:
                ax2.plot(x2_range, interp1d(self.points_coords2["x_line"],
                                            self.points_coords2["y_line"], kind="linear",
                                            fill_value="extrapolate")(x2_range),
                         'k-', lw=1.5, label="Lin")

            if "x_3" in self.points_coords2 and "3_points" in self.available_models2:
                ax2.plot(x2_range, interp1d(self.points_coords2["x_3"],
                                            self.points_coords2["y_3"], kind="linear",
                                            fill_value="extrapolate")(x2_range),
                         'm:', lw=2, label="3")
                ax2.scatter(self.points_coords2["x_3"], self.points_coords2["y_3"],
                            c='m', s=30, zorder=4)

            if "x_5" in self.points_coords2 and "5_points" in self.available_models2:
                ax2.plot(x2_range, interp1d(self.points_coords2["x_5"],
                                            self.points_coords2["y_5"], kind="linear",
                                            fill_value="extrapolate")(x2_range),
                         'g--', lw=2, label="5")
                ax2.scatter(self.points_coords2["x_5"], self.points_coords2["y_5"],
                            c='g', s=35, zorder=4)

            if "x_9" in self.points_coords2 and "9_points" in self.available_models2:
                ax2.plot(x2_range, interp1d(self.points_coords2["x_9"],
                                            self.points_coords2["y_9"], kind="linear",
                                            fill_value="extrapolate")(x2_range),
                         'r-.', lw=2.5, label="9")
                ax2.scatter(self.points_coords2["x_9"], self.points_coords2["y_9"],
                            c='r', s=40, zorder=4)

            if "x_17" in self.points_coords2 and "17_points" in self.available_models2:
                ax2.plot(x2_range, interp1d(self.points_coords2["x_17"],
                                            self.points_coords2["y_17"], kind="linear",
                                            fill_value="extrapolate")(x2_range),
                         'b-', lw=3, label="17")
                ax2.scatter(self.points_coords2["x_17"], self.points_coords2["y_17"],
                            c='b', s=50, zorder=5)

            ax2.set_title(f"File 2: {self.value_col2}", fontsize=12, fontweight='bold')
            ax2.set_xlabel(self.value_col2, fontsize=10, fontweight='bold')
            ax2.set_ylabel("AMIS", fontsize=10, fontweight='bold')
            ax2.legend(fontsize=8)
            ax2.grid(True, alpha=0.3)
            ax2.axhline(50, color='orange', lw=2)

            # Graph 3: Correspondence - FIXED BLOCK
            ax3 = fig.add_subplot(223)
            y_amis = np.linspace(0, 100, 101)

            # Determine maximum available model for both files
            if "y_17" in self.points_coords1 and "y_17" in self.points_coords2:
                y_points = self.points_coords1['y_17']
                inv1 = interp1d(y_points, self.points_coords1['x_17'],
                                kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_17'],
                                kind='linear', fill_value='extrapolate', bounds_error=False)
            elif "y_9" in self.points_coords1 and "y_9" in self.points_coords2:
                y_points = self.points_coords1['y_9']
                inv1 = interp1d(y_points, self.points_coords1['x_9'],
                                kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_9'],
                                kind='linear', fill_value='extrapolate', bounds_error=False)
            elif "y_5" in self.points_coords1 and "y_5" in self.points_coords2:
                y_points = self.points_coords1['y_5']
                inv1 = interp1d(y_points, self.points_coords1['x_5'],
                                kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_5'],
                                kind='linear', fill_value='extrapolate', bounds_error=False)
            elif "y_3" in self.points_coords1 and "y_3" in self.points_coords2:
                y_points = self.points_coords1['y_3']
                inv1 = interp1d(y_points, self.points_coords1['x_3'],
                                kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_3'],
                                kind='linear', fill_value='extrapolate', bounds_error=False)
            else:
                # Use linear if nothing else is available
                y_points = self.points_coords1['y_line']
                inv1 = interp1d(y_points, self.points_coords1['x_line'],
                                kind='linear', fill_value='extrapolate', bounds_error=False)
                inv2 = interp1d(y_points, self.points_coords2['x_line'],
                                kind='linear', fill_value='extrapolate', bounds_error=False)

            nom1 = inv1(y_amis)
            nom2 = inv2(y_amis)

            ax3.plot(nom1, nom2, 'darkgreen', marker='o', markersize=4, linewidth=3)
            ax3.set_title("AMIS Correspondence", fontsize=12, fontweight='bold')
            ax3.set_xlabel(f"{self.value_col1}", fontsize=10, fontweight='bold')
            ax3.set_ylabel(f"{self.value_col2}", fontsize=10, fontweight='bold')
            ax3.grid(True, alpha=0.3)

            # Graph 4: Double Y
            ax4 = fig.add_subplot(224)
            ax4.plot(y_amis, nom1, 'blue', marker='o', markersize=5, linewidth=2.5,
                     label=f"{self.value_col1}")
            ax4.set_xlabel("AMIS (0-100)", fontsize=10, fontweight='bold')
            ax4.set_ylabel(f"{self.value_col1}", color='blue', fontsize=10, fontweight='bold')
            ax4.tick_params(axis='y', labelcolor='blue')

            ax4_2 = ax4.twinx()
            ax4_2.plot(y_amis, nom2, 'red', marker='s', markersize=5, linewidth=2.5,
                       label=f"{self.value_col2}")
            ax4_2.set_ylabel(f"{self.value_col2}", color='red', fontsize=10, fontweight='bold')
            ax4_2.tick_params(axis='y', labelcolor='red')

            ax4.set_title("Comparison by AMIS Scale", fontsize=12, fontweight='bold')
            ax4.legend(loc='upper left', fontsize=8)
            ax4_2.legend(loc='upper right', fontsize=8)
            ax4.grid(True, alpha=0.3)

            fig.tight_layout()

            # Save graph
            plot_path = os.path.join(plots_dir, "AMIS_comparison_graphs.png")
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            self.log_action(f"💾 Comparison graphs saved: {plot_path}", "success")

            # Embed graph in Tkinter window
            canvas = FigureCanvasTkAgg(fig, master=main_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # Create button frame at the bottom
            button_frame = ttk.Frame(graphs_window)
            button_frame.pack(fill=tk.X, padx=10, pady=5)

            # Save button
            save_btn = ttk.Button(button_frame, text="💾 Save All Graphs",
                                  command=lambda: self.save_comparison_figure(fig, self.path1, "AMIS_comparison_graphs"))
            save_btn.pack(side=tk.LEFT, padx=5)

            # Close button
            close_btn = ttk.Button(button_frame, text="❌ Close",
                                   command=lambda: [self.lift(), self.focus_force(), graphs_window.destroy()])
            close_btn.pack(side=tk.RIGHT, padx=5)

            # Close handler for X button
            graphs_window.protocol("WM_DELETE_WINDOW",
                                  lambda: [self.lift(), self.focus_force(), graphs_window.destroy()])

            # Center window
            center_window(graphs_window)

            # Wait for window to close
            self.wait_window(graphs_window)
            self.lift()  # Raise main window after closing
            self.focus_force()

        except Exception as e:
            self.log_action(f"❌ Graph plotting error: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to plot graphs:\n{str(e)}")

    def save_comparison_figure(self, fig, file_path, suffix):
        """Save comparison figure to file"""
        try:
            tables_dir, plots_dir, _, plot_path, _ = self.get_output_paths(file_path, suffix)

            # Save in multiple formats
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')

            # Also save as PDF
            pdf_path = plot_path.replace('.png', '.pdf')
            fig.savefig(pdf_path, bbox_inches='tight')

            self.log_action(f"💾 Comparison graphs saved in PNG and PDF formats", "success")
            messagebox.showinfo("Saved", f"Comparison graphs saved:\n\nPNG: {plot_path}\nPDF: {pdf_path}")

        except Exception as e:
            self.log_action(f"❌ Graph saving error: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to save comparison graphs:\n{str(e)}")

    def show_table(self, num):
        """Show table in separate window"""
        if num == 1 and self.data1 is None:
            messagebox.showwarning("Warning", "First load file 1")
            return
        elif num == 2 and self.data2 is None:
            messagebox.showwarning("Warning", "First load file 2")
            return

        data = self.data1 if num == 1 else self.data2
        path = self.path1 if num == 1 else self.path2

        # Create separate window for table
        table_window = tk.Toplevel(self)
        table_window.title(f"Data Table - File {num}: {os.path.basename(path)}")
        table_window.geometry("900x600")

        # Create table
        table_frame = TableViewer(table_window, title=f"File {num}: data")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        table_frame.set_original_data(data, "raw data")

        center_window(table_window)

    def clear_all(self):
        """Clear all data"""
        if messagebox.askyesno("Confirmation", "Are you sure you want to clear all data?"):
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
            self.available_models1 = None  # Clear available models
            self.available_models2 = None  # Clear available models
            self.file1_status = "empty"
            self.file2_status = "empty"

            self.table1.clear()
            self.table2.clear()
            self.log_text.delete(1.0, tk.END)
            self.log_action("🗑️ All data cleared", "info")
            self.update_ui_state()

    def show_about(self):
        """Show program information"""
        about_text = """
AMIS Normalization Tool v4.3

📊 Program for data normalization using AMIS method
WITH ADAPTIVE MODEL SELECTION

Author: Kravtsov G.
Research Center "Applied Statistics"
E-mail: 62abc@mail.ru

Features:
✅ Adaptive model selection based on data volume
✅ N < 10 → Error (minimum 10 points required)
✅ N = 10-19 → Linear + 3-point model
✅ N = 20-49 → + 5-point model
✅ N = 50-99 → + 9-point model
✅ N ≥ 100 → All 5 models (Linear, 3, 5, 9, 17 points)

Version 4.3 includes:
• Adaptive model selection
• Single data type support
• Improved stability
• Automatic bounds calculation
"""
        messagebox.showinfo("About", about_text)

    def show_help(self):
        """Show help"""
        help_text = """
📖 HOW TO USE THE PROGRAM - ADAPTIVE VERSION:

1. DATA LOADING
   • Click "Load File 1" or "Load File 2"
   • Select file (Excel or CSV format)
   • File should have at least 2 columns
   • Minimum 10 data points required

2. NORMALIZATION WITH ADAPTIVE MODELS
   • After loading click "Normalize"
   • Program automatically selects available models:
     - 10-19 points → Linear + 3-point model
     - 20-49 points → + 5-point model
     - 50-99 points → + 9-point model
     - 100+ points → All 5 models
   • Uses automatic bounds (min/max of data)

3. VIEWING RESULTS
   • Use "Original/Normalized" button in tables
   • Or "Show Normalized" buttons
   • Only available models are shown

4. FILE COMPARISON
   • Normalize both files
   • Click "Compare Files"

5. VISUALIZATION
   • "AMIS Methods Comparison": select from available methods only
   • "All Comparison Graphs": 4 comparison graphs
   • Disabled checkboxes = model not available for this data volume

📁 SAVING SYSTEM:
All results are saved next to source files:
• converted_tables/ - Excel tables (only available models)
• plots/ - graphs in PNG and PDF

📋 DATA FORMAT:
• Column 1: Labels/Names (optional)
• Column 2: Numerical values to normalize
• Minimum 10 data points required
"""
        # Create help window with scroll
        help_window = tk.Toplevel(self)
        help_window.title("Help - How to Use the Program")
        help_window.geometry("700x550")

        text_widget = tk.Text(help_window, wrap=tk.WORD, font=('Arial', 10))
        scrollbar = ttk.Scrollbar(help_window, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)

        center_window(help_window)