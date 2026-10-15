"""Chart-only source for the true_strength_index indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] True Strength Index\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Double-smoothed price momentum normalized by double-smoothed absolute\n"
    "# momentum. Exponential smoothing is causal and stable as bars are appended.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] True Strength Index"\n'
    'my_indicator_description = "Double-smoothed, normalized momentum with a signal line."\n'
    "\n"
    "# @param long_period int 25 Long EMA period range=2:200:1\n"
    "# @param short_period int 13 Short EMA period range=2:100:1\n"
    "# @param signal_period int 7 Signal EMA period range=2:100:1\n"
    "\n"
    'long_period = max(2, int(params.get("long_period", 25)))\n'
    'short_period = max(2, int(params.get("short_period", 13)))\n'
    'signal_period = max(2, int(params.get("signal_period", 7)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "momentum = close.diff()\n"
    "smoothed_momentum = momentum.ewm(span=long_period, adjust=False, min_periods=long_period).mean().ewm(\n"
    "    span=short_period, adjust=False, min_periods=short_period\n"
    ").mean()\n"
    "smoothed_absolute = momentum.abs().ewm(span=long_period, adjust=False, min_periods=long_period).mean().ewm(\n"
    "    span=short_period, adjust=False, min_periods=short_period\n"
    ").mean()\n"
    "tsi = 100.0 * smoothed_momentum / smoothed_absolute.replace(0.0, np.nan)\n"
    "tsi = tsi.replace([np.inf, -np.inf], np.nan)\n"
    "signal = tsi.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "TSI", "data": plot_list(tsi), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
