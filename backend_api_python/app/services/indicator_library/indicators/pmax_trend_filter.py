"""Chart-only source for the pmax_trend_filter indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] PMax Trend Filter\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# EMA baseline with ATR trailing stop bands. Signals are visual markers only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] PMax Trend Filter"\n'
    'my_indicator_description = "EMA baseline plus ATR trailing stop bands for PMax-style trend filtering."\n'
    "\n"
    "# @param ma_period int 10 EMA baseline period range=5:60:1\n"
    "# @param atr_period int 10 ATR period range=5:60:1\n"
    "# @param atr_multiplier float 3.0 ATR multiplier range=1.0:6.0:0.25\n"
    "\n"
    'ma_period = int(params.get("ma_period", 10))\n'
    'atr_period = int(params.get("atr_period", 10))\n'
    'atr_multiplier = float(params.get("atr_multiplier", 3.0))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "n = len(df)\n"
    "\n"
    "ma = close.ewm(span=ma_period, adjust=False).mean()\n"
    "prev_close = close.shift(1)\n"
    "tr = pd.concat([\n"
    "    high - low,\n"
    "    (high - prev_close).abs(),\n"
    "    (low - prev_close).abs(),\n"
    "], axis=1).max(axis=1)\n"
    "atr = tr.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()\n"
    "\n"
    "long_stop_basic = ma - atr_multiplier * atr\n"
    "short_stop_basic = ma + atr_multiplier * atr\n"
    "ma_values = ma.to_numpy()\n"
    "long_basic = long_stop_basic.to_numpy()\n"
    "short_basic = short_stop_basic.to_numpy()\n"
    "\n"
    "long_stop = np.full(n, np.nan)\n"
    "short_stop = np.full(n, np.nan)\n"
    "pmax = np.full(n, np.nan)\n"
    "direction = np.zeros(n, dtype=np.int8)\n"
    "\n"
    "for i in range(n):\n"
    "    if np.isnan(long_basic[i]) or np.isnan(short_basic[i]):\n"
    "        continue\n"
    "\n"
    "    if i == 0 or direction[i - 1] == 0 or np.isnan(long_stop[i - 1]) or np.isnan(short_stop[i - 1]):\n"
    "        long_stop[i] = long_basic[i]\n"
    "        short_stop[i] = short_basic[i]\n"
    "        direction[i] = 1 if close.iloc[i] >= ma_values[i] else -1\n"
    "        pmax[i] = long_stop[i] if direction[i] == 1 else short_stop[i]\n"
    "        continue\n"
    "\n"
    "    previous_ma = ma_values[i - 1]\n"
    "    long_stop[i] = max(long_basic[i], long_stop[i - 1]) if previous_ma > long_stop[i - 1] else long_basic[i]\n"
    "    short_stop[i] = min(short_basic[i], short_stop[i - 1]) if previous_ma < short_stop[i - 1] else short_basic[i]\n"
    "\n"
    "    if direction[i - 1] == -1 and ma_values[i] > short_stop[i - 1]:\n"
    "        direction[i] = 1\n"
    "    elif direction[i - 1] == 1 and ma_values[i] < long_stop[i - 1]:\n"
    "        direction[i] = -1\n"
    "    else:\n"
    "        direction[i] = direction[i - 1]\n"
    "\n"
    "    pmax[i] = long_stop[i] if direction[i] == 1 else short_stop[i]\n"
    "\n"
    "prev_direction = np.concatenate([[0], direction[:-1]])\n"
    "long_edge = (direction == 1) & (prev_direction == -1)\n"
    "short_edge = (direction == -1) & (prev_direction == 1)\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(v) else float(v) for v in values]\n"
    "\n"
    "pmax_up = [float(v) if (d == 1 and not pd.isna(v)) else None for v, d in zip(pmax, direction)]\n"
    "pmax_down = [float(v) if (d == -1 and not pd.isna(v)) else None for v, d in zip(pmax, direction)]\n"
    "long_marks = [float(low.iloc[i]) * 0.995 if bool(long_edge[i]) else None for i in range(n)]\n"
    "short_marks = [float(high.iloc[i]) * 1.005 if bool(short_edge[i]) else None for i in range(n)]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "EMA Baseline", "data": plot_list(ma), "color": "#FFB300", "overlay": True},\n'
    '        {"name": "PMax Up", "data": pmax_up, "color": "#00E676", "overlay": True},\n'
    '        {"name": "PMax Down", "data": pmax_down, "color": "#FF5252", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "PX+", "data": long_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "PX-", "data": short_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
