"""Chart-only source for the adaptive_trend_filter indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Adaptive Trend Filter\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# A recursive variance-aware price estimator followed by an ATR supertrend.\n"
    "# Both calculations are causal and intended for visual trend confirmation.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Adaptive Trend Filter"\n'
    'my_indicator_description = "Variance-adaptive price filter with ATR supertrend bands."\n'
    "\n"
    "# @param alpha_filter float 0.01 Filter responsiveness coefficient range=0.001:1.0:0.001\n"
    "# @param beta_filter float 0.1 Process-noise coefficient range=0.001:2.0:0.001\n"
    "# @param filter_period int 21 Filter scaling period range=2:100:1\n"
    "# @param supertrend_factor float 1.0 ATR band multiplier range=0.25:8.0:0.25\n"
    "# @param atr_period int 7 ATR period range=2:100:1\n"
    "\n"
    'alpha_filter = max(0.0001, float(params.get("alpha_filter", 0.01)))\n'
    'beta_filter = max(0.0001, float(params.get("beta_filter", 0.1)))\n'
    'filter_period = max(2, int(params.get("filter_period", 21)))\n'
    'supertrend_factor = max(0.05, float(params.get("supertrend_factor", 1.0)))\n'
    'atr_period = max(2, int(params.get("atr_period", 7)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    "cl = close.to_numpy()\n"
    "estimated = np.full(len(df), np.nan)\n"
    "variance = 1.0\n"
    "coefficient = alpha_filter * filter_period\n"
    "for i in range(len(df)):\n"
    "    if not np.isfinite(cl[i]):\n"
    "        continue\n"
    "    if i == 0 or not np.isfinite(estimated[i - 1]):\n"
    "        estimated[i] = cl[i]\n"
    "        continue\n"
    "    gain = variance / (variance + coefficient)\n"
    "    estimated[i] = estimated[i - 1] + gain * (cl[i] - estimated[i - 1])\n"
    "    variance = (1.0 - gain) * variance + beta_filter / filter_period\n"
    "filtered = pd.Series(estimated, index=df.index)\n"
    "previous_close = close.shift(1)\n"
    "true_range = pd.concat([\n"
    "    high - low,\n"
    "    (high - previous_close).abs(),\n"
    "    (low - previous_close).abs(),\n"
    "], axis=1).max(axis=1)\n"
    "atr = true_range.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()\n"
    "upper_basic = filtered + supertrend_factor * atr\n"
    "lower_basic = filtered - supertrend_factor * atr\n"
    "upper = upper_basic.to_numpy(copy=True)\n"
    "lower = lower_basic.to_numpy(copy=True)\n"
    "trend_line = np.full(len(df), np.nan)\n"
    "direction = np.zeros(len(df), dtype=int)\n"
    "for i in range(len(df)):\n"
    "    if not np.isfinite(upper[i]) or not np.isfinite(lower[i]):\n"
    "        continue\n"
    "    if i == 0 or direction[i - 1] == 0:\n"
    "        direction[i] = 1 if cl[i] >= filtered.iloc[i] else -1\n"
    "    else:\n"
    "        if direction[i - 1] > 0:\n"
    "            upper[i] = min(upper[i], upper[i - 1])\n"
    "            direction[i] = -1 if cl[i] < upper[i - 1] else 1\n"
    "        else:\n"
    "            lower[i] = max(lower[i], lower[i - 1])\n"
    "            direction[i] = 1 if cl[i] > lower[i - 1] else -1\n"
    "    trend_line[i] = lower[i] if direction[i] > 0 else upper[i]\n"
    "previous_direction = np.concatenate([[0], direction[:-1]])\n"
    "buy = (direction == 1) & (previous_direction == -1)\n"
    "sell = (direction == -1) & (previous_direction == 1)\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "low_values = low.to_numpy()\n"
    "high_values = high.to_numpy()\n"
    "buy_marks = [float(low_values[i]) * 0.995 if buy[i] else None for i in range(len(df))]\n"
    "sell_marks = [float(high_values[i]) * 1.005 if sell[i] else None for i in range(len(df))]\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Adaptive Filter", "data": plot_list(estimated), "color": "#2962FF", "overlay": True},\n'
    '        {"name": "Adaptive SuperTrend", "data": plot_list(trend_line), "color": "#FFB300", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "ATF+", "data": buy_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "ATF-", "data": sell_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
