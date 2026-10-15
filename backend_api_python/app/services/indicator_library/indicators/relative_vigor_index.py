"""Chart-only source for the relative_vigor_index indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Relative Vigor Index\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Compares close-open movement with the high-low range using trailing weighted\n"
    "# smoothing, then computes a trailing signal line. No future bars are used.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Relative Vigor Index"\n'
    'my_indicator_description = "OHLC vigor oscillator with a weighted signal line."\n'
    "\n"
    "# @param period int 10 RVI signal period range=2:100:1\n"
    "\n"
    'period = max(2, int(params.get("period", 10)))\n'
    "\n"
    "df = df.copy()\n"
    'open_price = df["open"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "price_move = close - open_price\n"
    "price_range = (high - low).clip(lower=0.0)\n"
    "weights = np.array([1.0, 2.0, 2.0, 1.0])\n"
    "\n"
    "def trailing_weighted_average(values):\n"
    "    return float(np.dot(values, weights) / weights.sum())\n"
    "\n"
    "smoothed_move = price_move.rolling(4, min_periods=4).apply(trailing_weighted_average, raw=True)\n"
    "smoothed_range = price_range.rolling(4, min_periods=4).apply(trailing_weighted_average, raw=True)\n"
    "rvi = smoothed_move / smoothed_range.replace(0.0, np.nan)\n"
    "signal = rvi.rolling(period, min_periods=period).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "RVI", "data": plot_list(rvi), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
