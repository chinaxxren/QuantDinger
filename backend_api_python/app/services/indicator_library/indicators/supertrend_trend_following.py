"""Chart-only source for the supertrend_trend_following indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Sample] SuperTrend Trend-Following -- classic ATR channel flip\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# This is a chart-only indicator. It never opens, closes, sizes, or manages\n"
    "# trades. Convert it to a Strategy API source before backtesting or live trading.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Sample] SuperTrend Trend-Following"\n'
    "my_indicator_description = (\n"
    '    "Classic SuperTrend: ATR-channel direction flip with chart-only bullish "\n'
    '    "and bearish markers."\n'
    ")\n"
    "\n"
    "# @param atr_period int 10 ATR Wilder smoothing period range=7:21:1\n"
    "# @param multiplier float 3.0 ATR band multiplier range=1.5:5.0:0.5\n"
    "\n"
    'atr_period = int(params.get("atr_period", 10))\n'
    'multiplier = float(params.get("multiplier", 3.0))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"]\n'
    'low = df["low"]\n'
    'close = df["close"]\n'
    "prev_close = close.shift(1)\n"
    "\n"
    "tr = pd.concat([\n"
    "    high - low,\n"
    "    (high - prev_close).abs(),\n"
    "    (low - prev_close).abs(),\n"
    "], axis=1).max(axis=1)\n"
    "atr = tr.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()\n"
    "\n"
    "hl2 = (high + low) / 2.0\n"
    "upper_basic = hl2 + multiplier * atr\n"
    "lower_basic = hl2 - multiplier * atr\n"
    "\n"
    "n = len(df)\n"
    "ub = upper_basic.to_numpy()\n"
    "lb = lower_basic.to_numpy()\n"
    "cl = close.to_numpy()\n"
    "\n"
    "final_upper = np.full(n, np.nan)\n"
    "final_lower = np.full(n, np.nan)\n"
    "direction = np.zeros(n, dtype=np.int8)\n"
    "supertrend = np.full(n, np.nan)\n"
    "start_idx = int(atr_period)\n"
    "\n"
    "for i in range(n):\n"
    "    if i < start_idx or np.isnan(ub[i]) or np.isnan(lb[i]):\n"
    "        continue\n"
    "\n"
    "    if i == start_idx or direction[i - 1] == 0:\n"
    "        final_upper[i] = ub[i]\n"
    "        final_lower[i] = lb[i]\n"
    "        direction[i] = 1 if cl[i] >= (ub[i] + lb[i]) / 2.0 else -1\n"
    "        supertrend[i] = final_lower[i] if direction[i] == 1 else final_upper[i]\n"
    "        continue\n"
    "\n"
    "    final_upper[i] = ub[i] if (ub[i] < final_upper[i - 1]) or (cl[i - 1] > final_upper[i - 1]) else final_upper[i - 1]\n"
    "    final_lower[i] = lb[i] if (lb[i] > final_lower[i - 1]) or (cl[i - 1] < final_lower[i - 1]) else final_lower[i - 1]\n"
    "\n"
    "    if cl[i] > final_upper[i - 1]:\n"
    "        direction[i] = 1\n"
    "    elif cl[i] < final_lower[i - 1]:\n"
    "        direction[i] = -1\n"
    "    else:\n"
    "        direction[i] = direction[i - 1]\n"
    "\n"
    "    supertrend[i] = final_lower[i] if direction[i] == 1 else final_upper[i]\n"
    "\n"
    "prev_direction = np.concatenate([[0], direction[:-1]])\n"
    "flip_long = (direction == 1) & (prev_direction == -1)\n"
    "flip_short = (direction == -1) & (prev_direction == 1)\n"
    "\n"
    "supertrend_up = [float(v) if (d == 1 and not np.isnan(v)) else None for v, d in zip(supertrend, direction)]\n"
    "supertrend_dn = [float(v) if (d == -1 and not np.isnan(v)) else None for v, d in zip(supertrend, direction)]\n"
    "\n"
    "long_marks = [float(low.iloc[i]) * 0.995 if bool(flip_long[i]) else None for i in range(n)]\n"
    "short_marks = [float(high.iloc[i]) * 1.005 if bool(flip_short[i]) else None for i in range(n)]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "SuperTrend Up", "data": supertrend_up, "color": "#00E676", "overlay": True},\n'
    '        {"name": "SuperTrend Down", "data": supertrend_dn, "color": "#FF5252", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "L", "data": long_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "S", "data": short_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
