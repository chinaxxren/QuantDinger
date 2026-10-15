"""Chart-only source for the vegas_supertrend indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Multi-Step Vegas SuperTrend\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# A Vegas EMA channel adjusts the ATR multiplier before a causal supertrend.\n"
    "# The original strategy's entries and exits are intentionally represented as\n"
    "# chart markers only; this source never places or manages trades.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Multi-Step Vegas SuperTrend"\n'
    'my_indicator_description = "Vegas volatility channel with an adaptive ATR supertrend and visual reversals."\n'
    "\n"
    "# @param atr_period int 10 ATR period range=2:100:1\n"
    "# @param vegas_period int 100 Vegas EMA and standard-deviation window range=5:300:1\n"
    "# @param supertrend_multiplier float 5.0 Base ATR multiplier range=0.5:12.0:0.5\n"
    "# @param volatility_adjustment float 5.0 Channel-width adjustment range=0.0:20.0:0.5\n"
    "\n"
    'atr_period = max(2, int(params.get("atr_period", 10)))\n'
    'vegas_period = max(5, int(params.get("vegas_period", 100)))\n'
    'supertrend_multiplier = max(0.05, float(params.get("supertrend_multiplier", 5.0)))\n'
    'volatility_adjustment = max(0.0, float(params.get("volatility_adjustment", 5.0)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    "vegas_average = close.ewm(span=vegas_period, adjust=False, min_periods=vegas_period).mean()\n"
    "vegas_deviation = close.rolling(vegas_period, min_periods=vegas_period).std()\n"
    "channel_width = 2.0 * vegas_deviation\n"
    "adjusted_multiplier = supertrend_multiplier + volatility_adjustment * (channel_width / vegas_average.replace(0.0, np.nan))\n"
    "previous_close = close.shift(1)\n"
    "true_range = pd.concat([\n"
    "    high - low,\n"
    "    (high - previous_close).abs(),\n"
    "    (low - previous_close).abs(),\n"
    "], axis=1).max(axis=1)\n"
    "atr = true_range.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()\n"
    "price_center = (high + low + close) / 3.0\n"
    "upper_basic = price_center - adjusted_multiplier * atr\n"
    "lower_basic = price_center + adjusted_multiplier * atr\n"
    "upper = upper_basic.to_numpy(copy=True)\n"
    "lower = lower_basic.to_numpy(copy=True)\n"
    "trend_line = np.full(len(df), np.nan)\n"
    "direction = np.zeros(len(df), dtype=int)\n"
    "for i in range(len(df)):\n"
    "    if not np.isfinite(upper[i]) or not np.isfinite(lower[i]):\n"
    "        continue\n"
    "    if i == 0 or direction[i - 1] == 0:\n"
    "        direction[i] = 1\n"
    "    else:\n"
    "        previous_upper = upper[i - 1]\n"
    "        previous_lower = lower[i - 1]\n"
    "        if direction[i - 1] > 0:\n"
    "            upper[i] = max(upper[i], previous_upper)\n"
    "            direction[i] = -1 if close.iloc[i] < previous_upper else 1\n"
    "        else:\n"
    "            lower[i] = min(lower[i], previous_lower)\n"
    "            direction[i] = 1 if close.iloc[i] > previous_lower else -1\n"
    "    trend_line[i] = upper[i] if direction[i] > 0 else lower[i]\n"
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
    '        {"name": "Vegas EMA", "data": plot_list(vegas_average), "color": "#42A5F5", "overlay": True},\n'
    '        {"name": "Vegas Upper", "data": plot_list(vegas_average + vegas_deviation), "color": "#90CAF9", "overlay": True},\n'
    '        {"name": "Vegas Lower", "data": plot_list(vegas_average - vegas_deviation), "color": "#90CAF9", "overlay": True},\n'
    '        {"name": "Vegas SuperTrend", "data": plot_list(trend_line), "color": "#FFB300", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "VS+", "data": buy_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "VS-", "data": sell_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
