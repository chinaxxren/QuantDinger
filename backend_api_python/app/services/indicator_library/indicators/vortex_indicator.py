"""Chart-only source for the vortex_indicator indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Vortex Indicator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Compares directional movement between the current high/low and prior low/high\n"
    "# with true range over a trailing window. The current bar is never future data.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Vortex Indicator"\n'
    'my_indicator_description = "Positive and negative directional movement ratios over true range."\n'
    "\n"
    "# @param period int 14 Rolling calculation period range=2:200:1\n"
    "\n"
    'period = max(2, int(params.get("period", 14)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "previous_high = high.shift(1)\n"
    "previous_low = low.shift(1)\n"
    "previous_close = close.shift(1)\n"
    "positive_movement = (high - previous_low).abs()\n"
    "negative_movement = (low - previous_high).abs()\n"
    "true_range = pd.concat([\n"
    "    high - low,\n"
    "    (high - previous_close).abs(),\n"
    "    (low - previous_close).abs(),\n"
    "], axis=1).max(axis=1)\n"
    "positive_sum = positive_movement.rolling(period, min_periods=period).sum()\n"
    "negative_sum = negative_movement.rolling(period, min_periods=period).sum()\n"
    "range_sum = true_range.rolling(period, min_periods=period).sum().replace(0.0, np.nan)\n"
    "vortex_positive = positive_sum / range_sum\n"
    "vortex_negative = negative_sum / range_sum\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "VI+", "data": plot_list(vortex_positive), "color": "#26A69A", "overlay": False},\n'
    '        {"name": "VI-", "data": plot_list(vortex_negative), "color": "#EF5350", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
