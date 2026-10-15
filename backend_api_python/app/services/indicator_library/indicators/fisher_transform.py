"""Chart-only source for the fisher_transform indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Fisher Transform\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Maps the rolling midpoint position into a bounded recursive Fisher series.\n"
    "# The rolling range includes the current bar only; no centered/future window.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Fisher Transform"\n'
    'my_indicator_description = "Recursive Fisher transform of normalized rolling price position."\n'
    "\n"
    "# @param period int 10 Rolling normalization period range=2:200:1\n"
    "# @param signal_period int 1 Signal smoothing period range=1:50:1\n"
    "\n"
    'period = max(2, int(params.get("period", 10)))\n'
    'signal_period = max(1, int(params.get("signal_period", 1)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    "price = (high + low) / 2.0\n"
    "rolling_high = price.rolling(period, min_periods=period).max().to_numpy()\n"
    "rolling_low = price.rolling(period, min_periods=period).min().to_numpy()\n"
    "price_values = price.to_numpy()\n"
    "normalized = np.full(len(df), np.nan)\n"
    "fisher = np.full(len(df), np.nan)\n"
    "previous_value = 0.0\n"
    "previous_fisher = 0.0\n"
    "for i in range(len(df)):\n"
    "    if not np.isfinite(rolling_high[i]) or not np.isfinite(rolling_low[i]) or not np.isfinite(price_values[i]):\n"
    "        continue\n"
    "    width = rolling_high[i] - rolling_low[i]\n"
    "    raw = 0.0 if width <= 0.0 else 2.0 * ((price_values[i] - rolling_low[i]) / width - 0.5)\n"
    "    value = 0.33 * raw + 0.67 * previous_value\n"
    "    value = min(0.999, max(-0.999, value))\n"
    "    transformed = 0.5 * np.log((1.0 + value) / (1.0 - value)) + 0.5 * previous_fisher\n"
    "    normalized[i] = value\n"
    "    fisher[i] = transformed\n"
    "    previous_value = value\n"
    "    previous_fisher = transformed\n"
    "signal = pd.Series(fisher, index=df.index).ewm(\n"
    "    span=signal_period, adjust=False, min_periods=signal_period\n"
    ").mean().to_numpy()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Fisher", "data": plot_list(fisher), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
