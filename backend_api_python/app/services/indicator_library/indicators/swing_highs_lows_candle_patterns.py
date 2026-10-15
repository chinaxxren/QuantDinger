"""Chart-only source for the swing_highs_lows_candle_patterns indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Swing Highs/Lows & Candle Patterns\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Swing pivots are confirmed only after the configured right-hand bars have\n"
    "# closed. Markers are emitted on the confirmation bar, not back-filled onto the\n"
    "# historical pivot bar, so the series remains causal and non-repainting.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Swing Highs/Lows & Candle Patterns"\n'
    'my_indicator_description = "Causal swing structure and candle-pattern detector with confirmed pivot markers."\n'
    "\n"
    "# @param length int 21 Swing pivot left/right confirmation bars range=1:100:1\n"
    "\n"
    'length = max(1, min(100, int(params.get("length", 21))))\n'
    "\n"
    "df = df.copy()\n"
    'open_price = df["open"].astype(float).to_numpy()\n'
    'high = df["high"].astype(float).to_numpy()\n'
    'low = df["low"].astype(float).to_numpy()\n'
    'close = df["close"].astype(float).to_numpy()\n'
    "n = len(df)\n"
    "\n"
    "swing_high_plot = np.full(n, np.nan, dtype=float)\n"
    "swing_low_plot = np.full(n, np.nan, dtype=float)\n"
    "swing_high_marker = [None] * n\n"
    "swing_low_marker = [None] * n\n"
    "pattern_buy_marker = [None] * n\n"
    "pattern_sell_marker = [None] * n\n"
    "swing_type = [None] * n\n"
    "pattern_code = [None] * n\n"
    "pattern_name = [None] * n\n"
    "\n"
    "last_high_value = np.nan\n"
    "last_low_value = np.nan\n"
    "\n"
    "for i in range(n):\n"
    "    # The candidate at i - length has exactly `length` bars on each side at\n"
    "    # this point. Both comparisons are strict, matching the TradingView logic.\n"
    "    pivot_index = i - length\n"
    "    confirmed_high = False\n"
    "    confirmed_low = False\n"
    "    pivot_high_value = np.nan\n"
    "    pivot_low_value = np.nan\n"
    "\n"
    "    if pivot_index >= length:\n"
    "        left_high = high[pivot_index - length:pivot_index]\n"
    "        right_high = high[pivot_index + 1:i + 1]\n"
    "        left_low = low[pivot_index - length:pivot_index]\n"
    "        right_low = low[pivot_index + 1:i + 1]\n"
    "        candidate_high = high[pivot_index]\n"
    "        candidate_low = low[pivot_index]\n"
    "\n"
    "        if (\n"
    "            np.isfinite(candidate_high)\n"
    "            and len(left_high) == length\n"
    "            and len(right_high) == length\n"
    "            and np.isfinite(left_high).all()\n"
    "            and np.isfinite(right_high).all()\n"
    "            and candidate_high > np.max(left_high)\n"
    "            and candidate_high > np.max(right_high)\n"
    "        ):\n"
    "            confirmed_high = True\n"
    "            pivot_high_value = float(candidate_high)\n"
    "\n"
    "        if (\n"
    "            np.isfinite(candidate_low)\n"
    "            and len(left_low) == length\n"
    "            and len(right_low) == length\n"
    "            and np.isfinite(left_low).all()\n"
    "            and np.isfinite(right_low).all()\n"
    "            and candidate_low < np.min(left_low)\n"
    "            and candidate_low < np.min(right_low)\n"
    "        ):\n"
    "            confirmed_low = True\n"
    "            pivot_low_value = float(candidate_low)\n"
    "\n"
    "    if confirmed_high:\n"
    "        # The sparse plot carries the confirmed pivot value, while the signal\n"
    "        # marker is positioned on the actual confirmation candle.\n"
    "        swing_high_plot[i] = pivot_high_value\n"
    "        swing_high_marker[i] = float(high[i]) * 1.005 if np.isfinite(high[i]) else None\n"
    '        swing_type[i] = "HH" if not np.isfinite(last_high_value) or pivot_high_value > last_high_value else "LH"\n'
    "        last_high_value = pivot_high_value\n"
    "\n"
    "    if confirmed_low:\n"
    "        swing_low_plot[i] = pivot_low_value\n"
    "        swing_low_marker[i] = float(low[i]) * 0.995 if np.isfinite(low[i]) else None\n"
    '        swing_type[i] = "LL" if not np.isfinite(last_low_value) or pivot_low_value < last_low_value else "HL"\n'
    "        last_low_value = pivot_low_value\n"
    "\n"
    "    # Candle patterns are evaluated on the confirmation candle using only the\n"
    "    # current and immediately preceding bars.\n"
    "    if i == 0:\n"
    "        continue\n"
    "    values = (open_price[i], high[i], low[i], close[i], open_price[i - 1], close[i - 1])\n"
    "    if not all(np.isfinite(value) for value in values):\n"
    "        continue\n"
    "\n"
    "    current_open = float(open_price[i])\n"
    "    current_high = float(high[i])\n"
    "    current_low = float(low[i])\n"
    "    current_close = float(close[i])\n"
    "    previous_open = float(open_price[i - 1])\n"
    "    previous_close = float(close[i - 1])\n"
    "    body_size = abs(current_close - current_open)\n"
    "    body_min = min(current_open, current_close)\n"
    "    body_max = max(current_open, current_close)\n"
    "\n"
    "    detected_code = None\n"
    "    detected_name = None\n"
    "    bullish = False\n"
    "\n"
    "    if confirmed_low and (body_min - current_low) > body_size and (current_high - body_max) < body_size:\n"
    '        detected_code = "HAM"\n'
    '        detected_name = "Hammer"\n'
    "        bullish = True\n"
    "    elif confirmed_low and (current_high - body_max) > body_size and (body_min - current_low) < body_size:\n"
    '        detected_code = "IHM"\n'
    '        detected_name = "Inverted Hammer"\n'
    "        bullish = True\n"
    "    elif (\n"
    "        current_close > current_open\n"
    "        and previous_close < previous_open\n"
    "        and current_close > previous_open\n"
    "        and current_open < previous_close\n"
    "    ):\n"
    '        detected_code = "BUE"\n'
    '        detected_name = "Bullish Engulfing"\n'
    "        bullish = True\n"
    "    elif confirmed_high and (body_min - current_low) > body_size and (current_high - body_max) < body_size:\n"
    '        detected_code = "HGM"\n'
    '        detected_name = "Hanging Man"\n'
    "    elif confirmed_high and (current_high - body_max) > body_size and (body_min - current_low) < body_size:\n"
    '        detected_code = "SS"\n'
    '        detected_name = "Shooting Star"\n'
    "    elif (\n"
    "        current_close < current_open\n"
    "        and previous_close > previous_open\n"
    "        and current_close < previous_open\n"
    "        and current_open > previous_close\n"
    "    ):\n"
    '        detected_code = "BEE"\n'
    '        detected_name = "Bearish Engulfing"\n'
    "\n"
    "    if detected_code is not None:\n"
    "        pattern_code[i] = detected_code\n"
    "        pattern_name[i] = detected_name\n"
    "        if bullish:\n"
    "            pattern_buy_marker[i] = float(current_low) * 0.99\n"
    "        else:\n"
    "            pattern_sell_marker[i] = float(current_high) * 1.01\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    "        {\n"
    '            "name": "Swing High",\n'
    '            "data": plot_list(swing_high_plot),\n'
    '            "color": "#FF5252",\n'
    '            "overlay": True,\n'
    "        },\n"
    "        {\n"
    '            "name": "Swing Low",\n'
    '            "data": plot_list(swing_low_plot),\n'
    '            "color": "#00E676",\n'
    '            "overlay": True,\n'
    "        },\n"
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "sell", "text": "Swing High", "data": swing_high_marker, "color": "#FF5252"},\n'
    '        {"type": "buy", "text": "Swing Low", "data": swing_low_marker, "color": "#00E676"},\n'
    '        {"type": "buy", "text": "Candle Buy", "data": pattern_buy_marker, "color": "#26A69A"},\n'
    '        {"type": "sell", "text": "Candle Sell", "data": pattern_sell_marker, "color": "#EF5350"},\n'
    "    ],\n"
    '    "metadata": {\n'
    '        "swing_type": swing_type,\n'
    '        "pattern_code": pattern_code,\n'
    '        "pattern_name": pattern_name,\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
