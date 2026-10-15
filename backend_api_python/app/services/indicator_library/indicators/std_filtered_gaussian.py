"""Chart-only source for the std_filtered_gaussian indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] STD-Filtered N-Pole Gaussian Filter\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# A causal cascade of EMA poles with a standard-deviation deadband. The\n"
    "# deadband suppresses small changes without centered windows or future data.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] STD-Filtered N-Pole Gaussian Filter"\n'
    'my_indicator_description = "Standard-deviation filtered multi-pole Gaussian-style price smoother."\n'
    "\n"
    "# @param period int 25 Gaussian smoothing period range=2:200:1\n"
    "# @param poles int 5 Number of causal smoothing poles range=1:6:1\n"
    "# @param filter_period int 10 Deadband volatility lookback range=2:100:1\n"
    "# @param filter_strength float 1.0 Deadband standard deviation multiplier range=0.0:5.0:0.25\n"
    "\n"
    'period = max(2, int(params.get("period", 25)))\n'
    'poles = min(6, max(1, int(params.get("poles", 5))))\n'
    'filter_period = max(2, int(params.get("filter_period", 10)))\n'
    'filter_strength = max(0.0, float(params.get("filter_strength", 1.0)))\n'
    "\n"
    "df = df.copy()\n"
    'source = (df["open"].astype(float) + df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 4.0\n'
    "rolling_std = source.rolling(filter_period, min_periods=filter_period).std()\n"
    "filtered_values = source.to_numpy(copy=True)\n"
    "std_values = rolling_std.to_numpy()\n"
    "for i in range(1, len(filtered_values)):\n"
    "    if np.isfinite(filtered_values[i - 1]) and np.isfinite(std_values[i]):\n"
    "        if abs(filtered_values[i] - filtered_values[i - 1]) < filter_strength * std_values[i]:\n"
    "            filtered_values[i] = filtered_values[i - 1]\n"
    "filtered = pd.Series(filtered_values, index=df.index)\n"
    "for _ in range(poles):\n"
    "    filtered = filtered.ewm(span=period, adjust=False, min_periods=period).mean()\n"
    "final_std = filtered.rolling(filter_period, min_periods=filter_period).std()\n"
    "final_values = filtered.to_numpy(copy=True)\n"
    "final_std_values = final_std.to_numpy()\n"
    "for i in range(1, len(final_values)):\n"
    "    if np.isfinite(final_values[i - 1]) and np.isfinite(final_std_values[i]):\n"
    "        if abs(final_values[i] - final_values[i - 1]) < filter_strength * final_std_values[i]:\n"
    "            final_values[i] = final_values[i - 1]\n"
    "previous = np.concatenate([[np.nan], final_values[:-1]])\n"
    "up = np.isfinite(final_values) & np.isfinite(previous) & (final_values > previous)\n"
    "down = np.isfinite(final_values) & np.isfinite(previous) & (final_values < previous)\n"
    "previous_up = np.concatenate([[False], up[:-1]])\n"
    "previous_down = np.concatenate([[False], down[:-1]])\n"
    "buy = up & (~previous_up)\n"
    "sell = down & (~previous_down)\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    'low = df["low"].astype(float).to_numpy()\n'
    'high = df["high"].astype(float).to_numpy()\n'
    "buy_marks = [float(low[i]) * 0.995 if buy[i] else None for i in range(len(df))]\n"
    "sell_marks = [float(high[i]) * 1.005 if sell[i] else None for i in range(len(df))]\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Gaussian Filter", "data": plot_list(final_values), "color": "#2962FF", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "GF+", "data": buy_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "GF-", "data": sell_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
