"""Chart-only source for the alpha_trend indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] AlphaTrend\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# ATR bands are ratcheted according to RSI momentum. The recursive state only\n"
    "# uses current and prior bars; cross markers are visual, not order actions.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] AlphaTrend"\n'
    'my_indicator_description = "RSI-confirmed ATR trend line with chart-only crossover markers."\n'
    "\n"
    "# @param atr_period int 14 ATR period range=2:100:1\n"
    "# @param momentum_period int 14 RSI period range=2:100:1\n"
    "# @param multiplier float 1.0 ATR channel multiplier range=0.25:8.0:0.25\n"
    "# @param confirmation_lag int 2 Signal comparison lag range=1:10:1\n"
    "\n"
    'atr_period = max(2, int(params.get("atr_period", 14)))\n'
    'momentum_period = max(2, int(params.get("momentum_period", 14)))\n'
    'multiplier = max(0.05, float(params.get("multiplier", 1.0)))\n'
    'confirmation_lag = max(1, int(params.get("confirmation_lag", 2)))\n'
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
    "delta = close.diff()\n"
    "gain = delta.clip(lower=0.0)\n"
    "loss = -delta.clip(upper=0.0)\n"
    "average_gain = gain.ewm(alpha=1.0 / momentum_period, adjust=False, min_periods=momentum_period).mean()\n"
    "average_loss = loss.ewm(alpha=1.0 / momentum_period, adjust=False, min_periods=momentum_period).mean()\n"
    "relative_strength = average_gain / average_loss.replace(0.0, np.nan)\n"
    "rsi = (100.0 - 100.0 / (1.0 + relative_strength)).fillna(50.0).to_numpy()\n"
    "cl = close.to_numpy()\n"
    "lo = low.to_numpy()\n"
    "hi = high.to_numpy()\n"
    "trend_line = np.full(len(df), np.nan)\n"
    "trend = np.zeros(len(df), dtype=int)\n"
    "for i in range(len(df)):\n"
    "    if not np.isfinite(atr[i]):\n"
    "        continue\n"
    "    lower_band = cl[i] - multiplier * float(atr[i])\n"
    "    upper_band = cl[i] + multiplier * float(atr[i])\n"
    "    bullish = rsi[i] >= 50.0\n"
    "    if i == 0 or not np.isfinite(trend_line[i - 1]):\n"
    "        trend_line[i] = lower_band if bullish else upper_band\n"
    "    elif bullish:\n"
    "        trend_line[i] = max(lower_band, trend_line[i - 1])\n"
    "    else:\n"
    "        trend_line[i] = min(upper_band, trend_line[i - 1])\n"
    "    trend[i] = 1 if bullish else -1\n"
    "\n"
    "lagged = np.concatenate([np.full(min(confirmation_lag, len(df)), np.nan), trend_line[:-confirmation_lag]]) if len(df) > confirmation_lag else np.full(len(df), np.nan)\n"
    "previous_gap = np.concatenate([[np.nan], (trend_line - lagged)[:-1]]) if len(df) else np.array([])\n"
    "current_gap = trend_line - lagged\n"
    "buy = (current_gap > 0.0) & (previous_gap <= 0.0) & np.isfinite(current_gap) & np.isfinite(previous_gap)\n"
    "sell = (current_gap < 0.0) & (previous_gap >= 0.0) & np.isfinite(current_gap) & np.isfinite(previous_gap)\n"
    "line_values = [None if not np.isfinite(value) else float(value) for value in trend_line]\n"
    "buy_marks = [float(lo[i]) * 0.995 if buy[i] else None for i in range(len(df))]\n"
    "sell_marks = [float(hi[i]) * 1.005 if sell[i] else None for i in range(len(df))]\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [{"name": "AlphaTrend", "data": line_values, "color": "#26A69A", "overlay": True}],\n'
    '    "signals": [\n'
    '        {"type": "buy", "text": "AT+", "data": buy_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "AT-", "data": sell_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
