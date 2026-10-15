"""Chart-only source for the twin_range_filter indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Twin Range Filter\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Colinmck's Twin Range Filter. Two independently smoothed ranges are\n"
    "# averaged into one causal filter, with chart-only Long/Short markers.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Twin Range Filter"\n'
    "my_indicator_description = (\n"
    '    "Twin smoothed range filter with configurable source and chart-only Long/Short signals."\n'
    ")\n"
    "\n"
    "# @param source string close Source price: close, open, high, low, hl2, hlc3, or ohlc4\n"
    "# @param per1 int 27 Fast filter period range=2:200:1\n"
    "# @param mult1 float 1.6 Fast filter multiplier range=0.1:10.0:0.1\n"
    "# @param per2 int 55 Slow filter period range=2:300:1\n"
    "# @param mult2 float 2.0 Slow filter multiplier range=0.1:10.0:0.1\n"
    "\n"
    'source_name = str(params.get("source", "close")).strip().lower()\n'
    'per1 = max(2, int(params.get("per1", params.get("fast_period", 27))))\n'
    'mult1 = max(0.1, float(params.get("mult1", params.get("fast_multiplier", 1.6))))\n'
    'per2 = max(2, int(params.get("per2", params.get("slow_period", 55))))\n'
    'mult2 = max(0.1, float(params.get("mult2", params.get("slow_multiplier", 2.0))))\n'
    "\n"
    "df = df.copy()\n"
    'open_values = df["open"].astype(float)\n'
    'high_series = df["high"].astype(float)\n'
    'low_series = df["low"].astype(float)\n'
    'close_series = df["close"].astype(float)\n'
    "\n"
    'if source_name == "open":\n'
    "    source_series = open_values\n"
    'elif source_name == "high":\n'
    "    source_series = high_series\n"
    'elif source_name == "low":\n'
    "    source_series = low_series\n"
    'elif source_name == "hl2":\n'
    "    source_series = (high_series + low_series) / 2.0\n"
    'elif source_name == "hlc3":\n'
    "    source_series = (high_series + low_series + close_series) / 3.0\n"
    'elif source_name == "ohlc4":\n'
    "    source_series = (open_values + high_series + low_series + close_series) / 4.0\n"
    "else:\n"
    '    source_name = "close"\n'
    "    source_series = close_series\n"
    "\n"
    "source = source_series.to_numpy()\n"
    "n = len(df)\n"
    "price_delta = source_series.diff().abs().fillna(0.0)\n"
    "\n"
    "def smooth_range(period, multiplier):\n"
    "    average_range = price_delta.ewm(span=period, adjust=False).mean()\n"
    "    return (\n"
    "        average_range.ewm(span=max(1, period * 2 - 1), adjust=False).mean()\n"
    "        * multiplier\n"
    "    ).to_numpy()\n"
    "\n"
    "range_values = (smooth_range(per1, mult1) + smooth_range(per2, mult2)) / 2.0\n"
    "filt = np.full(n, np.nan, dtype=float)\n"
    "upward = np.zeros(n, dtype=float)\n"
    "downward = np.zeros(n, dtype=float)\n"
    "if n > 0 and np.isfinite(source[0]):\n"
    "    filt[0] = source[0]\n"
    "\n"
    "# Apply the Pine rngfilt ratchet: price must cross the current range edge\n"
    "# before the filter moves; otherwise the previous filter value is retained.\n"
    "for i in range(1, n):\n"
    "    value = source[i]\n"
    "    previous = filt[i - 1]\n"
    "    width = range_values[i]\n"
    "    if not np.isfinite(value) or not np.isfinite(previous) or not np.isfinite(width):\n"
    "        continue\n"
    "\n"
    "    if value > previous:\n"
    "        filt[i] = previous if value - width < previous else value - width\n"
    "    else:\n"
    "        filt[i] = previous if value + width > previous else value + width\n"
    "\n"
    "    if filt[i] > previous:\n"
    "        upward[i] = upward[i - 1] + 1.0\n"
    "        downward[i] = 0.0\n"
    "    elif filt[i] < previous:\n"
    "        downward[i] = downward[i - 1] + 1.0\n"
    "        upward[i] = 0.0\n"
    "    else:\n"
    "        upward[i] = upward[i - 1]\n"
    "        downward[i] = downward[i - 1]\n"
    "\n"
    "previous_source = np.concatenate([[np.nan], source[:-1]])\n"
    "source_moved = np.isfinite(source) & np.isfinite(previous_source) & (source != previous_source)\n"
    "long_condition = (\n"
    "    np.isfinite(source)\n"
    "    & np.isfinite(filt)\n"
    "    & (source > filt)\n"
    "    & (upward > 0)\n"
    "    & source_moved\n"
    ")\n"
    "short_condition = (\n"
    "    np.isfinite(source)\n"
    "    & np.isfinite(filt)\n"
    "    & (source < filt)\n"
    "    & (downward > 0)\n"
    "    & source_moved\n"
    ")\n"
    "\n"
    "condition_state = np.zeros(n, dtype=np.int8)\n"
    "long_signal = np.zeros(n, dtype=bool)\n"
    "short_signal = np.zeros(n, dtype=bool)\n"
    "state = 0\n"
    "for i in range(n):\n"
    "    if long_condition[i]:\n"
    "        long_signal[i] = state == -1\n"
    "        state = 1\n"
    "    elif short_condition[i]:\n"
    "        short_signal[i] = state == 1\n"
    "        state = -1\n"
    "    condition_state[i] = state\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "low = low_series.to_numpy()\n"
    "high = high_series.to_numpy()\n"
    "long_marks = [\n"
    "    float(low[i]) * 0.995 if long_signal[i] and np.isfinite(low[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "short_marks = [\n"
    "    float(high[i]) * 1.005 if short_signal[i] and np.isfinite(high[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Twin Range Filter", "data": plot_list(filt), "color": "#2962FF", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "Long", "data": long_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "Short", "data": short_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "metadata": {\n'
    '        "source": source_name,\n'
    '        "upward": [float(value) if value else None for value in upward],\n'
    '        "downward": [float(value) if value else None for value in downward],\n'
    '        "condition_state": [int(value) if value else None for value in condition_state],\n'
    '        "causal": True,\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
