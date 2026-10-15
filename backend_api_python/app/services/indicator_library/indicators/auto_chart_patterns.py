"""Chart-only source for the auto_chart_patterns indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Auto Chart Patterns\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal chart-pattern detector built from confirmed ZigZag pivots. A pivot is\n"
    "# only added after the configured percentage reversal, and a detected pattern\n"
    "# starts drawing on its confirmation bar. No pattern line is back-filled into\n"
    "# bars that were already evaluated.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Auto Chart Patterns"\n'
    'my_indicator_description = "Causal channel, wedge, and triangle detection from confirmed price pivots."\n'
    "\n"
    "# @param source string close Pattern source: close or hl2\n"
    "# @param threshold float 0.01 Percentage reversal required to confirm a pivot range=0.001:0.2:0.001\n"
    "# @param min_pivots int 4 Minimum pivots used for a pattern range=4:6:1\n"
    "# @param max_pivots int 6 Maximum pivots used for a pattern range=4:6:1\n"
    "# @param error_ratio float 0.02 Maximum normalized fit error range=0.001:0.2:0.001\n"
    "# @param flat_ratio float 0.2 Relative slope threshold for a flat boundary range=0.01:1.0:0.01\n"
    "# @param conv_eps float 0.05 Slope convergence tolerance range=0.001:0.5:0.001\n"
    "# @param allow_channels bool true Detect ascending, descending, and horizontal channels\n"
    "# @param allow_wedges bool true Detect rising, falling, and broadening wedges\n"
    "# @param allow_triangles bool true Detect ascending, descending, symmetrical, and broadening triangles\n"
    "# @param max_patterns int 6 Maximum pivot count scanned for each pattern range=4:6:1\n"
    "# @param avoid_overlap bool true Replace an active pattern only after a newly confirmed pivot\n"
    "\n"
    'source_name = str(params.get("source", "close")).strip().lower()\n'
    'threshold = max(0.001, min(0.2, float(params.get("threshold", 0.01))))\n'
    'min_pivots = max(4, min(6, int(params.get("min_pivots", 4))))\n'
    'max_pivots = max(min_pivots, min(6, int(params.get("max_pivots", 6))))\n'
    'error_ratio = max(0.001, min(0.2, float(params.get("error_ratio", 0.02))))\n'
    'flat_ratio = max(0.01, min(1.0, float(params.get("flat_ratio", 0.2))))\n'
    'conv_eps = max(0.001, min(0.5, float(params.get("conv_eps", 0.05))))\n'
    'max_patterns = max(min_pivots, min(max_pivots, int(params.get("max_patterns", max_pivots))))\n'
    "\n"
    "\n"
    "def _as_bool(value, default):\n"
    "    if value is None:\n"
    "        return default\n"
    "    if isinstance(value, str):\n"
    "        lowered = value.strip().lower()\n"
    '        if lowered in ("true", "1", "yes", "on"):\n'
    "            return True\n"
    '        if lowered in ("false", "0", "no", "off"):\n'
    "            return False\n"
    "    return bool(value)\n"
    "\n"
    "\n"
    'allow_channels = _as_bool(params.get("allow_channels", True), True)\n'
    'allow_wedges = _as_bool(params.get("allow_wedges", True), True)\n'
    'allow_triangles = _as_bool(params.get("allow_triangles", True), True)\n'
    'avoid_overlap = _as_bool(params.get("avoid_overlap", True), True)\n'
    "\n"
    "# The chart contract exposes one set of top/bottom/mid lines. When overlap is\n"
    "# avoided, a fresh pattern must wait for the previous pattern's pivot window to\n"
    "# age out; otherwise a newly confirmed pattern may replace it immediately.\n"
    "\n"
    "df = df.copy()\n"
    'open_price = df["open"].astype(float).to_numpy()\n'
    'high = df["high"].astype(float).to_numpy()\n'
    'low = df["low"].astype(float).to_numpy()\n'
    'close = df["close"].astype(float).to_numpy()\n'
    'if source_name in ("hl2", "high/low", "high_low", "high-low"):\n'
    "    source = (high + low) / 2.0\n"
    "else:\n"
    "    source = close.copy()\n"
    "\n"
    "n = len(source)\n"
    "top_line = np.full(n, np.nan, dtype=float)\n"
    "bottom_line = np.full(n, np.nan, dtype=float)\n"
    "mid_line = np.full(n, np.nan, dtype=float)\n"
    "buy_signal = np.zeros(n, dtype=bool)\n"
    "sell_signal = np.zeros(n, dtype=bool)\n"
    "pattern_events = [None] * n\n"
    "\n"
    "\n"
    "def _fit_line(points):\n"
    "    if len(points) < 2:\n"
    "        return None\n"
    "    xs = [float(point[0]) for point in points]\n"
    "    ys = [float(point[1]) for point in points]\n"
    "    if not all(np.isfinite(value) for value in xs) or not all(np.isfinite(value) for value in ys):\n"
    "        return None\n"
    "    x_mean = sum(xs) / len(xs)\n"
    "    y_mean = sum(ys) / len(ys)\n"
    "    denominator = sum((value - x_mean) ** 2 for value in xs)\n"
    "    if denominator <= 1e-12:\n"
    "        return None\n"
    "    numerator = sum((xs[index] - x_mean) * (ys[index] - y_mean) for index in range(len(xs)))\n"
    "    slope = numerator / denominator\n"
    "    intercept = y_mean - slope * x_mean\n"
    "    residual = max(abs(ys[index] - (slope * xs[index] + intercept)) for index in range(len(xs)))\n"
    "    return float(slope), float(intercept), float(residual)\n"
    "\n"
    "\n"
    "def _pattern_candidate(pivots, current_index):\n"
    "    if len(pivots) < min_pivots:\n"
    "        return None\n"
    "    first_k = min(max_patterns, len(pivots))\n"
    "    for count in range(first_k, min_pivots - 1, -1):\n"
    "        window = pivots[-count:]\n"
    '        high_points = [(item[0], item[1]) for item in window if item[2] == "high"]\n'
    '        low_points = [(item[0], item[1]) for item in window if item[2] == "low"]\n'
    "        if len(high_points) < 2 or len(low_points) < 2:\n"
    "            continue\n"
    "        upper_fit = _fit_line(high_points)\n"
    "        lower_fit = _fit_line(low_points)\n"
    "        if upper_fit is None or lower_fit is None:\n"
    "            continue\n"
    "\n"
    "        upper_slope, upper_intercept, upper_error = upper_fit\n"
    "        lower_slope, lower_intercept, lower_error = lower_fit\n"
    "        scale = max(1e-12, max(abs(float(item[1])) for item in window))\n"
    "        span = max(1.0, float(window[-1][0] - window[0][0]))\n"
    "        if max(upper_error, lower_error) / scale > error_ratio:\n"
    "            continue\n"
    "\n"
    "        upper_relative = upper_slope * span / scale\n"
    "        lower_relative = lower_slope * span / scale\n"
    "        slope_gap = upper_relative - lower_relative\n"
    "        max_slope = max(abs(upper_relative), abs(lower_relative), 1e-12)\n"
    "        flat_limit = max(conv_eps * 0.25, max_slope * flat_ratio)\n"
    "        upper_flat = abs(upper_relative) <= flat_limit\n"
    "        lower_flat = abs(lower_relative) <= flat_limit\n"
    "        upper_now = upper_slope * current_index + upper_intercept\n"
    "        lower_now = lower_slope * current_index + lower_intercept\n"
    "        upper_start = upper_slope * window[0][0] + upper_intercept\n"
    "        lower_start = lower_slope * window[0][0] + lower_intercept\n"
    "        upper_end = upper_slope * window[-1][0] + upper_intercept\n"
    "        lower_end = lower_slope * window[-1][0] + lower_intercept\n"
    "        if min(upper_start - lower_start, upper_end - lower_end, upper_now - lower_now) <= 0:\n"
    "            continue\n"
    "\n"
    "        pattern_type = None\n"
    "        family = None\n"
    "        if abs(slope_gap) <= conv_eps:\n"
    '            family = "channel"\n'
    "            if not allow_channels:\n"
    "                continue\n"
    "            average_slope = (upper_relative + lower_relative) / 2.0\n"
    "            if abs(average_slope) <= flat_limit:\n"
    '                pattern_type = "Horizontal Channel"\n'
    "            elif average_slope > 0:\n"
    '                pattern_type = "Ascending Channel"\n'
    "            else:\n"
    '                pattern_type = "Descending Channel"\n'
    "        elif slope_gap < -conv_eps:\n"
    "            # A negative upper-minus-lower slope means the boundaries converge.\n"
    "            if upper_flat and lower_relative > flat_limit:\n"
    '                family = "triangle"\n'
    '                pattern_type = "Ascending Triangle"\n'
    "            elif lower_flat and upper_relative < -flat_limit:\n"
    '                family = "triangle"\n'
    '                pattern_type = "Descending Triangle"\n'
    "            elif upper_relative < -flat_limit and lower_relative > flat_limit:\n"
    '                family = "triangle"\n'
    '                pattern_type = "Symmetrical Triangle"\n'
    "            elif upper_relative > flat_limit and lower_relative > flat_limit:\n"
    '                family = "wedge"\n'
    '                pattern_type = "Rising Wedge"\n'
    "            elif upper_relative < -flat_limit and lower_relative < -flat_limit:\n"
    '                family = "wedge"\n'
    '                pattern_type = "Falling Wedge"\n'
    "            else:\n"
    '                family = "triangle"\n'
    '                pattern_type = "Symmetrical Triangle"\n'
    "        else:\n"
    '            family = "wedge"\n'
    "            if upper_relative > flat_limit and lower_relative < -flat_limit:\n"
    '                pattern_type = "Broadening Triangle"\n'
    '                family = "triangle"\n'
    "            elif upper_relative > flat_limit and lower_relative > flat_limit:\n"
    '                pattern_type = "Expanding Rising Wedge"\n'
    "            elif upper_relative < -flat_limit and lower_relative < -flat_limit:\n"
    '                pattern_type = "Expanding Falling Wedge"\n'
    "            else:\n"
    '                pattern_type = "Broadening Triangle"\n'
    '                family = "triangle"\n'
    "\n"
    '        if family == "channel" and not allow_channels:\n'
    "            continue\n"
    '        if family == "wedge" and not allow_wedges:\n'
    "            continue\n"
    '        if family == "triangle" and not allow_triangles:\n'
    "            continue\n"
    "\n"
    "        return {\n"
    '            "type": pattern_type,\n'
    '            "upper_slope": upper_slope,\n'
    '            "upper_intercept": upper_intercept,\n'
    '            "lower_slope": lower_slope,\n'
    '            "lower_intercept": lower_intercept,\n'
    '            "start": current_index,\n'
    "        }\n"
    "    return None\n"
    "\n"
    "\n"
    "# Causal percentage-reversal ZigZag. A pivot is appended on the bar that\n"
    "# confirms the reversal, never on the earlier extremum bar itself.\n"
    "pivots = []\n"
    "direction = 0\n"
    "extreme_index = -1\n"
    "extreme_value = np.nan\n"
    "active_pattern = None\n"
    "previous_top = np.nan\n"
    "previous_bottom = np.nan\n"
    "\n"
    "for i in range(n):\n"
    "    value = source[i]\n"
    "    if not np.isfinite(value):\n"
    "        continue\n"
    "\n"
    "    confirmed_pivot = False\n"
    "    if extreme_index < 0:\n"
    "        extreme_index = i\n"
    "        extreme_value = float(value)\n"
    "        continue\n"
    "\n"
    "    if direction == 0:\n"
    "        if value >= extreme_value * (1.0 + threshold):\n"
    '            pivots.append((extreme_index, extreme_value, "low"))\n'
    "            direction = 1\n"
    "            extreme_index = i\n"
    "            extreme_value = float(value)\n"
    "            confirmed_pivot = True\n"
    "        elif value <= extreme_value * (1.0 - threshold):\n"
    '            pivots.append((extreme_index, extreme_value, "high"))\n'
    "            direction = -1\n"
    "            extreme_index = i\n"
    "            extreme_value = float(value)\n"
    "            confirmed_pivot = True\n"
    "    elif direction == 1:\n"
    "        if value >= extreme_value:\n"
    "            extreme_index = i\n"
    "            extreme_value = float(value)\n"
    "        elif value <= extreme_value * (1.0 - threshold):\n"
    '            pivots.append((extreme_index, extreme_value, "high"))\n'
    "            direction = -1\n"
    "            extreme_index = i\n"
    "            extreme_value = float(value)\n"
    "            confirmed_pivot = True\n"
    "    else:\n"
    "        if value <= extreme_value:\n"
    "            extreme_index = i\n"
    "            extreme_value = float(value)\n"
    "        elif value >= extreme_value * (1.0 + threshold):\n"
    '            pivots.append((extreme_index, extreme_value, "low"))\n'
    "            direction = 1\n"
    "            extreme_index = i\n"
    "            extreme_value = float(value)\n"
    "            confirmed_pivot = True\n"
    "\n"
    "    if confirmed_pivot:\n"
    "        candidate = _pattern_candidate(pivots, i)\n"
    "        can_replace = (\n"
    "            candidate is not None\n"
    "            and (\n"
    "                not avoid_overlap\n"
    "                or active_pattern is None\n"
    '                or i - active_pattern["start"] >= max_patterns\n'
    "            )\n"
    "        )\n"
    "        if can_replace:\n"
    "            active_pattern = candidate\n"
    '            pattern_events[i] = candidate["type"]\n'
    "\n"
    '    if active_pattern is None or i < active_pattern["start"]:\n'
    "        continue\n"
    "\n"
    '    top_value = active_pattern["upper_slope"] * i + active_pattern["upper_intercept"]\n'
    '    bottom_value = active_pattern["lower_slope"] * i + active_pattern["lower_intercept"]\n'
    "    if not np.isfinite(top_value) or not np.isfinite(bottom_value) or top_value <= bottom_value:\n"
    "        active_pattern = None\n"
    "        continue\n"
    "\n"
    "    top_line[i] = top_value\n"
    "    bottom_line[i] = bottom_value\n"
    "    mid_line[i] = (top_value + bottom_value) / 2.0\n"
    "\n"
    '    if i > active_pattern["start"] and np.isfinite(close[i - 1]):\n'
    "        if np.isfinite(previous_top) and close[i - 1] <= previous_top and close[i] > top_value:\n"
    "            buy_signal[i] = True\n"
    "        if np.isfinite(previous_bottom) and close[i - 1] >= previous_bottom and close[i] < bottom_value:\n"
    "            sell_signal[i] = True\n"
    "    previous_top = top_value\n"
    "    previous_bottom = bottom_value\n"
    "\n"
    "\n"
    "def _plot_values(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    "buy_marks = [float(low[i]) * 0.995 if buy_signal[i] and np.isfinite(low[i]) else None for i in range(n)]\n"
    "sell_marks = [float(high[i]) * 1.005 if sell_signal[i] and np.isfinite(high[i]) else None for i in range(n)]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Pattern Top", "data": _plot_values(top_line), "color": "#EF5350", "overlay": True},\n'
    '        {"name": "Pattern Mid", "data": _plot_values(mid_line), "color": "#FFB300", "overlay": True},\n'
    '        {"name": "Pattern Bottom", "data": _plot_values(bottom_line), "color": "#26A69A", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "ACP+", "data": buy_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "ACP-", "data": sell_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    '    "metadata": {\n'
    '        "pattern_type": pattern_events,\n'
    '        "causal": True,\n'
    '        "source": source_name,\n'
    "    },\n"
    "}\n"
)
