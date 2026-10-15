"""Chart-only source for the alphatrend_screener indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] AlphaTrend - Screener\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal AlphaTrend approximation using ATR plus RSI/MFI momentum gating.\n"
    "# The screener concept is represented by chart trend state and markers because\n"
    "# the frontend indicator protocol renders chart series rather than tables.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] AlphaTrend - Screener"\n'
    'my_indicator_description = "ATR and momentum gated AlphaTrend line with causal crossover markers."\n'
    "\n"
    "# @param coeff float 1.0 ATR coefficient range=0.1:10.0:0.1\n"
    "# @param period int 14 ATR and momentum period range=2:200:1\n"
    "# @param use_mfi bool True Use MFI when volume is available\n"
    "# @param show_signal bool True Show delayed signal line\n"
    "\n"
    'coeff = max(0.1, float(params.get("coeff", 1.0)))\n'
    'period = max(2, int(params.get("period", 14)))\n'
    'use_mfi_value = params.get("use_mfi", True)\n'
    'use_mfi = not (str(use_mfi_value).strip().lower() in ("false", "0", "no", "off"))\n'
    'show_signal_value = params.get("show_signal", True)\n'
    'show_signal = not (str(show_signal_value).strip().lower() in ("false", "0", "no", "off"))\n'
    "\n"
    "_df = df.copy()\n"
    'high = _df["high"].astype(float)\n'
    'low = _df["low"].astype(float)\n'
    'close = _df["close"].astype(float)\n'
    'volume = _df["volume"].astype(float)\n'
    "close_values = close.to_numpy(dtype=float)\n"
    "high_values = high.to_numpy(dtype=float)\n"
    "low_values = low.to_numpy(dtype=float)\n"
    "volume_values = volume.to_numpy(dtype=float)\n"
    "n = len(_df)\n"
    "\n"
    "previous_close = close.shift(1)\n"
    "true_range = pd.concat(\n"
    "    [\n"
    "        high - low,\n"
    "        (high - previous_close).abs(),\n"
    "        (low - previous_close).abs(),\n"
    "    ],\n"
    "    axis=1,\n"
    ").max(axis=1)\n"
    "atr = true_range.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean().to_numpy(dtype=float)\n"
    "\n"
    "change = close.diff()\n"
    "gain = change.clip(lower=0.0).rolling(period, min_periods=period).mean().to_numpy(dtype=float)\n"
    "loss = (-change.clip(upper=0.0)).rolling(period, min_periods=period).mean().to_numpy(dtype=float)\n"
    "rsi = np.full(n, np.nan, dtype=float)\n"
    "valid_rsi = np.isfinite(gain) & np.isfinite(loss)\n"
    "rsi[valid_rsi & (loss <= 0.0) & (gain > 0.0)] = 100.0\n"
    "rsi[valid_rsi & (loss <= 0.0) & (gain <= 0.0)] = 50.0\n"
    "normal_rsi = valid_rsi & (loss > 0.0)\n"
    "rsi[normal_rsi] = 100.0 - 100.0 / (1.0 + gain[normal_rsi] / loss[normal_rsi])\n"
    "\n"
    "typical_price = (high + low + close) / 3.0\n"
    "money_flow = typical_price * volume\n"
    "price_delta = typical_price.diff().to_numpy(dtype=float)\n"
    "money_flow_values = money_flow.to_numpy(dtype=float)\n"
    "positive_flow = np.where(price_delta > 0.0, money_flow_values, 0.0)\n"
    "negative_flow = np.where(price_delta < 0.0, money_flow_values, 0.0)\n"
    "positive_sum = pd.Series(positive_flow, index=_df.index).rolling(period, min_periods=period).sum().to_numpy(dtype=float)\n"
    "negative_sum = pd.Series(negative_flow, index=_df.index).rolling(period, min_periods=period).sum().to_numpy(dtype=float)\n"
    "mfi = np.full(n, np.nan, dtype=float)\n"
    "valid_mfi = np.isfinite(positive_sum) & np.isfinite(negative_sum)\n"
    "mfi[valid_mfi & (negative_sum <= 0.0) & (positive_sum > 0.0)] = 100.0\n"
    "mfi[valid_mfi & (negative_sum <= 0.0) & (positive_sum <= 0.0)] = 50.0\n"
    "normal_mfi = valid_mfi & (negative_sum > 0.0)\n"
    "mfi[normal_mfi] = 100.0 - 100.0 / (1.0 + positive_sum[normal_mfi] / negative_sum[normal_mfi])\n"
    "\n"
    "momentum = mfi if use_mfi and np.isfinite(volume_values).any() and np.nanmax(np.abs(volume_values)) > 0.0 else rsi\n"
    "up_level = low_values - coeff * atr\n"
    "down_level = high_values + coeff * atr\n"
    "alpha = np.full(n, np.nan, dtype=float)\n"
    "trend = np.zeros(n, dtype=float)\n"
    "for i in range(n):\n"
    "    if not np.isfinite(close_values[i]):\n"
    "        continue\n"
    "    if i == 0 or not np.isfinite(alpha[i - 1]):\n"
    "        alpha[i] = close_values[i]\n"
    "    else:\n"
    "        momentum_value = momentum[i]\n"
    "        if np.isfinite(momentum_value) and momentum_value >= 50.0:\n"
    "            candidate = up_level[i]\n"
    "            alpha[i] = max(alpha[i - 1], candidate) if np.isfinite(candidate) else alpha[i - 1]\n"
    "        elif np.isfinite(momentum_value):\n"
    "            candidate = down_level[i]\n"
    "            alpha[i] = min(alpha[i - 1], candidate) if np.isfinite(candidate) else alpha[i - 1]\n"
    "        else:\n"
    "            alpha[i] = alpha[i - 1]\n"
    "\n"
    "    if i > 0 and np.isfinite(alpha[i - 1]):\n"
    "        if alpha[i] > alpha[i - 1]:\n"
    "            trend[i] = 1.0\n"
    "        elif alpha[i] < alpha[i - 1]:\n"
    "            trend[i] = -1.0\n"
    "        else:\n"
    "            trend[i] = trend[i - 1]\n"
    "\n"
    "signal = np.full(n, np.nan, dtype=float)\n"
    "if n > 2:\n"
    "    signal[2:] = alpha[:-2]\n"
    "if not show_signal:\n"
    "    signal = np.full(n, np.nan, dtype=float)\n"
    "\n"
    "long_signal = np.zeros(n, dtype=bool)\n"
    "short_signal = np.zeros(n, dtype=bool)\n"
    "for i in range(1, n):\n"
    "    if np.isfinite(alpha[i]) and np.isfinite(signal[i]) and np.isfinite(alpha[i - 1]) and np.isfinite(signal[i - 1]):\n"
    "        long_signal[i] = alpha[i] > signal[i] and alpha[i - 1] <= signal[i - 1]\n"
    "        short_signal[i] = alpha[i] < signal[i] and alpha[i - 1] >= signal[i - 1]\n"
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
    '        {"name": "AlphaTrend", "data": plot_list(alpha), "color": "#00BFA5", "overlay": True},\n'
    '        {"name": "AlphaTrend Signal", "data": plot_list(signal), "color": "#FFAB00", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "AlphaTrend Up", "data": long_marks, "color": "#00C853"},\n'
    '        {"type": "sell", "text": "AlphaTrend Down", "data": short_marks, "color": "#FF1744"},\n'
    "    ],\n"
    '    "metadata": {\n'
    '        "trend": [int(value) for value in trend],\n'
    '        "rsi": plot_list(rsi),\n'
    '        "mfi": plot_list(mfi),\n'
    '        "momentum_source": "mfi" if use_mfi and np.isfinite(volume_values).any() and np.nanmax(np.abs(volume_values)) > 0.0 else "rsi",\n'
    '        "show_signal": show_signal,\n'
    '        "causal": True,\n'
    '        "chart_only": True,\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
