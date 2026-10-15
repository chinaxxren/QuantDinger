"""Chart-only source for the smart_money_breakout_signals indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Smart Money Breakout Signals\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal structure-break detector.  Reference highs/lows are taken from bars\n"
    "# strictly before the current bar, so a breakout marker cannot repaint history.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Smart Money Breakout Signals"\n'
    'my_indicator_description = "Causal market-structure breakouts confirmed by candle body and relative volume."\n'
    "\n"
    "# @param swing_length int 5 Swing lookback range=2:100:1\n"
    "# @param volume_length int 20 Relative-volume lookback range=2:200:1\n"
    "# @param volume_multiplier float 1.0 Minimum relative-volume multiplier range=0.1:10.0:0.1\n"
    "# @param use_volume bool True Require volume confirmation\n"
    "# @param show_levels bool True Show active structure levels\n"
    "\n"
    'swing_length = max(2, int(params.get("swing_length", 5)))\n'
    'volume_length = max(2, int(params.get("volume_length", 20)))\n'
    'volume_multiplier = max(0.1, float(params.get("volume_multiplier", 1.0)))\n'
    'use_volume_value = params.get("use_volume", True)\n'
    'use_volume = not (str(use_volume_value).strip().lower() in ("false", "0", "no", "off"))\n'
    'show_levels_value = params.get("show_levels", True)\n'
    'show_levels = not (str(show_levels_value).strip().lower() in ("false", "0", "no", "off"))\n'
    "\n"
    "_df = df.copy()\n"
    'open_values = _df["open"].astype(float).to_numpy(dtype=float)\n'
    'high_values = _df["high"].astype(float).to_numpy(dtype=float)\n'
    'low_values = _df["low"].astype(float).to_numpy(dtype=float)\n'
    'close_values = _df["close"].astype(float).to_numpy(dtype=float)\n'
    'volume_values = _df["volume"].astype(float).to_numpy(dtype=float)\n'
    "n = len(_df)\n"
    "\n"
    'prior_high = _df["high"].astype(float).shift(1).rolling(\n'
    "    swing_length, min_periods=swing_length\n"
    ").max().to_numpy(dtype=float)\n"
    'prior_low = _df["low"].astype(float).shift(1).rolling(\n'
    "    swing_length, min_periods=swing_length\n"
    ").min().to_numpy(dtype=float)\n"
    'average_volume = _df["volume"].astype(float).shift(1).rolling(\n'
    "    volume_length, min_periods=volume_length\n"
    ").mean().to_numpy(dtype=float)\n"
    "\n"
    "structure_high = np.full(n, np.nan, dtype=float)\n"
    "structure_low = np.full(n, np.nan, dtype=float)\n"
    "long_signal = np.zeros(n, dtype=bool)\n"
    "short_signal = np.zeros(n, dtype=bool)\n"
    "break_direction = np.zeros(n, dtype=float)\n"
    "\n"
    "active_high = np.nan\n"
    "active_low = np.nan\n"
    "for i in range(n):\n"
    "    if np.isfinite(prior_high[i]):\n"
    "        active_high = prior_high[i]\n"
    "    if np.isfinite(prior_low[i]):\n"
    "        active_low = prior_low[i]\n"
    "\n"
    "    structure_high[i] = active_high\n"
    "    structure_low[i] = active_low\n"
    "\n"
    "    volume_ok = True\n"
    "    if use_volume:\n"
    "        volume_ok = (\n"
    "            np.isfinite(volume_values[i])\n"
    "            and np.isfinite(average_volume[i])\n"
    "            and volume_values[i] >= average_volume[i] * volume_multiplier\n"
    "        )\n"
    "    bullish_body = np.isfinite(open_values[i]) and np.isfinite(close_values[i]) and close_values[i] > open_values[i]\n"
    "    bearish_body = np.isfinite(open_values[i]) and np.isfinite(close_values[i]) and close_values[i] < open_values[i]\n"
    "\n"
    "    broke_up = (\n"
    "        bullish_body\n"
    "        and volume_ok\n"
    "        and np.isfinite(active_high)\n"
    "        and np.isfinite(close_values[i])\n"
    "        and close_values[i] > active_high\n"
    "        and (i == 0 or not np.isfinite(close_values[i - 1]) or close_values[i - 1] <= active_high)\n"
    "    )\n"
    "    broke_down = (\n"
    "        bearish_body\n"
    "        and volume_ok\n"
    "        and np.isfinite(active_low)\n"
    "        and np.isfinite(close_values[i])\n"
    "        and close_values[i] < active_low\n"
    "        and (i == 0 or not np.isfinite(close_values[i - 1]) or close_values[i - 1] >= active_low)\n"
    "    )\n"
    "    if broke_up:\n"
    "        long_signal[i] = True\n"
    "        break_direction[i] = 1.0\n"
    "    elif broke_down:\n"
    "        short_signal[i] = True\n"
    "        break_direction[i] = -1.0\n"
    "\n"
    "if not show_levels:\n"
    "    structure_high = np.full(n, np.nan, dtype=float)\n"
    "    structure_low = np.full(n, np.nan, dtype=float)\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "long_marks = [\n"
    "    float(low_values[i]) if long_signal[i] and np.isfinite(low_values[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "short_marks = [\n"
    "    float(high_values[i]) if short_signal[i] and np.isfinite(high_values[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Structure High", "data": plot_list(structure_high), "color": "#EF5350", "overlay": True},\n'
    '        {"name": "Structure Low", "data": plot_list(structure_low), "color": "#26A69A", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "Bullish BOS", "data": long_marks, "color": "#00C853"},\n'
    '        {"type": "sell", "text": "Bearish BOS", "data": short_marks, "color": "#FF1744"},\n'
    "    ],\n"
    '    "metadata": {\n'
    '        "break_direction": [int(value) for value in break_direction],\n'
    '        "use_volume": use_volume,\n'
    '        "show_levels": show_levels,\n'
    '        "causal": True,\n'
    '        "chart_only": True,\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
