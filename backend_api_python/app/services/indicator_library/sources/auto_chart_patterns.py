# ============================================================
# [Default] Auto Chart Patterns
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal chart-pattern detector built from confirmed ZigZag pivots. A pivot is
# only added after the configured percentage reversal, and a detected pattern
# starts drawing on its confirmation bar. No pattern line is back-filled into
# bars that were already evaluated.
# ============================================================

my_indicator_name = "[Default] Auto Chart Patterns"
my_indicator_description = "Causal channel, wedge, and triangle detection from confirmed price pivots."

# @param source string close Pattern source: close or hl2
# @param threshold float 0.01 Percentage reversal required to confirm a pivot range=0.001:0.2:0.001
# @param min_pivots int 4 Minimum pivots used for a pattern range=4:6:1
# @param max_pivots int 6 Maximum pivots used for a pattern range=4:6:1
# @param error_ratio float 0.02 Maximum normalized fit error range=0.001:0.2:0.001
# @param flat_ratio float 0.2 Relative slope threshold for a flat boundary range=0.01:1.0:0.01
# @param conv_eps float 0.05 Slope convergence tolerance range=0.001:0.5:0.001
# @param allow_channels bool true Detect ascending, descending, and horizontal channels
# @param allow_wedges bool true Detect rising, falling, and broadening wedges
# @param allow_triangles bool true Detect ascending, descending, symmetrical, and broadening triangles
# @param max_patterns int 6 Maximum pivot count scanned for each pattern range=4:6:1
# @param avoid_overlap bool true Replace an active pattern only after a newly confirmed pivot

source_name = str(params.get("source", "close")).strip().lower()
threshold = max(0.001, min(0.2, float(params.get("threshold", 0.01))))
min_pivots = max(4, min(6, int(params.get("min_pivots", 4))))
max_pivots = max(min_pivots, min(6, int(params.get("max_pivots", 6))))
error_ratio = max(0.001, min(0.2, float(params.get("error_ratio", 0.02))))
flat_ratio = max(0.01, min(1.0, float(params.get("flat_ratio", 0.2))))
conv_eps = max(0.001, min(0.5, float(params.get("conv_eps", 0.05))))
max_patterns = max(min_pivots, min(max_pivots, int(params.get("max_patterns", max_pivots))))


def _as_bool(value, default):
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes", "on"):
            return True
        if lowered in ("false", "0", "no", "off"):
            return False
    return bool(value)


allow_channels = _as_bool(params.get("allow_channels", True), True)
allow_wedges = _as_bool(params.get("allow_wedges", True), True)
allow_triangles = _as_bool(params.get("allow_triangles", True), True)
avoid_overlap = _as_bool(params.get("avoid_overlap", True), True)

# The chart contract exposes one set of top/bottom/mid lines. When overlap is
# avoided, a fresh pattern must wait for the previous pattern's pivot window to
# age out; otherwise a newly confirmed pattern may replace it immediately.

df = df.copy()
open_price = df["open"].astype(float).to_numpy()
high = df["high"].astype(float).to_numpy()
low = df["low"].astype(float).to_numpy()
close = df["close"].astype(float).to_numpy()
if source_name in ("hl2", "high/low", "high_low", "high-low"):
    source = (high + low) / 2.0
else:
    source = close.copy()

n = len(source)
top_line = np.full(n, np.nan, dtype=float)
bottom_line = np.full(n, np.nan, dtype=float)
mid_line = np.full(n, np.nan, dtype=float)
buy_signal = np.zeros(n, dtype=bool)
sell_signal = np.zeros(n, dtype=bool)
pattern_events = [None] * n


def _fit_line(points):
    if len(points) < 2:
        return None
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    if not all(np.isfinite(value) for value in xs) or not all(np.isfinite(value) for value in ys):
        return None
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    denominator = sum((value - x_mean) ** 2 for value in xs)
    if denominator <= 1e-12:
        return None
    numerator = sum((xs[index] - x_mean) * (ys[index] - y_mean) for index in range(len(xs)))
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    residual = max(abs(ys[index] - (slope * xs[index] + intercept)) for index in range(len(xs)))
    return float(slope), float(intercept), float(residual)


def _pattern_candidate(pivots, current_index):
    if len(pivots) < min_pivots:
        return None
    first_k = min(max_patterns, len(pivots))
    for count in range(first_k, min_pivots - 1, -1):
        window = pivots[-count:]
        high_points = [(item[0], item[1]) for item in window if item[2] == "high"]
        low_points = [(item[0], item[1]) for item in window if item[2] == "low"]
        if len(high_points) < 2 or len(low_points) < 2:
            continue
        upper_fit = _fit_line(high_points)
        lower_fit = _fit_line(low_points)
        if upper_fit is None or lower_fit is None:
            continue

        upper_slope, upper_intercept, upper_error = upper_fit
        lower_slope, lower_intercept, lower_error = lower_fit
        scale = max(1e-12, max(abs(float(item[1])) for item in window))
        span = max(1.0, float(window[-1][0] - window[0][0]))
        if max(upper_error, lower_error) / scale > error_ratio:
            continue

        upper_relative = upper_slope * span / scale
        lower_relative = lower_slope * span / scale
        slope_gap = upper_relative - lower_relative
        max_slope = max(abs(upper_relative), abs(lower_relative), 1e-12)
        flat_limit = max(conv_eps * 0.25, max_slope * flat_ratio)
        upper_flat = abs(upper_relative) <= flat_limit
        lower_flat = abs(lower_relative) <= flat_limit
        upper_now = upper_slope * current_index + upper_intercept
        lower_now = lower_slope * current_index + lower_intercept
        upper_start = upper_slope * window[0][0] + upper_intercept
        lower_start = lower_slope * window[0][0] + lower_intercept
        upper_end = upper_slope * window[-1][0] + upper_intercept
        lower_end = lower_slope * window[-1][0] + lower_intercept
        if min(upper_start - lower_start, upper_end - lower_end, upper_now - lower_now) <= 0:
            continue

        pattern_type = None
        family = None
        if abs(slope_gap) <= conv_eps:
            family = "channel"
            if not allow_channels:
                continue
            average_slope = (upper_relative + lower_relative) / 2.0
            if abs(average_slope) <= flat_limit:
                pattern_type = "Horizontal Channel"
            elif average_slope > 0:
                pattern_type = "Ascending Channel"
            else:
                pattern_type = "Descending Channel"
        elif slope_gap < -conv_eps:
            # A negative upper-minus-lower slope means the boundaries converge.
            if upper_flat and lower_relative > flat_limit:
                family = "triangle"
                pattern_type = "Ascending Triangle"
            elif lower_flat and upper_relative < -flat_limit:
                family = "triangle"
                pattern_type = "Descending Triangle"
            elif upper_relative < -flat_limit and lower_relative > flat_limit:
                family = "triangle"
                pattern_type = "Symmetrical Triangle"
            elif upper_relative > flat_limit and lower_relative > flat_limit:
                family = "wedge"
                pattern_type = "Rising Wedge"
            elif upper_relative < -flat_limit and lower_relative < -flat_limit:
                family = "wedge"
                pattern_type = "Falling Wedge"
            else:
                family = "triangle"
                pattern_type = "Symmetrical Triangle"
        else:
            family = "wedge"
            if upper_relative > flat_limit and lower_relative < -flat_limit:
                pattern_type = "Broadening Triangle"
                family = "triangle"
            elif upper_relative > flat_limit and lower_relative > flat_limit:
                pattern_type = "Expanding Rising Wedge"
            elif upper_relative < -flat_limit and lower_relative < -flat_limit:
                pattern_type = "Expanding Falling Wedge"
            else:
                pattern_type = "Broadening Triangle"
                family = "triangle"

        if family == "channel" and not allow_channels:
            continue
        if family == "wedge" and not allow_wedges:
            continue
        if family == "triangle" and not allow_triangles:
            continue

        return {
            "type": pattern_type,
            "upper_slope": upper_slope,
            "upper_intercept": upper_intercept,
            "lower_slope": lower_slope,
            "lower_intercept": lower_intercept,
            "start": current_index,
        }
    return None


# Causal percentage-reversal ZigZag. A pivot is appended on the bar that
# confirms the reversal, never on the earlier extremum bar itself.
pivots = []
direction = 0
extreme_index = -1
extreme_value = np.nan
active_pattern = None
previous_top = np.nan
previous_bottom = np.nan

for i in range(n):
    value = source[i]
    if not np.isfinite(value):
        continue

    confirmed_pivot = False
    if extreme_index < 0:
        extreme_index = i
        extreme_value = float(value)
        continue

    if direction == 0:
        if value >= extreme_value * (1.0 + threshold):
            pivots.append((extreme_index, extreme_value, "low"))
            direction = 1
            extreme_index = i
            extreme_value = float(value)
            confirmed_pivot = True
        elif value <= extreme_value * (1.0 - threshold):
            pivots.append((extreme_index, extreme_value, "high"))
            direction = -1
            extreme_index = i
            extreme_value = float(value)
            confirmed_pivot = True
    elif direction == 1:
        if value >= extreme_value:
            extreme_index = i
            extreme_value = float(value)
        elif value <= extreme_value * (1.0 - threshold):
            pivots.append((extreme_index, extreme_value, "high"))
            direction = -1
            extreme_index = i
            extreme_value = float(value)
            confirmed_pivot = True
    else:
        if value <= extreme_value:
            extreme_index = i
            extreme_value = float(value)
        elif value >= extreme_value * (1.0 + threshold):
            pivots.append((extreme_index, extreme_value, "low"))
            direction = 1
            extreme_index = i
            extreme_value = float(value)
            confirmed_pivot = True

    if confirmed_pivot:
        candidate = _pattern_candidate(pivots, i)
        can_replace = (
            candidate is not None
            and (
                not avoid_overlap
                or active_pattern is None
                or i - active_pattern["start"] >= max_patterns
            )
        )
        if can_replace:
            active_pattern = candidate
            pattern_events[i] = candidate["type"]

    if active_pattern is None or i < active_pattern["start"]:
        continue

    top_value = active_pattern["upper_slope"] * i + active_pattern["upper_intercept"]
    bottom_value = active_pattern["lower_slope"] * i + active_pattern["lower_intercept"]
    if not np.isfinite(top_value) or not np.isfinite(bottom_value) or top_value <= bottom_value:
        active_pattern = None
        continue

    top_line[i] = top_value
    bottom_line[i] = bottom_value
    mid_line[i] = (top_value + bottom_value) / 2.0

    if i > active_pattern["start"] and np.isfinite(close[i - 1]):
        if np.isfinite(previous_top) and close[i - 1] <= previous_top and close[i] > top_value:
            buy_signal[i] = True
        if np.isfinite(previous_bottom) and close[i - 1] >= previous_bottom and close[i] < bottom_value:
            sell_signal[i] = True
    previous_top = top_value
    previous_bottom = bottom_value


def _plot_values(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


buy_marks = [float(low[i]) * 0.995 if buy_signal[i] and np.isfinite(low[i]) else None for i in range(n)]
sell_marks = [float(high[i]) * 1.005 if sell_signal[i] and np.isfinite(high[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Pattern Top", "data": _plot_values(top_line), "color": "#EF5350", "overlay": True},
        {"name": "Pattern Mid", "data": _plot_values(mid_line), "color": "#FFB300", "overlay": True},
        {"name": "Pattern Bottom", "data": _plot_values(bottom_line), "color": "#26A69A", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "ACP+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "ACP-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
    "metadata": {
        "pattern_type": pattern_events,
        "causal": True,
        "source": source_name,
    },
}
