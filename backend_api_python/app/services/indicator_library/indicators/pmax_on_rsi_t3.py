"""Chart-only source for the pmax_on_rsi_t3 indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] PMax on RSI w T3\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Custom RSI, Tillson T3 support, and ATR PMax trailing levels in a\n"
    "# separate pane. Signals are visual markers only; this source never trades.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] PMax on RSI w T3"\n'
    "my_indicator_description = (\n"
    '    "Custom RSI smoothed by Tillson T3 with ATR-based PMax trailing levels "\n'
    '    "and chart-only crossover signals."\n'
    ")\n"
    "\n"
    "# @param source str hl2 Price source: hl2, hlc3, close, open, high, or low\n"
    "# @param multiplier float 1.0 ATR multiplier for the PMax trailing levels range=0.1:10:0.1\n"
    "# @param t3_length int 8 Tillson T3 smoothing length range=2:100:1\n"
    "# @param t3_factor float 0.7 Tillson T3 volume factor range=0:1:0.05\n"
    "# @param atr_length int 10 RSI ATR smoothing length range=2:100:1\n"
    "# @param rsi_length int 14 Custom RSI length range=2:100:1\n"
    "# @param show_rsi bool True Show the RSI line\n"
    "# @param show_support bool True Show the T3 support line\n"
    "# @param show_signals bool True Show chart-only Buy/Sell markers\n"
    "# @param highlighting bool True Show bull/bear highlight boundaries\n"
    "\n"
    'source_name = str(params.get("source", "hl2")).lower()\n'
    'multiplier = max(0.1, float(params.get("multiplier", 1.0)))\n'
    't3_length = max(2, int(params.get("t3_length", 8)))\n'
    't3_factor = min(1.0, max(0.0, float(params.get("t3_factor", 0.7))))\n'
    'atr_length = max(2, int(params.get("atr_length", 10)))\n'
    'rsi_length = max(2, int(params.get("rsi_length", 14)))\n'
    'show_rsi = bool(params.get("show_rsi", True))\n'
    'show_support = bool(params.get("show_support", True))\n'
    'show_signals = bool(params.get("show_signals", True))\n'
    'highlighting = bool(params.get("highlighting", True))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'open_price = df["open"].astype(float) if "open" in df else close\n'
    "\n"
    "source_map = {\n"
    '    "hl2": (high + low) / 2.0,\n'
    '    "hlc3": (high + low + close) / 3.0,\n'
    '    "close": close,\n'
    '    "open": open_price,\n'
    '    "high": high,\n'
    '    "low": low,\n'
    "}\n"
    'price_source = source_map.get(source_name, source_map["hl2"])\n'
    "\n"
    "# Wilder's moving average (WWMA/RMA) with a causal first-value seed.\n"
    "def wwma(values, length):\n"
    "    return values.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()\n"
    "\n"
    "# The original indicator blends WWMA and SMA for its custom RSI. The high/low\n"
    "# ranges are also fed into the RSI envelope used to calculate the RSI ATR.\n"
    "change = price_source.diff()\n"
    "up = change.clip(lower=0.0)\n"
    "down = (-change).clip(lower=0.0)\n"
    "up_wilder = wwma(up, rsi_length)\n"
    "down_wilder = wwma(down, rsi_length)\n"
    "up_sma = up.rolling(rsi_length, min_periods=rsi_length).mean()\n"
    "down_sma = down.rolling(rsi_length, min_periods=rsi_length).mean()\n"
    "\n"
    "average_up = (up_wilder + up_sma) / 2.0\n"
    "average_down = (down_wilder + down_sma) / 2.0\n"
    "relative_strength = average_up / average_down.replace(0.0, np.nan)\n"
    "rsi = (100.0 - 100.0 / (1.0 + relative_strength)).clip(0.0, 100.0)\n"
    "rsi = rsi.where(average_down > 0.0, 100.0)\n"
    "rsi = rsi.where(~((average_up == 0.0) & (average_down == 0.0)), 50.0)\n"
    "\n"
    "# Build causal RSI high/low envelopes from the current bar's range versus the\n"
    "# previous close. They make the PMax ATR react to an expanding RSI range.\n"
    "previous_close = close.shift(1)\n"
    "high_move = (high - previous_close).clip(lower=0.0)\n"
    "low_move = (previous_close - low).clip(lower=0.0)\n"
    "range_scale = (high - low).abs() / price_source.abs().replace(0.0, np.nan) * 100.0\n"
    "range_scale = range_scale.replace([np.inf, -np.inf], np.nan)\n"
    "range_scale = range_scale.fillna(0.0)\n"
    "\n"
    "high_adjustment = wwma(high_move, rsi_length) / price_source.abs().replace(0.0, np.nan) * 100.0\n"
    "low_adjustment = wwma(low_move, rsi_length) / price_source.abs().replace(0.0, np.nan) * 100.0\n"
    "high_adjustment = high_adjustment.replace([np.inf, -np.inf], np.nan).fillna(0.0)\n"
    "low_adjustment = low_adjustment.replace([np.inf, -np.inf], np.nan).fillna(0.0)\n"
    "rsih = (rsi + high_adjustment + range_scale / 2.0).clip(0.0, 100.0)\n"
    "rsil = (rsi - low_adjustment - range_scale / 2.0).clip(0.0, 100.0)\n"
    "\n"
    "rsi_values = rsi.to_numpy(dtype=float)\n"
    "rsih_values = rsih.to_numpy(dtype=float)\n"
    "rsil_values = rsil.to_numpy(dtype=float)\n"
    "n = len(df)\n"
    "\n"
    "# RSI-based true range and simple moving-average ATR.\n"
    "rsi_previous = np.concatenate([[np.nan], rsi_values[:-1]])\n"
    "rsi_tr = np.maximum(\n"
    "    rsih_values - rsil_values,\n"
    "    np.maximum(np.abs(rsih_values - rsi_previous), np.abs(rsil_values - rsi_previous)),\n"
    ")\n"
    "rsi_tr_series = pd.Series(rsi_tr, index=df.index)\n"
    "atr = rsi_tr_series.rolling(atr_length, min_periods=atr_length).mean()\n"
    "\n"
    "# Tillson T3: six causal EMA passes and the standard volume-factor weights.\n"
    "e1 = rsi.ewm(span=t3_length, adjust=False, min_periods=t3_length).mean()\n"
    "e2 = e1.ewm(span=t3_length, adjust=False, min_periods=t3_length).mean()\n"
    "e3 = e2.ewm(span=t3_length, adjust=False, min_periods=t3_length).mean()\n"
    "e4 = e3.ewm(span=t3_length, adjust=False, min_periods=t3_length).mean()\n"
    "e5 = e4.ewm(span=t3_length, adjust=False, min_periods=t3_length).mean()\n"
    "e6 = e5.ewm(span=t3_length, adjust=False, min_periods=t3_length).mean()\n"
    "a = t3_factor\n"
    "c1 = -(a ** 3)\n"
    "c2 = 3.0 * (a ** 2) + 3.0 * (a ** 3)\n"
    "c3 = -6.0 * (a ** 2) - 3.0 * a - 3.0 * (a ** 3)\n"
    "c4 = 1.0 + 3.0 * a + (a ** 3) + 3.0 * (a ** 2)\n"
    "t3 = c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3\n"
    "\n"
    "atr_values = atr.to_numpy(dtype=float)\n"
    "t3_values = t3.to_numpy(dtype=float)\n"
    "long_basic = t3_values - multiplier * atr_values\n"
    "short_basic = t3_values + multiplier * atr_values\n"
    "long_stop = np.full(n, np.nan, dtype=float)\n"
    "short_stop = np.full(n, np.nan, dtype=float)\n"
    "pmax = np.full(n, np.nan, dtype=float)\n"
    "direction = np.zeros(n, dtype=np.int8)\n"
    "\n"
    "# PMax uses one-sided ratchets and flips only when T3 crosses the prior stop.\n"
    "for i in range(n):\n"
    "    if not np.isfinite(t3_values[i]) or not np.isfinite(long_basic[i]) or not np.isfinite(short_basic[i]):\n"
    "        if i > 0:\n"
    "            direction[i] = direction[i - 1]\n"
    "        continue\n"
    "\n"
    "    if i == 0 or direction[i - 1] == 0 or not np.isfinite(pmax[i - 1]):\n"
    "        long_stop[i] = long_basic[i]\n"
    "        short_stop[i] = short_basic[i]\n"
    "        direction[i] = 1\n"
    "        pmax[i] = long_stop[i]\n"
    "        continue\n"
    "\n"
    "    previous_long = long_stop[i - 1]\n"
    "    previous_short = short_stop[i - 1]\n"
    "    previous_t3 = t3_values[i - 1]\n"
    "    if np.isfinite(previous_long) and previous_t3 > previous_long:\n"
    "        long_stop[i] = max(long_basic[i], previous_long)\n"
    "    else:\n"
    "        long_stop[i] = long_basic[i]\n"
    "    if np.isfinite(previous_short) and previous_t3 < previous_short:\n"
    "        short_stop[i] = min(short_basic[i], previous_short)\n"
    "    else:\n"
    "        short_stop[i] = short_basic[i]\n"
    "\n"
    "    previous_direction = direction[i - 1]\n"
    "    if previous_direction == -1 and t3_values[i] > previous_short:\n"
    "        direction[i] = 1\n"
    "    elif previous_direction == 1 and t3_values[i] < previous_long:\n"
    "        direction[i] = -1\n"
    "    else:\n"
    "        direction[i] = previous_direction\n"
    "    pmax[i] = long_stop[i] if direction[i] == 1 else short_stop[i]\n"
    "\n"
    "previous_t3 = np.concatenate([[np.nan], t3_values[:-1]])\n"
    "previous_pmax = np.concatenate([[np.nan], pmax[:-1]])\n"
    "long_signal = (\n"
    "    np.isfinite(t3_values)\n"
    "    & np.isfinite(pmax)\n"
    "    & np.isfinite(previous_t3)\n"
    "    & np.isfinite(previous_pmax)\n"
    "    & (t3_values > pmax)\n"
    "    & (previous_t3 <= previous_pmax)\n"
    ")\n"
    "short_signal = (\n"
    "    np.isfinite(t3_values)\n"
    "    & np.isfinite(pmax)\n"
    "    & np.isfinite(previous_t3)\n"
    "    & np.isfinite(previous_pmax)\n"
    "    & (t3_values < pmax)\n"
    "    & (previous_t3 >= previous_pmax)\n"
    ")\n"
    "\n"
    "# Use the direction selected by PMax for the optional bull/bear boundaries.\n"
    "rsi_up = np.where((direction > 0) & np.isfinite(rsi_values), rsi_values, np.nan)\n"
    "pmax_up = np.where((direction > 0) & np.isfinite(pmax), pmax, np.nan)\n"
    "rsi_dn = np.where((direction < 0) & np.isfinite(rsi_values), rsi_values, np.nan)\n"
    "pmax_dn = np.where((direction < 0) & np.isfinite(pmax), pmax, np.nan)\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    "none_values = [None] * n\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    "        {\n"
    '            "name": "RSI",\n'
    '            "data": plot_list(rsi_values) if show_rsi else none_values,\n'
    '            "color": "#8E1599",\n'
    '            "overlay": False,\n'
    "        },\n"
    "        {\n"
    '            "name": "T3 Support",\n'
    '            "data": plot_list(t3_values) if show_support else none_values,\n'
    '            "color": "#111111",\n'
    '            "overlay": False,\n'
    '            "width": 2,\n'
    "        },\n"
    "        {\n"
    '            "name": "PMax",\n'
    '            "data": plot_list(pmax),\n'
    '            "color": "#E53935",\n'
    '            "overlay": False,\n'
    '            "width": 2,\n'
    "        },\n"
    '        {"name": "RSI Upper", "data": [70.0] * n, "color": "#9E9E9E", "overlay": False},\n'
    '        {"name": "RSI Lower", "data": [30.0] * n, "color": "#9E9E9E", "overlay": False},\n'
    "        {\n"
    '            "name": "Bull RSI Highlight",\n'
    '            "data": plot_list(rsi_up) if highlighting else none_values,\n'
    '            "color": "#26A69A",\n'
    '            "overlay": False,\n'
    "        },\n"
    "        {\n"
    '            "name": "Bull PMax Highlight",\n'
    '            "data": plot_list(pmax_up) if highlighting else none_values,\n'
    '            "color": "#26A69A",\n'
    '            "overlay": False,\n'
    "        },\n"
    "        {\n"
    '            "name": "Bear RSI Highlight",\n'
    '            "data": plot_list(rsi_dn) if highlighting else none_values,\n'
    '            "color": "#EF5350",\n'
    '            "overlay": False,\n'
    "        },\n"
    "        {\n"
    '            "name": "Bear PMax Highlight",\n'
    '            "data": plot_list(pmax_dn) if highlighting else none_values,\n'
    '            "color": "#EF5350",\n'
    '            "overlay": False,\n'
    "        },\n"
    "    ],\n"
    '    "signals": [\n'
    "        {\n"
    '            "type": "buy",\n'
    '            "text": "Buy",\n'
    '            "data": [\n'
    "                float(pmax[i] * 0.995) if show_signals and long_signal[i] and np.isfinite(pmax[i]) else None\n"
    "                for i in range(n)\n"
    "            ],\n"
    '            "color": "#00C853",\n'
    "        },\n"
    "        {\n"
    '            "type": "sell",\n'
    '            "text": "Sell",\n'
    '            "data": [\n'
    "                float(pmax[i] * 1.005) if show_signals and short_signal[i] and np.isfinite(pmax[i]) else None\n"
    "                for i in range(n)\n"
    "            ],\n"
    '            "color": "#D50000",\n'
    "        },\n"
    "    ],\n"
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "source": source_name if source_name in source_map else "hl2",\n'
    '        "direction": [int(value) if value else None for value in direction],\n'
    '        "long_signal": [bool(value) for value in long_signal],\n'
    '        "short_signal": [bool(value) for value in short_signal],\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
