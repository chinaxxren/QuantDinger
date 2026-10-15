"""Chart-only source for the ut_bot_alerts indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] UT Bot Alerts\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# ATR-based causal trailing stop. Crosses are chart annotations only and do\n"
    "# not place, modify, or close trades.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] UT Bot Alerts"\n'
    'my_indicator_description = "ATR trailing stop with chart-only price-cross markers."\n'
    "\n"
    "# @param atr_period int 10 ATR period range=2:100:1\n"
    "# @param key_value float 1.0 ATR sensitivity multiplier range=0.25:10.0:0.25\n"
    "\n"
    'atr_period = max(2, int(params.get("atr_period", 10)))\n'
    'key_value = max(0.05, float(params.get("key_value", 1.0)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "previous_close = close.shift(1)\n"
    "true_range = pd.concat([\n"
    "    high - low,\n"
    "    (high - previous_close).abs(),\n"
    "    (low - previous_close).abs(),\n"
    "], axis=1).max(axis=1)\n"
    "atr = true_range.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean().to_numpy()\n"
    "cl = close.to_numpy()\n"
    "lo = low.to_numpy()\n"
    "hi = high.to_numpy()\n"
    "stop = np.full(len(df), np.nan)\n"
    "trend = np.zeros(len(df), dtype=int)\n"
    "for i in range(len(df)):\n"
    "    if not np.isfinite(atr[i]):\n"
    "        continue\n"
    "    loss = float(atr[i]) * key_value\n"
    "    if i == 0 or not np.isfinite(stop[i - 1]):\n"
    "        stop[i] = cl[i] - loss\n"
    "        trend[i] = 1\n"
    "        continue\n"
    "    previous_stop = stop[i - 1]\n"
    "    previous_price = cl[i - 1]\n"
    "    if previous_price > previous_stop and cl[i] > previous_stop:\n"
    "        stop[i] = max(previous_stop, cl[i] - loss)\n"
    "    elif previous_price < previous_stop and cl[i] < previous_stop:\n"
    "        stop[i] = min(previous_stop, cl[i] + loss)\n"
    "    elif cl[i] > previous_stop:\n"
    "        stop[i] = cl[i] - loss\n"
    "    else:\n"
    "        stop[i] = cl[i] + loss\n"
    "    trend[i] = 1 if cl[i] > stop[i] else -1\n"
    "\n"
    "previous_trend = np.concatenate([[0], trend[:-1]])\n"
    "buy = (trend == 1) & (previous_trend == -1)\n"
    "sell = (trend == -1) & (previous_trend == 1)\n"
    "stop_values = [None if not np.isfinite(value) else float(value) for value in stop]\n"
    "buy_marks = [float(lo[i]) * 0.995 if buy[i] else None for i in range(len(df))]\n"
    "sell_marks = [float(hi[i]) * 1.005 if sell[i] else None for i in range(len(df))]\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [{"name": "UT Bot Stop", "data": stop_values, "color": "#FFB300", "overlay": True}],\n'
    '    "signals": [\n'
    '        {"type": "buy", "text": "UT Buy", "data": buy_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "UT Sell", "data": sell_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
