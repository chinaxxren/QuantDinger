"""Chart-only source for the zero_lag_trend_signals indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Zero Lag Trend Signals\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Zero-lag EMA baseline with ATR-extreme volatility bands. It preserves the\n"
    "# original indicator's trend-flip and pullback signals while keeping all\n"
    "# calculations causal and chart-only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Zero Lag Trend Signals"\n'
    "my_indicator_description = (\n"
    '    "Zero-lag EMA trend baseline with ATR volatility bands and chart-only "\n'
    '    "trend-flip and pullback signals."\n'
    ")\n"
    "\n"
    "# @param length int 70 Zero-lag EMA and ATR lookback range=2:300:1\n"
    "# @param mult float 1.2 Volatility band multiplier range=0.1:10.0:0.1\n"
    "\n"
    'length = max(2, int(params.get("length", 70)))\n'
    'mult = max(0.05, float(params.get("mult", 1.2)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "cl = close.to_numpy()\n"
    "\n"
    "lag = max(1, int((length - 1) // 2))\n"
    "source = close + (close - close.shift(lag))\n"
    "zlema = source.ewm(span=length, adjust=False, min_periods=length).mean().to_numpy()\n"
    "\n"
    "previous_close = close.shift(1)\n"
    "true_range = pd.concat([\n"
    "    high - low,\n"
    "    (high - previous_close).abs(),\n"
    "    (low - previous_close).abs(),\n"
    "], axis=1).max(axis=1)\n"
    "atr = true_range.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()\n"
    "volatility = (atr.rolling(length * 3, min_periods=length * 3).max() * mult).to_numpy()\n"
    "upper = zlema + volatility\n"
    "lower = zlema - volatility\n"
    "\n"
    "n = len(df)\n"
    "trend = np.zeros(n, dtype=np.int8)\n"
    "for i in range(n):\n"
    "    if not np.isfinite(zlema[i]) or not np.isfinite(upper[i]) or not np.isfinite(lower[i]) or not np.isfinite(cl[i]):\n"
    "        continue\n"
    "\n"
    "    if i == 0 or trend[i - 1] == 0:\n"
    "        trend[i] = 1 if cl[i] >= zlema[i] else -1\n"
    "        continue\n"
    "\n"
    "    previous_zlema = zlema[i - 1]\n"
    "    previous_upper = upper[i - 1]\n"
    "    previous_lower = lower[i - 1]\n"
    "    previous_value = cl[i - 1]\n"
    "    if np.isfinite(previous_upper) and previous_value <= previous_upper and cl[i] > previous_upper:\n"
    "        trend[i] = 1\n"
    "    elif np.isfinite(previous_lower) and previous_value >= previous_lower and cl[i] < previous_lower:\n"
    "        trend[i] = -1\n"
    "    else:\n"
    "        trend[i] = trend[i - 1]\n"
    "\n"
    "previous_trend = np.concatenate([[0], trend[:-1]])\n"
    "trend_bull = (trend == 1) & (previous_trend == -1)\n"
    "trend_bear = (trend == -1) & (previous_trend == 1)\n"
    "\n"
    "# Pullback entries require the trend to be established on both bars and a\n"
    "# close crossing of the zero-lag baseline on the current bar.\n"
    "long_entry = np.zeros(n, dtype=bool)\n"
    "short_entry = np.zeros(n, dtype=bool)\n"
    "for i in range(1, n):\n"
    "    if trend[i] == 1 and trend[i - 1] == 1 and np.isfinite(zlema[i]) and np.isfinite(zlema[i - 1]):\n"
    "        long_entry[i] = np.isfinite(cl[i - 1]) and cl[i - 1] <= zlema[i - 1] and cl[i] > zlema[i]\n"
    "    elif trend[i] == -1 and trend[i - 1] == -1 and np.isfinite(zlema[i]) and np.isfinite(zlema[i - 1]):\n"
    "        short_entry[i] = np.isfinite(cl[i - 1]) and cl[i - 1] >= zlema[i - 1] and cl[i] < zlema[i]\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "# Keep the two trend-colored baseline plots separated for the existing chart\n"
    "# renderer. The active band is shown only in its corresponding trend state.\n"
    "zlema_bull = [float(zlema[i]) if trend[i] == 1 and np.isfinite(zlema[i]) else None for i in range(n)]\n"
    "zlema_bear = [float(zlema[i]) if trend[i] == -1 and np.isfinite(zlema[i]) else None for i in range(n)]\n"
    "upper_plot = [float(upper[i]) if trend[i] == -1 and np.isfinite(upper[i]) else None for i in range(n)]\n"
    "lower_plot = [float(lower[i]) if trend[i] == 1 and np.isfinite(lower[i]) else None for i in range(n)]\n"
    "\n"
    "low_values = low.to_numpy()\n"
    "high_values = high.to_numpy()\n"
    "long_marks = [float(low_values[i]) * 0.995 if long_entry[i] and np.isfinite(low_values[i]) else None for i in range(n)]\n"
    "short_marks = [float(high_values[i]) * 1.005 if short_entry[i] and np.isfinite(high_values[i]) else None for i in range(n)]\n"
    "bear_marks = [float(high_values[i]) * 1.015 if trend_bear[i] and np.isfinite(high_values[i]) else None for i in range(n)]\n"
    "bull_marks = [float(low_values[i]) * 0.985 if trend_bull[i] and np.isfinite(low_values[i]) else None for i in range(n)]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Zero Lag Bull", "data": zlema_bull, "color": "#00FFBB", "overlay": True},\n'
    '        {"name": "Zero Lag Bear", "data": zlema_bear, "color": "#FF1100", "overlay": True},\n'
    '        {"name": "Upper Band", "data": upper_plot, "color": "#FF5252", "overlay": True},\n'
    '        {"name": "Lower Band", "data": lower_plot, "color": "#00E676", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "Long", "data": long_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "Short", "data": short_marks, "color": "#FF5252"},\n'
    '        {"type": "sell", "text": "Bear", "data": bear_marks, "color": "#FF1744"},\n'
    '        {"type": "buy", "text": "Bull", "data": bull_marks, "color": "#00C853"},\n'
    "    ],\n"
    '    "metadata": {\n'
    '        "trend": [int(value) if value else None for value in trend],\n'
    '        "causal": True,\n'
    '        "source": "Zero Lag EMA + ATR extreme volatility bands",\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
