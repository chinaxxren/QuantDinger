"""Chart-only source for the keltner_channel indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Keltner Channel\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# EMA centerline with Wilder ATR envelopes. Every input uses current or prior\n"
    "# bars only, so historical channel values remain stable as new bars arrive.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Keltner Channel"\n'
    'my_indicator_description = "EMA centerline with ATR-based volatility envelopes."\n'
    "\n"
    "# @param period int 20 EMA centerline period range=2:200:1\n"
    "# @param atr_period int 10 ATR period range=2:100:1\n"
    "# @param multiplier float 2.0 ATR band multiplier range=0.25:8.0:0.25\n"
    "\n"
    'period = max(2, int(params.get("period", 20)))\n'
    'atr_period = max(2, int(params.get("atr_period", 10)))\n'
    'multiplier = max(0.05, float(params.get("multiplier", 2.0)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    "center = close.ewm(span=period, adjust=False, min_periods=period).mean()\n"
    "previous_close = close.shift(1)\n"
    "true_range = pd.concat([\n"
    "    high - low,\n"
    "    (high - previous_close).abs(),\n"
    "    (low - previous_close).abs(),\n"
    "], axis=1).max(axis=1)\n"
    "atr = true_range.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()\n"
    "upper = center + multiplier * atr\n"
    "lower = center - multiplier * atr\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Upper", "data": plot_list(upper), "color": "#26A69A", "overlay": True},\n'
    '        {"name": "EMA", "data": plot_list(center), "color": "#2962FF", "overlay": True},\n'
    '        {"name": "Lower", "data": plot_list(lower), "color": "#EF5350", "overlay": True},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
