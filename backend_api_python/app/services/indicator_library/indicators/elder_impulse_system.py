"""Chart-only source for the elder_impulse_system indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Elder Impulse System\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Combines EMA slope and MACD histogram slope into causal impulse states.\n"
    "# States are exposed as chart markers only; no orders are submitted.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Elder Impulse System"\n'
    'my_indicator_description = "EMA and MACD momentum impulse states with chart-only color markers."\n'
    "\n"
    "# @param ema_length int 13 Trend EMA period range=2:100:1\n"
    "# @param macd_fast int 12 MACD fast period range=2:100:1\n"
    "# @param macd_slow int 26 MACD slow period range=3:200:1\n"
    "# @param macd_signal int 9 MACD signal period range=2:100:1\n"
    "\n"
    "def _int_param(name, default, minimum, maximum):\n"
    "    try:\n"
    "        value = int(params.get(name, default))\n"
    "    except (TypeError, ValueError):\n"
    "        value = default\n"
    "    return max(minimum, min(maximum, value))\n"
    "\n"
    'ema_length = _int_param("ema_length", 13, 2, 100)\n'
    'macd_fast = _int_param("macd_fast", 12, 2, 100)\n'
    'macd_slow = _int_param("macd_slow", 26, 3, 200)\n'
    "if macd_slow <= macd_fast:\n"
    "    macd_slow = min(200, macd_fast + 1)\n"
    'macd_signal = _int_param("macd_signal", 9, 2, 100)\n'
    "\n"
    "frame = df.copy()\n"
    'close = frame["close"].astype(float)\n'
    "ema = close.ewm(span=ema_length, adjust=False, min_periods=ema_length).mean()\n"
    "fast = close.ewm(span=macd_fast, adjust=False, min_periods=macd_fast).mean()\n"
    "slow = close.ewm(span=macd_slow, adjust=False, min_periods=macd_slow).mean()\n"
    "macd = fast - slow\n"
    "signal = macd.ewm(span=macd_signal, adjust=False, min_periods=macd_signal).mean()\n"
    "histogram = macd - signal\n"
    "\n"
    "ema_values = ema.to_numpy(dtype=float)\n"
    "hist_values = histogram.to_numpy(dtype=float)\n"
    "previous_ema = np.concatenate(([np.nan], ema_values[:-1]))\n"
    "previous_hist = np.concatenate(([np.nan], hist_values[:-1]))\n"
    "valid = (\n"
    "    np.isfinite(ema_values)\n"
    "    & np.isfinite(hist_values)\n"
    "    & np.isfinite(previous_ema)\n"
    "    & np.isfinite(previous_hist)\n"
    ")\n"
    "ema_rising = valid & (ema_values > previous_ema)\n"
    "ema_falling = valid & (ema_values < previous_ema)\n"
    "hist_rising = valid & (hist_values > previous_hist)\n"
    "hist_falling = valid & (hist_values < previous_hist)\n"
    "impulse = np.where(ema_rising & hist_rising, 1, np.where(ema_falling & hist_falling, -1, 0))\n"
    "\n"
    "previous_impulse = np.concatenate(([0], impulse[:-1]))\n"
    "buy = (impulse == 1) & (previous_impulse != 1)\n"
    "sell = (impulse == -1) & (previous_impulse != -1)\n"
    'high_values = frame["high"].astype(float).to_numpy(dtype=float)\n'
    'low_values = frame["low"].astype(float).to_numpy(dtype=float)\n'
    "\n"
    "def _plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "buy_marks = [float(low_values[i]) * 0.995 if buy[i] and np.isfinite(low_values[i]) else None for i in range(len(frame))]\n"
    "sell_marks = [float(high_values[i]) * 1.005 if sell[i] and np.isfinite(high_values[i]) else None for i in range(len(frame))]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Impulse EMA", "data": _plot_list(ema_values), "color": "#42A5F5", "overlay": True},\n'
    '        {"name": "MACD Histogram", "data": _plot_list(hist_values), "color": "#90CAF9", "overlay": False},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "Impulse Up", "data": buy_marks, "color": "#00C853"},\n'
    '        {"type": "sell", "text": "Impulse Down", "data": sell_marks, "color": "#FF1744"},\n'
    "    ],\n"
    '    "layers": [],\n'
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "ema_length": ema_length,\n'
    '        "macd_fast": macd_fast,\n'
    '        "macd_slow": macd_slow,\n'
    '        "macd_signal": macd_signal,\n'
    '        "impulse": [int(value) for value in impulse],\n'
    "    },\n"
    "}\n"
)
