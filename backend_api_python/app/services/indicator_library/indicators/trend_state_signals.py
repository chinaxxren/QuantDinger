"""Chart-only source for the trend_state_signals indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Trend State Signals\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal adaptive step filter based on the trailing RMA of absolute price\n"
    "# changes. Trend reversals are emitted as visual chart markers only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Trend State Signals"\n'
    'my_indicator_description = "Adaptive step filter with trend state and chart-only reversal markers."\n'
    "\n"
    "# @param length int 20 RMA volatility lookback range=2:200:1\n"
    "# @param multiplier float 3.5 Adaptive range multiplier range=0.1:10.0:0.1\n"
    "# @param src_type string close Price source: close, hl2, hlc3, or ohlc4\n"
    "\n"
    'length = max(2, int(params.get("length", 20)))\n'
    'multiplier = max(0.1, float(params.get("multiplier", 3.5)))\n'
    'src_type = str(params.get("src_type", "close")).lower()\n'
    "\n"
    "df = df.copy()\n"
    'open_price = df["open"].astype(float).to_numpy()\n'
    'high = df["high"].astype(float).to_numpy()\n'
    'low = df["low"].astype(float).to_numpy()\n'
    'close = df["close"].astype(float).to_numpy()\n'
    'if src_type == "hl2":\n'
    "    source = (high + low) / 2.0\n"
    'elif src_type == "hlc3":\n'
    "    source = (high + low + close) / 3.0\n"
    'elif src_type == "ohlc4":\n'
    "    source = (open_price + high + low + close) / 4.0\n"
    "else:\n"
    "    source = close\n"
    "\n"
    "n = len(source)\n"
    "movement = np.full(n, np.nan, dtype=float)\n"
    "if n > 1:\n"
    "    movement[1:] = np.abs(np.diff(source))\n"
    "movement_rma = np.full(n, np.nan, dtype=float)\n"
    "adaptive_range = np.full(n, np.nan, dtype=float)\n"
    "\n"
    "# Wilder RMA seeded by an SMA of the first complete window, matching Pine's\n"
    "# ta.rma warm-up rather than pandas' differently seeded ewm implementation.\n"
    "first_rma_index = length\n"
    "if n > first_rma_index:\n"
    "    seed = movement[1:first_rma_index + 1]\n"
    "    if len(seed) == length and np.isfinite(seed).all():\n"
    "        movement_rma[first_rma_index] = float(np.mean(seed))\n"
    "        adaptive_range[first_rma_index] = movement_rma[first_rma_index] * multiplier\n"
    "        for i in range(first_rma_index + 1, n):\n"
    "            if np.isfinite(movement[i]) and np.isfinite(movement_rma[i - 1]):\n"
    "                movement_rma[i] = (\n"
    "                    movement_rma[i - 1] * (length - 1) + movement[i]\n"
    "                ) / length\n"
    "                adaptive_range[i] = movement_rma[i] * multiplier\n"
    "\n"
    "filter_line = np.full(n, np.nan, dtype=float)\n"
    "trend = np.zeros(n, dtype=int)\n"
    "for i in range(first_rma_index, n):\n"
    "    if not np.isfinite(source[i]) or not np.isfinite(adaptive_range[i]):\n"
    "        if i > first_rma_index:\n"
    "            filter_line[i] = filter_line[i - 1]\n"
    "            trend[i] = trend[i - 1]\n"
    "        continue\n"
    "\n"
    "    if i == first_rma_index or not np.isfinite(filter_line[i - 1]):\n"
    "        filter_line[i] = source[i]\n"
    "        continue\n"
    "\n"
    "    previous_filter = filter_line[i - 1]\n"
    "    distance = adaptive_range[i]\n"
    "    if source[i] > previous_filter + distance:\n"
    "        filter_line[i] = source[i] - distance\n"
    "    elif source[i] < previous_filter - distance:\n"
    "        filter_line[i] = source[i] + distance\n"
    "    else:\n"
    "        filter_line[i] = previous_filter\n"
    "\n"
    "    if filter_line[i] > previous_filter:\n"
    "        trend[i] = 1\n"
    "    elif filter_line[i] < previous_filter:\n"
    "        trend[i] = -1\n"
    "    else:\n"
    "        trend[i] = trend[i - 1]\n"
    "\n"
    "previous_trend = np.concatenate(([0], trend[:-1]))\n"
    "long_signal = (trend == 1) & (previous_trend != 1) & (previous_trend != 0)\n"
    "short_signal = (trend == -1) & (previous_trend != -1) & (previous_trend != 0)\n"
    "buy_marks = [float(low[i]) * 0.995 if long_signal[i] and np.isfinite(low[i]) else None for i in range(n)]\n"
    "sell_marks = [float(high[i]) * 1.005 if short_signal[i] and np.isfinite(high[i]) else None for i in range(n)]\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Step Filter", "data": plot_list(filter_line), "color": "#26A69A", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "TSS+", "data": buy_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "TSS-", "data": sell_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
