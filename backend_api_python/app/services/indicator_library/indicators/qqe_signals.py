"""Chart-only source for the qqe_signals indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] QQE Signals\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# RSI-based adaptive trailing levels. All smoothing and state transitions use\n"
    "# current and prior bars; markers are visual only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] QQE Signals"\n'
    'my_indicator_description = "Smoothed RSI with volatility-adaptive QQE trailing levels and chart-only signals."\n'
    "\n"
    "# @param rsi_period int 14 RSI period range=2:100:1\n"
    "# @param rsi_smoothing int 5 RSI smoothing period range=1:50:1\n"
    "# @param qqe_factor float 4.236 Trailing-level multiplier range=0.5:10.0:0.1\n"
    "\n"
    'rsi_period = max(2, int(params.get("rsi_period", 14)))\n'
    'rsi_smoothing = max(1, int(params.get("rsi_smoothing", 5)))\n'
    'qqe_factor = max(0.1, float(params.get("qqe_factor", 4.236)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "delta = close.diff()\n"
    "gain = delta.clip(lower=0.0)\n"
    "loss = -delta.clip(upper=0.0)\n"
    "average_gain = gain.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()\n"
    "average_loss = loss.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()\n"
    "rsi = 100.0 - 100.0 / (1.0 + average_gain / average_loss.replace(0.0, np.nan))\n"
    "rsi = rsi.where(average_loss != 0.0, 100.0)\n"
    "rsi = rsi.where(average_gain != 0.0, 0.0)\n"
    "rsi = rsi.fillna(50.0)\n"
    "smoothed_rsi = rsi.ewm(span=rsi_smoothing, adjust=False, min_periods=rsi_smoothing).mean().to_numpy()\n"
    "rsi_delta = pd.Series(smoothed_rsi).diff().abs()\n"
    "range_first = rsi_delta.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()\n"
    "range_second = range_first.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()\n"
    "trailing_range = (range_second * qqe_factor).to_numpy()\n"
    "long_band = np.full(len(df), np.nan)\n"
    "short_band = np.full(len(df), np.nan)\n"
    "trend = np.zeros(len(df), dtype=int)\n"
    "for i in range(len(df)):\n"
    "    value = smoothed_rsi[i]\n"
    "    distance = trailing_range[i]\n"
    "    if not np.isfinite(value) or not np.isfinite(distance):\n"
    "        continue\n"
    "    candidate_long = value - distance\n"
    "    candidate_short = value + distance\n"
    "    if i == 0 or not np.isfinite(long_band[i - 1]):\n"
    "        long_band[i] = candidate_long\n"
    "        short_band[i] = candidate_short\n"
    "        trend[i] = 1\n"
    "        continue\n"
    "    previous_long = long_band[i - 1]\n"
    "    previous_short = short_band[i - 1]\n"
    "    previous_value = smoothed_rsi[i - 1]\n"
    "    long_band[i] = max(previous_long, candidate_long) if previous_value > previous_long and value > previous_long else candidate_long\n"
    "    short_band[i] = min(previous_short, candidate_short) if previous_value < previous_short and value < previous_short else candidate_short\n"
    "    if value > previous_short:\n"
    "        trend[i] = 1\n"
    "    elif value < previous_long:\n"
    "        trend[i] = -1\n"
    "    else:\n"
    "        trend[i] = trend[i - 1]\n"
    "active_band = np.where(trend == 1, long_band, short_band)\n"
    "previous_trend = np.concatenate([[0], trend[:-1]])\n"
    "buy = (trend == 1) & (previous_trend == -1)\n"
    "sell = (trend == -1) & (previous_trend == 1)\n"
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
    '        {"name": "QQE RSI", "data": plot_list(smoothed_rsi), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "QQE Trail", "data": plot_list(active_band), "color": "#FF6D00", "overlay": False},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "QQE+", "data": buy_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "QQE-", "data": sell_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
