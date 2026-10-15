"""Chart-only source for the smart_money_breakouts indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Smart Money Breakouts\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal swing-pivot liquidity breakout indicator inspired by\n"
    "# Smart Money Breakouts [ChartPrime]. It emits chart-only BOS/CHoCH\n"
    "# markers, volume-bias annotations, and optional visual TP/SL levels.\n"
    "# It never places, submits, or manages real trading orders.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Smart Money Breakouts"\n'
    "my_indicator_description = (\n"
    '    "Causal smart-money pivot breakout detector with BOS/CHoCH signals, "\n'
    '    "volume-bias labels, and optional chart-only risk levels."\n'
    ")\n"
    "\n"
    "# @param length int 20 Swing pivot left/right confirmation length range=2:100:1\n"
    "# @param candle_type string Wicks Breakout source: Wicks or Body\n"
    "# @param rr_ratio float 1.1 Reward/risk ratio range=0.1:20:0.1\n"
    "# @param sl_type string Close Stop trigger: Close or High/Low\n"
    "# @param show_sl bool False Show chart-only stop-loss line\n"
    "# @param line_style string Dashed Line style: Solid, Dashed, or Dotted\n"
    "# @param pivot_high_color string #028545 Pivot high color\n"
    "# @param pivot_low_color string #F60707 Pivot low color\n"
    "# @param tp_color string #148D9A Target color\n"
    "# @param sl_color string #F60707 Stop color\n"
    "\n"
    "\n"
    "def as_bool(value, default=False):\n"
    "    if value is None:\n"
    "        return default\n"
    "    text = str(value).strip().lower()\n"
    '    if text in ("false", "0", "no", "off"):\n'
    "        return False\n"
    '    if text in ("true", "1", "yes", "on"):\n'
    "        return True\n"
    "    return bool(value)\n"
    "\n"
    "\n"
    "def clamp_int(value, default, minimum, maximum):\n"
    "    try:\n"
    "        parsed = int(value)\n"
    "    except (TypeError, ValueError):\n"
    "        parsed = default\n"
    "    return min(maximum, max(minimum, parsed))\n"
    "\n"
    "\n"
    "def clamp_float(value, default, minimum, maximum):\n"
    "    try:\n"
    "        parsed = float(value)\n"
    "    except (TypeError, ValueError):\n"
    "        parsed = default\n"
    "    if not np.isfinite(parsed):\n"
    "        parsed = default\n"
    "    return min(maximum, max(minimum, parsed))\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    "def rma(values, period):\n"
    "    values = np.asarray(values, dtype=float)\n"
    "    result = np.full(len(values), np.nan, dtype=float)\n"
    "    if period <= 0:\n"
    "        return result\n"
    "    for index in range(period - 1, len(values)):\n"
    "        if not np.all(np.isfinite(values[index - period + 1:index + 1])):\n"
    "            continue\n"
    "        if index == period - 1:\n"
    "            result[index] = float(np.mean(values[:period]))\n"
    "        elif np.isfinite(result[index - 1]):\n"
    "            result[index] = (result[index - 1] * (period - 1) + values[index]) / period\n"
    "    return result\n"
    "\n"
    "\n"
    'length = clamp_int(params.get("length", 20), 20, 2, 100)\n'
    'candle_type = str(params.get("candle_type", "Wicks")).strip().lower()\n'
    'if candle_type not in ("wicks", "body"):\n'
    '    candle_type = "wicks"\n'
    'rr_ratio = clamp_float(params.get("rr_ratio", 1.1), 1.1, 0.1, 20.0)\n'
    'sl_type = str(params.get("sl_type", "Close")).strip().lower()\n'
    'if sl_type not in ("close", "high/low", "high_low", "highlow"):\n'
    '    sl_type = "close"\n'
    'show_sl = as_bool(params.get("show_sl", False), False)\n'
    'line_style = str(params.get("line_style", "Dashed")).strip().lower()\n'
    'if line_style not in ("solid", "dashed", "dotted"):\n'
    '    line_style = "dashed"\n'
    "\n"
    'pivot_high_color = str(params.get("pivot_high_color", "#028545"))\n'
    'pivot_low_color = str(params.get("pivot_low_color", "#F60707"))\n'
    'tp_color = str(params.get("tp_color", "#148D9A"))\n'
    'sl_color = str(params.get("sl_color", "#F60707"))\n'
    "\n"
    "df = df.copy()\n"
    'high = pd.to_numeric(df["high"], errors="coerce").to_numpy(dtype=float)\n'
    'low = pd.to_numeric(df["low"], errors="coerce").to_numpy(dtype=float)\n'
    'close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)\n'
    "open_price = (\n"
    '    pd.to_numeric(df["open"], errors="coerce").to_numpy(dtype=float)\n'
    '    if "open" in df\n'
    "    else close.copy()\n"
    ")\n"
    'if "volume" in df:\n'
    '    volume = pd.to_numeric(df["volume"], errors="coerce").to_numpy(dtype=float)\n'
    "    volume = np.where(np.isfinite(volume) & (volume >= 0.0), volume, 0.0)\n"
    "else:\n"
    "    volume = np.ones(len(df), dtype=float)\n"
    "\n"
    "n = len(close)\n"
    "pivot_high = np.full(n, np.nan, dtype=float)\n"
    "pivot_low = np.full(n, np.nan, dtype=float)\n"
    "tp = np.full(n, np.nan, dtype=float)\n"
    "sl = np.full(n, np.nan, dtype=float)\n"
    "long_signal = np.full(n, np.nan, dtype=float)\n"
    "short_signal = np.full(n, np.nan, dtype=float)\n"
    "break_type = np.full(n, np.nan, dtype=float)\n"
    "vol_sign = np.full(n, np.nan, dtype=float)\n"
    "winning = np.zeros(n, dtype=float)\n"
    "losing = np.zeros(n, dtype=float)\n"
    "trade_on = np.zeros(n, dtype=float)\n"
    "break_text = [None] * n\n"
    "volume_text = [None] * n\n"
    "\n"
    "true_range = np.full(n, np.nan, dtype=float)\n"
    "for i in range(n):\n"
    "    if not (np.isfinite(high[i]) and np.isfinite(low[i])):\n"
    "        continue\n"
    "    if i == 0 or not np.isfinite(close[i - 1]):\n"
    "        true_range[i] = high[i] - low[i]\n"
    "    else:\n"
    "        true_range[i] = max(\n"
    "            high[i] - low[i],\n"
    "            abs(high[i] - close[i - 1]),\n"
    "            abs(low[i] - close[i - 1]),\n"
    "        )\n"
    "atr = rma(true_range, 14)\n"
    "\n"
    "active_high = np.nan\n"
    "active_low = np.nan\n"
    "active_high_index = None\n"
    "active_low_index = None\n"
    "high_active = False\n"
    "low_active = False\n"
    "last_break_direction = 0\n"
    "position = 0\n"
    "position_tp = np.nan\n"
    "position_sl = np.nan\n"
    "wins = 0.0\n"
    "losses = 0.0\n"
    "\n"
    "for i in range(n):\n"
    "    # A pivot is only known after `length` right-side bars are complete. The\n"
    "    # level is projected forward from the confirmation bar, never backfilled.\n"
    "    pivot_index = i - length\n"
    "    if pivot_index >= length:\n"
    "        left_high = high[pivot_index - length:pivot_index]\n"
    "        right_high = high[pivot_index + 1:i + 1]\n"
    "        left_low = low[pivot_index - length:pivot_index]\n"
    "        right_low = low[pivot_index + 1:i + 1]\n"
    "        if (\n"
    "            np.isfinite(high[pivot_index])\n"
    "            and np.all(np.isfinite(left_high))\n"
    "            and np.all(np.isfinite(right_high))\n"
    "            and high[pivot_index] > np.max(left_high)\n"
    "            and high[pivot_index] >= np.max(right_high)\n"
    "        ):\n"
    "            active_high = float(high[pivot_index])\n"
    "            active_high_index = pivot_index\n"
    "            high_active = True\n"
    "        if (\n"
    "            np.isfinite(low[pivot_index])\n"
    "            and np.all(np.isfinite(left_low))\n"
    "            and np.all(np.isfinite(right_low))\n"
    "            and low[pivot_index] < np.min(left_low)\n"
    "            and low[pivot_index] <= np.min(right_low)\n"
    "        ):\n"
    "            active_low = float(low[pivot_index])\n"
    "            active_low_index = pivot_index\n"
    "            low_active = True\n"
    "\n"
    "    if np.isfinite(active_high):\n"
    "        pivot_high[i] = active_high\n"
    "    if np.isfinite(active_low):\n"
    "        pivot_low[i] = active_low\n"
    "\n"
    "    # Manage an already-open visual trade before considering a new entry. If\n"
    "    # both levels are touched in one candle, stop loss wins conservatively.\n"
    "    if position != 0:\n"
    "        if position > 0:\n"
    "            stop_hit = False\n"
    '            if sl_type == "close":\n'
    "                stop_hit = np.isfinite(close[i]) and close[i] <= position_sl\n"
    "            else:\n"
    "                stop_hit = np.isfinite(low[i]) and low[i] <= position_sl\n"
    "            target_hit = np.isfinite(high[i]) and high[i] >= position_tp\n"
    "            if stop_hit:\n"
    "                losses += 1.0\n"
    "                position = 0\n"
    "            elif target_hit:\n"
    "                wins += 1.0\n"
    "                position = 0\n"
    "        else:\n"
    "            stop_hit = False\n"
    '            if sl_type == "close":\n'
    "                stop_hit = np.isfinite(close[i]) and close[i] >= position_sl\n"
    "            else:\n"
    "                stop_hit = np.isfinite(high[i]) and high[i] >= position_sl\n"
    "            target_hit = np.isfinite(low[i]) and low[i] <= position_tp\n"
    "            if stop_hit:\n"
    "                losses += 1.0\n"
    "                position = 0\n"
    "            elif target_hit:\n"
    "                wins += 1.0\n"
    "                position = 0\n"
    "\n"
    '    scr_high = high[i] if candle_type == "wicks" else close[i]\n'
    '    scr_low = low[i] if candle_type == "wicks" else close[i]\n'
    "    long_break = (\n"
    "        high_active\n"
    "        and np.isfinite(active_high)\n"
    "        and np.isfinite(scr_high)\n"
    "        and scr_high > active_high\n"
    "    )\n"
    "    short_break = (\n"
    "        low_active\n"
    "        and np.isfinite(active_low)\n"
    "        and np.isfinite(scr_low)\n"
    "        and scr_low < active_low\n"
    "    )\n"
    "\n"
    "    # A single candle cannot normally break both sides. Process a malformed\n"
    "    # two-sided candle deterministically, with the bullish side first.\n"
    "    if long_break:\n"
    "        high_active = False\n"
    "        if position == 0 and np.isfinite(close[i]) and np.isfinite(low[i]) and np.isfinite(atr[i]):\n"
    "            distance = abs(close[i] - (low[i] - atr[i] * 1.5))\n"
    "            if distance > 0.0:\n"
    "                position = 1\n"
    "                position_tp = close[i] + rr_ratio * distance\n"
    "                position_sl = close[i] - distance\n"
    "                long_signal[i] = low[i]\n"
    "                break_type[i] = 1.0 if last_break_direction < 0 else 2.0\n"
    "                last_break_direction = 1\n"
    "                start = active_high_index + 1 if active_high_index is not None else i\n"
    "                start = max(0, min(i, start))\n"
    "                green_volume = float(np.sum(volume[start:i + 1][close[start:i + 1] > open_price[start:i + 1]]))\n"
    "                red_volume = float(np.sum(volume[start:i + 1][close[start:i + 1] < open_price[start:i + 1]]))\n"
    "                total_volume = green_volume + red_volume\n"
    "                if total_volume > 0.0 and green_volume / total_volume > 0.55:\n"
    "                    vol_sign[i] = 1.0\n"
    '                    volume_text[i] = "🟢"\n'
    "                elif total_volume > 0.0 and red_volume / total_volume > 0.55:\n"
    "                    vol_sign[i] = 2.0\n"
    '                    volume_text[i] = "🔴"\n'
    "                else:\n"
    "                    vol_sign[i] = 3.0\n"
    '                    volume_text[i] = "🟡"\n'
    '                break_text[i] = "CHoCH" if break_type[i] == 1.0 else "BOS"\n'
    "\n"
    "    if short_break:\n"
    "        low_active = False\n"
    "        if position == 0 and np.isfinite(close[i]) and np.isfinite(high[i]) and np.isfinite(atr[i]):\n"
    "            distance = abs(close[i] - (high[i] + atr[i] * 1.5))\n"
    "            if distance > 0.0:\n"
    "                position = -1\n"
    "                position_tp = close[i] - rr_ratio * distance\n"
    "                position_sl = close[i] + distance\n"
    "                short_signal[i] = high[i]\n"
    "                break_type[i] = 1.0 if last_break_direction > 0 else 2.0\n"
    "                last_break_direction = -1\n"
    "                start = active_low_index + 1 if active_low_index is not None else i\n"
    "                start = max(0, min(i, start))\n"
    "                green_volume = float(np.sum(volume[start:i + 1][close[start:i + 1] > open_price[start:i + 1]]))\n"
    "                red_volume = float(np.sum(volume[start:i + 1][close[start:i + 1] < open_price[start:i + 1]]))\n"
    "                total_volume = green_volume + red_volume\n"
    "                if total_volume > 0.0 and green_volume / total_volume > 0.55:\n"
    "                    vol_sign[i] = 1.0\n"
    '                    volume_text[i] = "🟢"\n'
    "                elif total_volume > 0.0 and red_volume / total_volume > 0.55:\n"
    "                    vol_sign[i] = 2.0\n"
    '                    volume_text[i] = "🔴"\n'
    "                else:\n"
    "                    vol_sign[i] = 3.0\n"
    '                    volume_text[i] = "🟡"\n'
    '                break_text[i] = "CHoCH" if break_type[i] == 1.0 else "BOS"\n'
    "\n"
    "    if position != 0 and np.isfinite(position_tp):\n"
    "        tp[i] = position_tp\n"
    "        if show_sl and np.isfinite(position_sl):\n"
    "            sl[i] = position_sl\n"
    "    trade_on[i] = 1.0 if position != 0 else 0.0\n"
    "    winning[i] = wins\n"
    "    losing[i] = losses\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    "        {\n"
    '            "name": "Pivot High",\n'
    '            "data": plot_list(pivot_high),\n'
    '            "color": pivot_high_color,\n'
    '            "overlay": True,\n'
    '            "style": line_style,\n'
    "        },\n"
    "        {\n"
    '            "name": "Pivot Low",\n'
    '            "data": plot_list(pivot_low),\n'
    '            "color": pivot_low_color,\n'
    '            "overlay": True,\n'
    '            "style": line_style,\n'
    "        },\n"
    "        {\n"
    '            "name": "Take Profit",\n'
    '            "data": plot_list(tp),\n'
    '            "color": tp_color,\n'
    '            "overlay": True,\n'
    '            "style": line_style,\n'
    "        },\n"
    "        {\n"
    '            "name": "Stop Loss",\n'
    '            "data": plot_list(sl),\n'
    '            "color": sl_color,\n'
    '            "overlay": True,\n'
    '            "style": line_style,\n'
    "        },\n"
    "    ],\n"
    '    "signals": [\n'
    "        {\n"
    '            "type": "buy",\n'
    '            "text": "BOS/CHoCH",\n'
    '            "data": plot_list(long_signal),\n'
    '            "color": "#00C853",\n'
    "        },\n"
    "        {\n"
    '            "type": "sell",\n'
    '            "text": "BOS/CHoCH",\n'
    '            "data": plot_list(short_signal),\n'
    '            "color": "#F23645",\n'
    "        },\n"
    "    ],\n"
    '    "layers": [],\n'
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "length": length,\n'
    '        "candle_type": "Wicks" if candle_type == "wicks" else "Body",\n'
    '        "rr_ratio": rr_ratio,\n'
    '        "sl_type": "High/Low" if sl_type != "close" else "Close",\n'
    '        "show_sl": show_sl,\n'
    '        "line_style": line_style,\n'
    '        "break_type": plot_list(break_type),\n'
    '        "vol_sign": plot_list(vol_sign),\n'
    '        "winning": plot_list(winning),\n'
    '        "losing": plot_list(losing),\n'
    '        "trade_on": plot_list(trade_on),\n'
    '        "break_text": break_text,\n'
    '        "volume_text": volume_text,\n'
    "    },\n"
    "}\n"
)
