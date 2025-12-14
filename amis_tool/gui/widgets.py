"""
AMIS Widgets (TableViewer and others)
Fixed version with proper scrolling and column handling
"""

import tkinter as tk
from tkinter import ttk
import pandas as pd
import numpy as np

class TableViewer(ttk.Frame):
    """Widget for displaying data tables with centered values and proper scrolling"""
    def __init__(self, master, title="", **kwargs):
        super().__init__(master, **kwargs)
        self.title_text = title
        self.data = None
        self.create_widgets()

    def create_widgets(self):
        """Create all widgets with proper scrollbar configuration"""
        # Table title
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        ttk.Label(title_frame, text=self.title_text, font=('Arial', 11, 'bold')).pack(side=tk.LEFT)

        # Table mode switch buttons
        self.mode_frame = ttk.Frame(title_frame)
        self.mode_frame.pack(side=tk.RIGHT)

        self.mode_label = ttk.Label(self.mode_frame, text="Mode:", font=('Arial', 9))
        self.mode_label.pack(side=tk.LEFT, padx=(0, 5))

        self.mode_btn = ttk.Button(self.mode_frame, text="Original", width=12,
                                  command=self.toggle_mode)
        self.mode_btn.pack(side=tk.LEFT)

        # By default show original data
        self.showing_normalized = False
        self.original_data = None
        self.normalized_data = None

        # Data information
        self.info_label = ttk.Label(title_frame, text="No data", font=('Arial', 9))
        self.info_label.pack(side=tk.RIGHT, padx=(0, 10))

        # Main table container
        table_container = ttk.Frame(self)
        table_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure grid weights
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        # Create Treeview with scrollbars
        self.tree = ttk.Treeview(table_container, show='headings')

        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scrollbar.set)

        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(table_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscrollcommand=h_scrollbar.set)

        # Grid layout for proper scrolling
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')

    def toggle_mode(self):
        """Switch between original and normalized data"""
        if self.showing_normalized:
            # Switch to original data
            self.showing_normalized = False
            self.mode_btn.config(text="Original")
            if self.original_data is not None:
                self.update_data(self.original_data, "original")
        else:
            # Switch to normalized data
            self.showing_normalized = True
            self.mode_btn.config(text="Normalized")
            if self.normalized_data is not None:
                self.update_data(self.normalized_data, "normalized")

    def set_normalized_data(self, df_normalized):
        """
        Set normalized data DataFrame directly

        Parameters:
        -----------
        df_normalized : pandas.DataFrame
            DataFrame with normalized data (includes first column with names/IDs)
        """
        self.normalized_data = df_normalized
        self.update_info_text()

    def set_original_data(self, df, data_type=""):
        """Set original data"""
        self.original_data = df
        self.data_type = data_type
        self.update_data(df, data_type)

    def update_info_text(self):
        """Update information label with clear English description"""
        if self.showing_normalized and self.normalized_data is not None:
            total_rows = len(self.normalized_data)
            total_cols = len(self.normalized_data.columns)
            display_rows = min(100, total_rows)

            if total_rows > 100:
                self.info_label.config(
                    text=f"Normalized: {total_rows} rows, {total_cols} cols (displaying first {display_rows})"
                )
            else:
                self.info_label.config(
                    text=f"Normalized: {total_rows} rows, {total_cols} cols (all data displayed)"
                )

        elif self.original_data is not None:
            total_rows = len(self.original_data)
            total_cols = len(self.original_data.columns)
            display_rows = min(100, total_rows)

            if total_rows > 100:
                self.info_label.config(
                    text=f"Original: {total_rows} rows, {total_cols} cols (displaying first {display_rows})"
                )
            else:
                self.info_label.config(
                    text=f"Original: {total_rows} rows, {total_cols} cols (all data displayed)"
                )
        else:
            self.info_label.config(text="No data loaded")

    def update_data(self, df, data_type=""):
        """
        Update data in table with centered values and proper formatting

        Parameters:
        -----------
        df : pandas.DataFrame
            Data to display
        data_type : str
            Type of data (for information only)
        """
        self.data = df

        # Clear old data but preserve treeview structure
        for item in self.tree.get_children():
            self.tree.delete(item)

        if df is None or df.empty:
            self.info_label.config(text="No data")
            self.mode_btn.config(state=tk.DISABLED)
            self.tree['columns'] = []
            return

        # Activate switch button if normalized data exists
        self.mode_btn.config(state=tk.NORMAL if self.normalized_data is not None else tk.DISABLED)

        # Set columns
        columns = list(df.columns)
        self.tree['columns'] = columns

        # Configure headers and center values
        for col in columns:
            self.tree.heading(col, text=col, anchor=tk.CENTER)

            # Auto-adjust column width based on content
            try:
                # Get max length of string representation
                max_len = 0
                for val in df[col].head(100):  # Check first 100 rows
                    if pd.isna(val):
                        str_val = ""
                    else:
                        str_val = str(val)
                    max_len = max(max_len, len(str_val))

                # Include column name length
                max_len = max(max_len, len(col))

                # Calculate width (characters * pixel width)
                width = min(max_len * 8, 300)  # Limit maximum width
                width = max(width, 50)  # Minimum width

                self.tree.column(col, width=width, minwidth=50, anchor=tk.CENTER)
            except:
                # Fallback if there's an error
                self.tree.column(col, width=100, minwidth=50, anchor=tk.CENTER)

        # Display first 100 rows (or less if table has fewer rows)
        display_rows = min(100, len(df))
        display_df = df.head(display_rows)

        for i, row in display_df.iterrows():
            # Format numbers for better display
            values = []
            for col_idx, col in enumerate(columns):
                val = row[col]

                if pd.isna(val):
                    values.append("")
                elif isinstance(val, (int, np.integer)):
                    # Display integers without decimal points
                    values.append(f"{int(val)}")
                elif isinstance(val, (float, np.floating)):
                    # Check if value is actually an integer (e.g., 1.0, 2.0)
                    if abs(val - round(val)) < 0.000001:  # Small epsilon for floating point comparison
                        # Display as integer
                        values.append(f"{int(round(val))}")
                    elif self.showing_normalized and col_idx >= 1:  # Skip first column for normalized data
                        # Normalized data: 2 decimal places
                        values.append(f"{float(val):.2f}")
                    else:
                        # Original data: remove unnecessary trailing zeros
                        formatted = f"{float(val):.6f}".rstrip('0').rstrip('.')
                        if formatted == '':
                            formatted = '0'
                        values.append(formatted)
                else:
                    values.append(str(val))

            self.tree.insert('', 'end', values=values)

        # Update information
        self.update_info_text()

        # Refresh the display to ensure scrollbars work
        self.tree.update_idletasks()

    def clear(self):
        """Clear all data from the table"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.tree['columns'] = []
        self.original_data = None
        self.normalized_data = None
        self.showing_normalized = False
        self.mode_btn.config(text="Original", state=tk.DISABLED)
        self.info_label.config(text="No data")