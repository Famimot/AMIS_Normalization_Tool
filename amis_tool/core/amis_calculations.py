"""
Core AMIS Normalization Algorithms
Simplified version - single data type support
WITH ADAPTIVE MODEL SELECTION
"""

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

def remove_duplicates_and_sort(x, y):
    """
    Remove duplicate x-values while preserving the last corresponding y-value
    """
    x = np.array(x)
    y = np.array(y)

    sorted_idx = np.argsort(x)
    x_sorted = x[sorted_idx]
    y_sorted = y[sorted_idx]

    unique_x, last_indices = np.unique(x_sorted, return_index=True)
    last_indices = [np.where(x_sorted == val)[0][-1] for val in unique_x]

    return x_sorted[last_indices], y_sorted[last_indices]

def safe_nanmean(arr):
    """Safe mean calculation with NaN handling"""
    if len(arr) == 0:
        return None
    valid = arr[~np.isnan(arr)]
    return np.mean(valid) if len(valid) > 0 else None

def load_data_to_array(df):
    """
    Load data from DataFrame to numpy array
    Returns values, labels (from first column), and column name

    Returns:
    --------
    values : numpy.ndarray
        Array of numeric values from second column
    value_col : str
        Name of the value column
    labels : numpy.ndarray
        Labels from first column (e.g., country names, IDs)
    """
    try:
        df_work = df.copy(deep=True)

        if len(df_work.columns) < 2:
            raise ValueError(
                f"Data needs at least 2 columns.\n"
                f"Got {len(df_work.columns)} column(s): {list(df_work.columns)}\n"
                f"Expected format:\n"
                f"Column 1: Labels/Names (optional)\n"
                f"Column 2: Numerical values to normalize"
            )

        value_col = df_work.columns[1]
        labels = df_work.iloc[:, 0].values
        values_series = pd.to_numeric(df_work.iloc[:, 1], errors='coerce')
        values = values_series.dropna().values

        # Check for sufficient data (minimum 10 points)
        if len(values) < 10:
            raise ValueError(
                f"Insufficient data: {len(values)} valid values (minimum 10 required).\n"
                f"Check for non-numeric values in column '{value_col}'"
            )

        return values, value_col, labels

    except Exception as e:
        raise ValueError(f"Failed to load data: {str(e)}")

def get_available_models(n):
    """
    Determine available models based on data volume

    Parameters:
    -----------
    n : int
        Number of data points

    Returns:
    --------
    available_models : dict
        Dictionary with available models and their names
    """
    available_models = {}

    if n >= 100:
        available_models = {
            "17_points": "17 points",
            "9_points": "9 points",
            "5_points": "5 points",
            "3_points": "3 points",
            "linear": "Linear"
        }
    elif n >= 50:
        available_models = {
            "9_points": "9 points",
            "5_points": "5 points",
            "3_points": "3 points",
            "linear": "Linear"
        }
    elif n >= 20:
        available_models = {
            "5_points": "5 points",
            "3_points": "3 points",
            "linear": "Linear"
        }
    elif n >= 10:
        available_models = {
            "3_points": "3 points",
            "linear": "Linear"
        }
    else:
        # This should not happen as load_data_to_array already checks n >= 10
        available_models = {"linear": "Linear"}

    return available_models

def amis_safe_conversion(data, fixed_min=None, fixed_max=None):
    """
    Safe AMIS conversion with automatic bounds and ADAPTIVE model selection

    Parameters:
    -----------
    data : numpy.ndarray
        Array of numeric values
    fixed_min : float, optional
        Fixed minimum value for normalization (None for automatic)
    fixed_max : float, optional
        Fixed maximum value for normalization (None for automatic)

    Returns:
    --------
    converted : dict
        Dictionary with normalized values for AVAILABLE models only
    points_coords : dict
        Dictionary with interpolation points coordinates for AVAILABLE models
    available_models : dict
        Dictionary of available models and their display names
    """
    data = np.array(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)

    if n < 10:
        raise ValueError(f"Need 10+ values, got {n}")

    # Get available models based on data volume
    available_models = get_available_models(n)

    # Determine bounds (automatic if not specified)
    dmin = fixed_min if fixed_min is not None else float(np.min(data))
    dmax = fixed_max if fixed_max is not None else float(np.max(data))

    if dmin >= dmax:
        raise ValueError(f"dmin({dmin}) >= dmax({dmax})")

    # Calculate ALL control points (will be filtered based on availability)
    x5 = safe_nanmean(data) or (dmin + dmax) / 2

    # Hierarchical averaging for all possible points
    if n >= 10:  # Minimum for 3-point model
        x3 = safe_nanmean(data[(data >= dmin) & (data <= x5)]) or (dmin + x5) / 2
        x7 = safe_nanmean(data[(data >= x5) & (data <= dmax)]) or (x5 + dmax) / 2

    if n >= 20:  # Minimum for 5-point model
        x2 = safe_nanmean(data[(data >= dmin) & (data <= x3)]) or (dmin + x3) / 2
        x4 = safe_nanmean(data[(data >= x3) & (data <= x5)]) or (x3 + x5) / 2
        x6 = safe_nanmean(data[(data >= x5) & (data <= x7)]) or (x5 + x7) / 2
        x8 = safe_nanmean(data[(data >= x7) & (data <= dmax)]) or (x7 + dmax) / 2

    if n >= 50:  # Minimum for 9-point model
        x25 = safe_nanmean(data[(data >= dmin) & (data <= x2)]) or (dmin + x2) / 2
        x35 = safe_nanmean(data[(data >= x2) & (data <= x3)]) or (x2 + x3) / 2
        x45 = safe_nanmean(data[(data >= x3) & (data <= x4)]) or (x3 + x4) / 2
        x55 = safe_nanmean(data[(data >= x4) & (data <= x5)]) or (x4 + x5) / 2
        x65 = safe_nanmean(data[(data >= x5) & (data <= x6)]) or (x5 + x6) / 2
        x75 = safe_nanmean(data[(data >= x6) & (data <= x7)]) or (x6 + x7) / 2
        x85 = safe_nanmean(data[(data >= x7) & (data <= x8)]) or (x7 + x8) / 2
        x95 = safe_nanmean(data[(data >= x8) & (data <= dmax)]) or (x8 + dmax) / 2

        # Prevent duplicate maximum point
        if np.isclose(x95, dmax, rtol=1e-10):
            x95 = (x8 + dmax) / 2

    # Initialize result dictionaries
    converted = {}
    points_coords = {}

    def safe_interp(x, y):
        """Safe interpolation with duplicate handling"""
        mask = ~np.isnan(x) & ~np.isnan(y)
        x_clean = x[mask]
        y_clean = y[mask]

        if len(x_clean) < 2:
            return interp1d([dmin, dmax], [0, 100], kind='linear',
                          fill_value='extrapolate', bounds_error=False)

        x_clean, y_clean = remove_duplicates_and_sort(x_clean, y_clean)
        return interp1d(x_clean, y_clean, kind='linear',
                       fill_value='extrapolate', bounds_error=False)

    # Create models based on availability

    # LINEAR model (always available)
    points_line = np.array([dmin, dmax])
    y_line = np.array([0, 100])
    interp_line = safe_interp(points_line, y_line)
    converted["linear"] = interp_line(data)
    points_coords["x_line"] = interp_line.x
    points_coords["y_line"] = interp_line.y

    # 3-POINT model (available for n >= 10)
    if "3_points" in available_models:
        points_3 = np.array([dmin, x5, dmax])
        y_3 = np.linspace(0, 100, 3)
        interp_3 = safe_interp(points_3, y_3)
        converted["3_points"] = interp_3(data)
        points_coords["x_3"] = interp_3.x
        points_coords["y_3"] = interp_3.y

    # 5-POINT model (available for n >= 20)
    if "5_points" in available_models:
        points_5 = np.array([dmin, x3, x5, x7, dmax])
        y_5 = np.linspace(0, 100, 5)
        interp_5 = safe_interp(points_5, y_5)
        converted["5_points"] = interp_5(data)
        points_coords["x_5"] = interp_5.x
        points_coords["y_5"] = interp_5.y

    # 9-POINT model (available for n >= 50)
    if "9_points" in available_models:
        points_9 = np.array([dmin, x2, x3, x4, x5, x6, x7, x8, dmax])
        y_9 = np.linspace(0, 100, 9)
        interp_9 = safe_interp(points_9, y_9)
        converted["9_points"] = interp_9(data)
        points_coords["x_9"] = interp_9.x
        points_coords["y_9"] = interp_9.y

    # 17-POINT model (available for n >= 100)
    if "17_points" in available_models:
        points_17 = np.array([dmin, x25, x2, x35, x3, x45, x4, x55, x5, x65, x6, x75, x7, x85, x8, x95, dmax])
        y_17 = np.linspace(0, 100, 17)
        interp_17 = safe_interp(points_17, y_17)
        converted["17_points"] = interp_17(data)
        points_coords["x_17"] = interp_17.x
        points_coords["y_17"] = interp_17.y

    return converted, points_coords, available_models