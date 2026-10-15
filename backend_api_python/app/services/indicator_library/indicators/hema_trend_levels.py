"""Chart-only source for the hema_trend_levels indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] HEMA Trend Levels\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Hull-style exponential moving average with causal ATR levels.  Trend state\n"
    "# and markers are derived only from the current and prior bars.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] HEMA Trend Levels"\n'
    'my_indicator_description = "Hull-style exponential average with causal ATR trend levels and reversal markers."\n'
    "\n"
    "# @param length int 50 HEMA period range=2:200:1\n"
    "# @param atr_length int 14 ATR period range=2:200:1\n"
    "# @param atr_multiplier float 1.5 ATR level multiplier range=0.1:10.0:0.1\n"
    "# @param source str close Price source choices=close,hl2,hlc3,ohlc4\n"
    "# @param show_levels bool True Show ATR trend levels\n"
    "\n"
    'length = max(2, int(params.get("length", 50)))\n'
    'atr_length = max(2, int(params.get("atr_length", 14)))\n'
    'atr_multiplier = max(0.1, float(params.get("atr_multiplier", 1.5)))\n'
    'source_name = str(params.get("source", "close")).strip().lower()\n'
    'show_levels_value = params.get("show_levels", True)\n'
    'show_levels = not (str(show_levels_value).strip().lower() in ("false", "0", "no", "off"))\n'
    "\n"
    "_df = df.copy()\n"
    'if source_name == "hl2":\n'
    '    source = (_df["high"].astype(float) + _df["low"].astype(float)) / 2.0\n'
    'elif source_name == "hlc3":\n'
    "    source = (\n"
    '        _df["high"].astype(float) + _df["low"].astype(float) + _df["close"].astype(float)\n'
    "    ) / 3.0\n"
    'elif source_name == "ohlc4":\n'
    "    source = (\n"
    '        _df["open"].astype(float)\n'
    '        + _df["high"].astype(float)\n'
    '        + _df["low"].astype(float)\n'
    '        + _df["close"].astype(float)\n'
    "    ) / 4.0\n"
    "else:\n"
    '    source_name = "close"\n'
    '    source = _df["close"].astype(float)\n'
    "\n"
    "half_length = max(1, int(length / 2))\n"
    "sqrt_length = max(1, int(np.sqrt(length)))\n"
    "ema_half = source.ewm(span=half_length, adjust=False, min_periods=half_length).mean()\n"
    "ema_full = source.ewm(span=length, adjust=False, min_periods=length).mean()\n"
    "raw_hema = 2.0 * ema_half - ema_full\n"
    "hema = raw_hema.ewm(span=sqrt_length, adjust=False, min_periods=sqrt_length).mean()\n"
    "hema_values = hema.to_numpy(dtype=float)\n"
    "\n"
    'previous_close = _df["close"].astype(float).shift(1)\n'
    "true_range = pd.concat(\n"
    "    [\n"
    '        _df["high"].astype(float) - _df["low"].astype(float),\n'
    '        (_df["high"].astype(float) - previous_close).abs(),\n'
    '        (_df["low"].astype(float) - previous_close).abs(),\n'
    "    ],\n"
    "    axis=1,\n"
    ").max(axis=1)\n"
    "atr_values = true_range.ewm(alpha=1.0 / atr_length, adjust=False, min_periods=atr_length).mean().to_numpy(dtype=float)\n"
    "\n"
    "upper = hema_values + atr_values * atr_multiplier\n"
    "lower = hema_values - atr_values * atr_multiplier\n"
    "trend = np.zeros(len(_df), dtype=float)\n"
    "long_signal = np.zeros(len(_df), dtype=bool)\n"
    "short_signal = np.zeros(len(_df), dtype=bool)\n"
    "for i in range(len(_df)):\n"
    "    if not np.isfinite(hema_values[i]):\n"
    "        if i > 0:\n"
    "            trend[i] = trend[i - 1]\n"
    "        continue\n"
    "    if i > 0 and np.isfinite(hema_values[i - 1]):\n"
    "        if hema_values[i] > hema_values[i - 1]:\n"
    "            trend[i] = 1.0\n"
    "        elif hema_values[i] < hema_values[i - 1]:\n"
    "            trend[i] = -1.0\n"
    "        else:\n"
    "            trend[i] = trend[i - 1]\n"
    "    if i > 0 and trend[i] != 0.0 and trend[i] != trend[i - 1]:\n"
    "        long_signal[i] = trend[i] > 0.0\n"
    "        short_signal[i] = trend[i] < 0.0\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "if not show_levels:\n"
    "    upper = np.full(len(_df), np.nan, dtype=float)\n"
    "    lower = np.full(len(_df), np.nan, dtype=float)\n"
    "\n"
    'low_values = _df["low"].astype(float).to_numpy(dtype=float)\n'
    'high_values = _df["high"].astype(float).to_numpy(dtype=float)\n'
    "long_marks = [\n"
    "    float(low_values[i]) if long_signal[i] and np.isfinite(low_values[i]) else None\n"
    "    for i in range(len(_df))\n"
    "]\n"
    "short_marks = [\n"
    "    float(high_values[i]) if short_signal[i] and np.isfinite(high_values[i]) else None\n"
    "    for i in range(len(_df))\n"
    "]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "HEMA", "data": plot_list(hema_values), "color": "#2962FF", "overlay": True},\n'
    '        {"name": "HEMA Upper", "data": plot_list(upper), "color": "#26A69A", "overlay": True},\n'
    '        {"name": "HEMA Lower", "data": plot_list(lower), "color": "#EF5350", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "HEMA Up", "data": long_marks, "color": "#00C853"},\n'
    '        {"type": "sell", "text": "HEMA Down", "data": short_marks, "color": "#FF1744"},\n'
    "    ],\n"
    '    "metadata": {\n'
    '        "source": source_name,\n'
    '        "trend": [int(value) for value in trend],\n'
    '        "atr": plot_list(atr_values),\n'
    '        "show_levels": show_levels,\n'
    '        "causal": True,\n'
    '        "chart_only": True,\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
