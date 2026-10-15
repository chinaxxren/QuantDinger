"""Chart-only source for the range_filter_buy_sell indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Range Filter Buy and Sell\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Guikroth's Range Filter Buy and Sell variant. This indicator produces\n"
    "# causal overlay lines and chart markers only; it does not execute trades.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Range Filter Buy and Sell"\n'
    "my_indicator_description = (\n"
    '    "Configurable-source range filter with directional bands and chart-only Buy/Sell signals."\n'
    ")\n"
    "\n"
    "# @param per int 100 Sampling period for the smoothed range range=2:200:1\n"
    "# @param mult float 3.0 Range multiplier range=0.1:10.0:0.1\n"
    "# @param source string close Source price: close, open, high, low, hl2, or hlc3\n"
    "\n"
    'per = max(2, int(params.get("per", 100)))\n'
    'mult = max(0.1, float(params.get("mult", 3.0)))\n'
    'source_name = str(params.get("source", "close")).strip().lower()\n'
    "\n"
    "_df = df.copy()\n"
    'if source_name == "open":\n'
    '    source_series = _df["open"].astype(float)\n'
    'elif source_name == "high":\n'
    '    source_series = _df["high"].astype(float)\n'
    'elif source_name == "low":\n'
    '    source_series = _df["low"].astype(float)\n'
    'elif source_name == "hl2":\n'
    '    source_series = ((_df["high"].astype(float) + _df["low"].astype(float)) / 2.0)\n'
    'elif source_name == "hlc3":\n'
    "    source_series = (\n"
    '        _df["high"].astype(float)\n'
    '        + _df["low"].astype(float)\n'
    '        + _df["close"].astype(float)\n'
    "    ) / 3.0\n"
    "else:\n"
    '    source_name = "close"\n'
    '    source_series = _df["close"].astype(float)\n'
    "\n"
    'high = _df["high"].astype(float).to_numpy()\n'
    'low = _df["low"].astype(float).to_numpy()\n'
    "source = source_series.to_numpy()\n"
    "n = len(_df)\n"
    "\n"
    "# The source indicator smooths absolute price changes twice before applying\n"
    "# the range multiplier. adjust=False preserves the recursive EMA behavior.\n"
    "source_delta = source_series.diff().abs().fillna(0.0)\n"
    "avrng = source_delta.ewm(span=per, adjust=False).mean()\n"
    "wper = max(1, per * 2 - 1)\n"
    "smrng = avrng.ewm(span=wper, adjust=False).mean() * mult\n"
    "range_values = smrng.to_numpy()\n"
    "\n"
    "filt = np.full(n, np.nan, dtype=float)\n"
    "upward = np.zeros(n, dtype=float)\n"
    "downward = np.zeros(n, dtype=float)\n"
    "if n > 0 and np.isfinite(source[0]):\n"
    "    filt[0] = source[0]\n"
    "\n"
    "# Range Filter ratchets only when price crosses the current channel edge.\n"
    "for i in range(1, n):\n"
    "    value = source[i]\n"
    "    previous = filt[i - 1]\n"
    "    width = range_values[i]\n"
    "    if not np.isfinite(value) or not np.isfinite(previous) or not np.isfinite(width):\n"
    "        continue\n"
    "\n"
    "    if value - width > previous:\n"
    "        filt[i] = value - width\n"
    "    elif value + width < previous:\n"
    "        filt[i] = value + width\n"
    "    else:\n"
    "        filt[i] = previous\n"
    "\n"
    "    if filt[i] > previous:\n"
    "        upward[i] = upward[i - 1] + 1.0\n"
    "        downward[i] = 0.0\n"
    "    elif filt[i] < previous:\n"
    "        downward[i] = downward[i - 1] + 1.0\n"
    "        upward[i] = 0.0\n"
    "    else:\n"
    "        upward[i] = upward[i - 1]\n"
    "        downward[i] = downward[i - 1]\n"
    "\n"
    "previous_source = np.concatenate([[np.nan], source[:-1]])\n"
    "source_moved = np.isfinite(source) & np.isfinite(previous_source) & (source != previous_source)\n"
    "long_condition = (\n"
    "    np.isfinite(source)\n"
    "    & np.isfinite(filt)\n"
    "    & (source > filt)\n"
    "    & (upward > 0)\n"
    "    & source_moved\n"
    ")\n"
    "short_condition = (\n"
    "    np.isfinite(source)\n"
    "    & np.isfinite(filt)\n"
    "    & (source < filt)\n"
    "    & (downward > 0)\n"
    "    & source_moved\n"
    ")\n"
    "\n"
    "# CondIni suppresses repeated markers while a condition remains active.\n"
    "condition_state = np.zeros(n, dtype=np.int8)\n"
    "long_signal = np.zeros(n, dtype=bool)\n"
    "short_signal = np.zeros(n, dtype=bool)\n"
    "state = 0\n"
    "for i in range(n):\n"
    "    if long_condition[i]:\n"
    "        long_signal[i] = state == -1\n"
    "        state = 1\n"
    "    elif short_condition[i]:\n"
    "        short_signal[i] = state == 1\n"
    "        state = -1\n"
    "    condition_state[i] = state\n"
    "\n"
    "hband = filt + range_values\n"
    "lband = filt - range_values\n"
    "\n"
    "# Direction-colored filter segments use the source colors from the indicator.\n"
    "# Include the transition point in both segments so lines remain connected.\n"
    "filt_up = np.where(upward > 0, filt, np.nan)\n"
    "filt_down = np.where(downward > 0, filt, np.nan)\n"
    "for i in range(1, n):\n"
    "    if upward[i] > 0 and downward[i - 1] > 0:\n"
    "        filt_up[i - 1] = filt[i - 1]\n"
    "        filt_up[i] = filt[i]\n"
    "    elif downward[i] > 0 and upward[i - 1] > 0:\n"
    "        filt_down[i - 1] = filt[i - 1]\n"
    "        filt_down[i] = filt[i]\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "long_marks = [\n"
    "    float(low[i]) if long_signal[i] and np.isfinite(low[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "short_marks = [\n"
    "    float(high[i]) if short_signal[i] and np.isfinite(high[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Filter", "data": plot_list(filt), "color": "#AAAAAA", "overlay": True},\n'
    '        {"name": "Filter Up", "data": plot_list(filt_up), "color": "#CF1E1E", "overlay": True},\n'
    '        {"name": "Filter Down", "data": plot_list(filt_down), "color": "#0000FF", "overlay": True},\n'
    '        {"name": "Upper Band", "data": plot_list(hband), "color": "#4DDF48", "overlay": True},\n'
    '        {"name": "Lower Band", "data": plot_list(lband), "color": "#0000FF", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "Buy", "data": long_marks, "color": "#AAAAAA"},\n'
    '        {"type": "sell", "text": "Sell", "data": short_marks, "color": "#0000FF"},\n'
    "    ],\n"
    '    "metadata": {\n'
    '        "source": source_name,\n'
    '        "upward": [float(value) if value else None for value in upward],\n'
    '        "downward": [float(value) if value else None for value in downward],\n'
    '        "condition_state": [int(value) if value else None for value in condition_state],\n'
    '        "causal": True,\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
