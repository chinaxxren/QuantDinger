"""Chart-only source for the schaff_trend_cycle indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Schaff Trend Cycle\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Applies two rolling stochastic transforms to MACD, with recursive smoothing.\n"
    "# Every rolling range is trailing and each recursive stage uses past state only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Schaff Trend Cycle"\n'
    'my_indicator_description = "Smoothed double-stochastic MACD cycle oscillator."\n'
    "\n"
    "# @param fast_period int 23 Fast MACD EMA period range=2:150:1\n"
    "# @param slow_period int 50 Slow MACD EMA period range=3:250:1\n"
    "# @param cycle_period int 10 Stochastic cycle period range=2:100:1\n"
    "# @param smoothing float 0.5 Recursive smoothing factor range=0.1:1.0:0.1\n"
    "\n"
    'fast_period = max(2, int(params.get("fast_period", 23)))\n'
    'slow_period = max(fast_period + 1, int(params.get("slow_period", 50)))\n'
    'cycle_period = max(2, int(params.get("cycle_period", 10)))\n'
    'smoothing = min(1.0, max(0.01, float(params.get("smoothing", 0.5))))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "macd = close.ewm(span=fast_period, adjust=False, min_periods=fast_period).mean() - close.ewm(\n"
    "    span=slow_period, adjust=False, min_periods=slow_period\n"
    ").mean()\n"
    "macd_min = macd.rolling(cycle_period, min_periods=cycle_period).min()\n"
    "macd_max = macd.rolling(cycle_period, min_periods=cycle_period).max()\n"
    "macd_width = macd_max - macd_min\n"
    "first_raw = 100.0 * (macd - macd_min) / macd_width.replace(0.0, np.nan)\n"
    "first_raw = first_raw.where(macd_width != 0.0, 50.0)\n"
    "first_values = first_raw.to_numpy()\n"
    "first_cycle = np.full(len(df), np.nan)\n"
    "previous = 50.0\n"
    "for i, value in enumerate(first_values):\n"
    "    if not np.isfinite(value):\n"
    "        continue\n"
    "    previous = smoothing * float(value) + (1.0 - smoothing) * previous\n"
    "    first_cycle[i] = previous\n"
    "second_series = pd.Series(first_cycle, index=df.index)\n"
    "second_min = second_series.rolling(cycle_period, min_periods=cycle_period).min()\n"
    "second_max = second_series.rolling(cycle_period, min_periods=cycle_period).max()\n"
    "second_width = second_max - second_min\n"
    "second_raw = 100.0 * (second_series - second_min) / second_width.replace(0.0, np.nan)\n"
    "second_raw = second_raw.where(second_width != 0.0, 50.0)\n"
    "second_values = second_raw.to_numpy()\n"
    "cycle = np.full(len(df), np.nan)\n"
    "previous = 50.0\n"
    "for i, value in enumerate(second_values):\n"
    "    if not np.isfinite(value):\n"
    "        continue\n"
    "    previous = smoothing * float(value) + (1.0 - smoothing) * previous\n"
    "    cycle[i] = previous\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "STC", "data": plot_list(cycle), "color": "#2962FF", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
