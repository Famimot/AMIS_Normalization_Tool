"""
Core AMIS Normalization Algorithms

=== CHANGES (v6.3) ===
+ REMOVED: check_intervals() — непустота интервалов больше НЕ отклоняет модель.
  Причина: AMIS метрическая, линейный отрезок между вычисленными узлами
  корректен даже при отсутствии данных внутри интервала.
+ KEPT: has_unique_nodes() — узлы должны быть различимы (технический запрет).
  Если узлы схлопнулись (например x3 = x5), модель НЕ строится.
+ OPTIONAL: diagnose_intervals=True — печатает пустые интервалы как ИНФОРМАЦИЮ,
  но НЕ отклоняет модель.
+ SYNCHRONIZED: available_models содержит только реально построенные модели.

=== COMPATIBILITY ===
API amis_conversion() не изменился. raw_to_amis() не изменился.
"""

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def remove_duplicates_and_sort(x, y):
    """Remove duplicate x-values while preserving the last corresponding y-value"""
    x = np.array(x)
    y = np.array(y)

    sorted_idx = np.argsort(x)
    x_sorted = x[sorted_idx]
    y_sorted = y[sorted_idx]

    unique_x, _ = np.unique(x_sorted, return_index=True)
    last_indices = [np.where(x_sorted == val)[0][-1] for val in unique_x]

    return x_sorted[last_indices], y_sorted[last_indices]


def safe_nanmean(arr):
    """Safe mean calculation with NaN handling"""
    if len(arr) == 0:
        return None
    valid = arr[~np.isnan(arr)]
    return np.mean(valid) if len(valid) > 0 else None


def has_unique_nodes(nodes):
    """
    Check that all computed node x-coordinates are distinct.
    If nodes collapse (duplicates), the model cannot be built correctly.
    This is the ONLY technical rejection criterion.
    """
    arr = np.asarray(nodes, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 2:
        return False
    return len(np.unique(arr)) == len(arr)


def count_unique_in_interval(data, lo, hi):
    """Count unique real data values in [lo, hi] (diagnostic only)."""
    mask = (data >= lo) & (data <= hi)
    if not np.any(mask):
        return 0
    return len(np.unique(data[mask]))


def get_available_models(n):
    """
    Determine model reliability based on data volume (n).
    NOTE: this is only "what could be available by n".
    Actual availability is synchronized with converted in amis_conversion().
    """
    if n >= 40:
        return {
            "17_points": "17 points (recommended)",
            "9_points": "9 points (recommended)",
            "5_points": "5 points (recommended)",
            "3_points": "3 points (recommended)",
            "linear": "Linear (recommended)"
        }
    elif n >= 20:
        return {
            "9_points": "9 points (recommended)",
            "5_points": "5 points (recommended)",
            "3_points": "3 points (recommended)",
            "linear": "Linear (recommended)",
            "17_points": "17 points (need 40+ points)"
        }
    elif n >= 10:
        return {
            "5_points": "5 points (recommended)",
            "3_points": "3 points (recommended)",
            "linear": "Linear (recommended)",
            "9_points": "9 points (need 20+ points)",
            "17_points": "17 points (need 40+ points)"
        }
    elif n >= 6:
        return {
            "3_points": "3 points (recommended)",
            "linear": "Linear (recommended)",
            "5_points": "5 points (need 10+ points)",
            "9_points": "9 points (need 20+ points)",
            "17_points": "17 points (need 40+ points)"
        }
    else:
        return {
            "linear": "Linear (recommended)",
            "3_points": "3 points (need 6+ points)",
            "5_points": "5 points (need 10+ points)",
            "9_points": "9 points (need 20+ points)",
            "17_points": "17 points (need 40+ points)"
        }


def get_unavailable_models(n, converted):
    """
    Optional helper for GUI: models that COULD be available by n
    but were NOT built (e.g. duplicate nodes).
    """
    could_be = get_available_models(n)
    return {m: v for m, v in could_be.items() if m not in converted}


# =========================================================
# DIAGNOSTIC (information only, never rejects a model)
# =========================================================

def _log_empty_intervals(model_name, pts, data, logger=None):
    """Print empty intervals as INFORMATION. Does not affect model building."""
    empty_info = []
    for i in range(len(pts) - 1):
        lo, hi = pts[i], pts[i + 1]
        if count_unique_in_interval(data, lo, hi) == 0:
            empty_info.append((i, lo, hi))
    if empty_info:
        msg = (f"[diagnostic] {model_name}: empty intervals "
               f"(no real data inside): " +
               ", ".join(f"#{i}[{lo:.3e};{hi:.3e}]" for i, lo, hi in empty_info))
        if logger is not None:
            logger.info(msg)
        else:
            print(msg)
    return empty_info


# =========================================================
# MAIN FORWARD TRANSFORM FUNCTION
# =========================================================

def amis_conversion(data, fixed_min=None, fixed_max=None, method='mean',
                    diagnose_intervals=False, logger=None):
    """
    AMIS conversion with user-defined bounds and method selection.

    Model building rules (v6.3):
    - Linear: always built (2 distinct nodes required — guaranteed by bounds check).
    - 3_points / 5_points / 9_points / 17_points:
        built if (n >= threshold) AND (unique_n >= min_unique)
        AND has_unique_nodes(points_N).
    - Empty intervals do NOT reject a model (only logged if diagnose_intervals=True).

    Parameters
    ----------
    data : array-like
    fixed_min, fixed_max : float or None
    method : str (only 'mean' supported)
    diagnose_intervals : bool
        If True, log empty intervals (information only, no rejection).
    logger : logging.Logger or None
        If provided, diagnostic goes to logger.info; else to print.

    Returns
    -------
    converted : dict {model_name: np.ndarray}
    points_coords : dict {x_N / y_N / x_line / y_line: np.ndarray}
    available_models : dict {model_name: description}  — synchronized with converted
    """
    data = np.array(data, dtype=float)
    data = data[~np.isnan(data)]
    n = len(data)
    unique_n = len(np.unique(data))

    if n < 3:
        raise ValueError(f"Need minimum 3 values, got {n}")

    central_func = safe_nanmean  # only 'mean' method supported

    data_min = fixed_min if fixed_min is not None else float(np.min(data))
    data_max = fixed_max if fixed_max is not None else float(np.max(data))

    if data_min >= data_max:
        raise ValueError(f"Minimum ({data_min}) must be less than maximum ({data_max})")

    # ========== x5 computed ONCE for ALL models ==========
    x5 = central_func(data) or (data_min + data_max) / 2

    # 3-point model control points
    x3 = central_func(data[(data >= data_min) & (data <= x5)]) or (data_min + x5) / 2
    x7 = central_func(data[(data >= x5) & (data <= data_max)]) or (x5 + data_max) / 2

    # 5-point model additional points
    x2 = central_func(data[(data >= data_min) & (data <= x3)]) or (data_min + x3) / 2
    x4 = central_func(data[(data >= x3) & (data <= x5)]) or (x3 + x5) / 2
    x6 = central_func(data[(data >= x5) & (data <= x7)]) or (x5 + x7) / 2
    x8 = central_func(data[(data >= x7) & (data <= data_max)]) or (x7 + data_max) / 2

    # 9-point model additional points
    x25 = central_func(data[(data >= data_min) & (data <= x2)]) or (data_min + x2) / 2
    x35 = central_func(data[(data >= x2) & (data <= x3)]) or (x2 + x3) / 2
    x45 = central_func(data[(data >= x3) & (data <= x4)]) or (x3 + x4) / 2
    x55 = central_func(data[(data >= x4) & (data <= x5)]) or (x4 + x5) / 2
    x65 = central_func(data[(data >= x5) & (data <= x6)]) or (x5 + x6) / 2
    x75 = central_func(data[(data >= x6) & (data <= x7)]) or (x6 + x7) / 2
    x85 = central_func(data[(data >= x7) & (data <= x8)]) or (x7 + x8) / 2
    x95 = central_func(data[(data >= x8) & (data <= data_max)]) or (x8 + data_max) / 2

    if np.isclose(x95, data_max, rtol=1e-10):
        x95 = (x8 + data_max) / 2

    # Define interpolation points per model
    points_17 = np.array([data_min, x25, x2, x35, x3, x45, x4, x55, x5,
                          x65, x6, x75, x7, x85, x8, x95, data_max])
    y_17 = np.linspace(0, 100, 17)

    points_9 = np.array([data_min, x2, x3, x4, x5, x6, x7, x8, data_max])
    y_9 = np.linspace(0, 100, 9)

    points_5 = np.array([data_min, x3, x5, x7, data_max])
    y_5 = np.linspace(0, 100, 5)

    points_3 = np.array([data_min, x5, data_max])
    y_3 = np.linspace(0, 100, 3)

    points_line = np.array([data_min, data_max])
    y_line = np.array([0, 100])

    def safe_interp(x, y):
        """
        Last-line-of-defense interpolation.
        For duplicate x we keep LAST y.
        After has_unique_nodes validation, duplicates should not reach here.
        """
        mask = ~np.isnan(x) & ~np.isnan(y)
        x_clean = x[mask]
        y_clean = y[mask]

        if len(x_clean) < 2:
            return interp1d([data_min, data_max], [0, 100], kind='linear',
                            fill_value='extrapolate', bounds_error=False)

        unique_dict = {}
        for xi, yi in zip(x_clean, y_clean):
            unique_dict[xi] = yi   # keep LAST

        x_clean = np.array(list(unique_dict.keys()))
        y_clean = np.array(list(unique_dict.values()))

        order = np.argsort(x_clean)
        x_clean = x_clean[order]
        y_clean = y_clean[order]

        return interp1d(x_clean, y_clean, kind='linear',
                        fill_value='extrapolate', bounds_error=False)

    converted = {}
    points_coords = {}

    # ----- Linear model (always) -----
    interp_line = safe_interp(points_line, y_line)
    converted["linear"] = interp_line(data)
    points_coords["x_line"] = interp_line.x
    points_coords["y_line"] = interp_line.y

    # ----- 3-point model -----
    if n >= 6 and unique_n >= 2 and has_unique_nodes(points_3):
        if diagnose_intervals:
            _log_empty_intervals("3_points", points_3, data, logger)
        interp_3 = safe_interp(points_3, y_3)
        converted["3_points"] = interp_3(data)
        points_coords["x_3"] = interp_3.x
        points_coords["y_3"] = interp_3.y

    # ----- 5-point model -----
    if n >= 10 and unique_n >= 3 and has_unique_nodes(points_5):
        if diagnose_intervals:
            _log_empty_intervals("5_points", points_5, data, logger)
        interp_5 = safe_interp(points_5, y_5)
        converted["5_points"] = interp_5(data)
        points_coords["x_5"] = interp_5.x
        points_coords["y_5"] = interp_5.y

    # ----- 9-point model -----
    if n >= 20 and unique_n >= 5 and has_unique_nodes(points_9):
        if diagnose_intervals:
            _log_empty_intervals("9_points", points_9, data, logger)
        interp_9 = safe_interp(points_9, y_9)
        converted["9_points"] = interp_9(data)
        points_coords["x_9"] = interp_9.x
        points_coords["y_9"] = interp_9.y

    # ----- 17-point model -----
    if n >= 40 and unique_n >= 9 and has_unique_nodes(points_17):
        if diagnose_intervals:
            _log_empty_intervals("17_points", points_17, data, logger)
        interp_17 = safe_interp(points_17, y_17)
        converted["17_points"] = interp_17(data)
        points_coords["x_17"] = interp_17.x
        points_coords["y_17"] = interp_17.y

    # ----- Synchronization: only actually built models -----
    available_models = {
        m: v for m, v in get_available_models(n).items()
        if m in converted
    }

    return converted, points_coords, available_models


# =========================================================
# INVERSE TRANSFORM "raw value → AMIS"
# =========================================================

def raw_to_amis(raw_values, converted, points_coords, available_models,
                fixed_min=None, fixed_max=None):
    """
    Inverse transform: raw value → AMIS (0-100).
    Unchanged from v6.2.
    """
    raw_values = np.asarray(raw_values, dtype=float)

    if "17_points" in converted and "17_points" in available_models:
        x_pts = np.asarray(points_coords["x_17"], dtype=float)
        y_pts = np.asarray(points_coords["y_17"], dtype=float)
    elif "9_points" in converted and "9_points" in available_models:
        x_pts = np.asarray(points_coords["x_9"], dtype=float)
        y_pts = np.asarray(points_coords["y_9"], dtype=float)
    elif "5_points" in converted and "5_points" in available_models:
        x_pts = np.asarray(points_coords["x_5"], dtype=float)
        y_pts = np.asarray(points_coords["y_5"], dtype=float)
    elif "3_points" in converted and "3_points" in available_models:
        x_pts = np.asarray(points_coords["x_3"], dtype=float)
        y_pts = np.asarray(points_coords["y_3"], dtype=float)
    else:
        x_pts = np.asarray(points_coords["x_line"], dtype=float)
        y_pts = np.asarray(points_coords["y_line"], dtype=float)

    unique_dict = {}
    for xi, yi in zip(x_pts, y_pts):
        if not np.isnan(xi) and not np.isnan(yi):
            unique_dict[xi] = yi

    x_u = np.array(list(unique_dict.keys()), dtype=float)
    y_u = np.array(list(unique_dict.values()), dtype=float)

    order = np.argsort(x_u)
    x_u = x_u[order]
    y_u = y_u[order]

    if len(x_u) < 2:
        dmin = fixed_min if fixed_min is not None else float(np.min(raw_values))
        dmax = fixed_max if fixed_max is not None else float(np.max(raw_values))
        if dmin == dmax:
            return np.full_like(raw_values, 50.0, dtype=float)
        return (raw_values - dmin) / (dmax - dmin) * 100.0

    f = interp1d(x_u, y_u, kind='linear',
                 fill_value='extrapolate', bounds_error=False)

    return f(raw_values)


# =========================================================
# AGGREGATED DATA CONVERSION
# =========================================================

def safe_aggregated_to_raw(df, data_type):
    """Convert aggregated data (value:count) to raw format"""
    try:
        df_work = df.copy(deep=True)

        if data_type == "raw":
            if len(df_work.columns) == 1:
                value_col = df_work.columns[0]
                values_series = pd.to_numeric(df_work.iloc[:, 0], errors='coerce')
                values = values_series.dropna().values
            elif len(df_work.columns) >= 2:
                value_col = df_work.columns[1]
                values_series = pd.to_numeric(df_work.iloc[:, 1], errors='coerce')
                values = values_series.dropna().values
            else:
                raise ValueError("No columns found")

        else:  # aggregated
            cols = list(df_work.columns)
            value_col = cols[0]
            count_col = cols[1] if len(cols) > 1 else None

            if count_col is None:
                raise ValueError(f"Aggregated data needs 2 columns. Got: {cols}")

            work_df = df_work[[value_col, count_col]].copy()
            work_df = work_df.dropna(how='all')

            if work_df.empty:
                raise ValueError("All rows are empty after removing NaN")

            work_df[value_col] = pd.to_numeric(work_df[value_col], errors='coerce')
            work_df[count_col] = pd.to_numeric(work_df[count_col], errors='coerce')

            work_df = work_df.dropna(subset=[count_col])
            work_df[count_col] = work_df[count_col].fillna(0).astype(int)
            work_df = work_df[work_df[count_col] > 0].copy()

            if work_df.empty:
                raise ValueError("No data with count > 0")

            raw_values = []
            total_limit = 500000

            for idx, row in work_df.iterrows():
                count = min(int(row[count_col]), 10000)
                raw_values.extend([float(row[value_col])] * count)

                if len(raw_values) >= total_limit:
                    break

            values = np.array(raw_values[:total_limit])

        values = values[~np.isnan(values)]

        if len(values) < 3:
            raise ValueError(f"Insufficient data: {len(values)} valid values (minimum 3 required)")

        return values, value_col

    except Exception as e:
        raise ValueError(f"Data conversion error: {str(e)}")


# =========================================================
# BACKWARD COMPATIBILITY
# =========================================================

amis_safe_conversion = amis_conversion