"""Chart-only source for the volume_weighted_macd indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Volume Weighted MACD\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# MACD calculated from a volume-weighted price source. This is a chart-only\n"
    "# oscillator and never submits or manages orders.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Volume Weighted MACD"\n'
    'my_indicator_description = "MACD oscillator using a causal volume-weighted price with crossover markers."\n'
    "\n"
    "# @param fast_length int 12 Fast EMA period range=2:100:1\n"
    "# @param slow_length int 26 Slow EMA period range=3:200:1\n"
    "# @param signal_length int 9 Signal EMA period range=2:100:1\n"
    "# @param histogram bool True Show MACD histogram range=0:1:1\n"
    "\n"
    "def _int_param(name, default, minimum, maximum):\n"
    "    try:\n"
    "        value = int(params.get(name, default))\n"
    "    except (TypeError, ValueError):\n"
    "        value = default\n"
    "    return max(minimum, min(maximum, value))\n"
    "\n"
    "def _as_bool(value, default=True):\n"
    "    if value is None:\n"
    "        return default\n"
    "    if isinstance(value, bool):\n"
    "        return value\n"
    '    return str(value).strip().lower() not in ("false", "0", "no", "off", "")\n'
    "\n"
    'fast_length = _int_param("fast_length", 12, 2, 100)\n'
    'slow_length = _int_param("slow_length", 26, 3, 200)\n'
    "if slow_length <= fast_length:\n"
    "    slow_length = min(200, fast_length + 1)\n"
    'signal_length = _int_param("signal_length", 9, 2, 100)\n'
    'show_histogram = _as_bool(params.get("histogram", True), True)\n'
    "\n"
    "frame = df.copy()\n"
    'close = frame["close"].astype(float)\n'
    'volume = frame.get("volume", pd.Series(0.0, index=frame.index)).astype(float)\n'
    "volume = volume.clip(lower=0.0)\n"
    "volume_sum = volume.rolling(slow_length, min_periods=1).sum()\n"
    "weighted_sum = (close * volume).rolling(slow_length, min_periods=1).sum()\n"
    "weighted_price = (weighted_sum / volume_sum.replace(0.0, np.nan)).where(volume_sum > 0.0, close)\n"
    "\n"
    "fast = weighted_price.ewm(span=fast_length, adjust=False, min_periods=fast_length).mean()\n"
    "slow = weighted_price.ewm(span=slow_length, adjust=False, min_periods=slow_length).mean()\n"
    "macd = fast - slow\n"
    "signal = macd.ewm(span=signal_length, adjust=False, min_periods=signal_length).mean()\n"
    "hist = macd - signal\n"
    "\n"
    "macd_values = macd.to_numpy(dtype=float)\n"
    "signal_values = signal.to_numpy(dtype=float)\n"
    "hist_values = hist.to_numpy(dtype=float)\n"
    "previous_macd = np.concatenate(([np.nan], macd_values[:-1]))\n"
    "previous_signal = np.concatenate(([np.nan], signal_values[:-1]))\n"
    "finite = (\n"
    "    np.isfinite(macd_values)\n"
    "    & np.isfinite(signal_values)\n"
    "    & np.isfinite(previous_macd)\n"
    "    & np.isfinite(previous_signal)\n"
    ")\n"
    "buy = finite & (previous_macd <= previous_signal) & (macd_values > signal_values)\n"
    "sell = finite & (previous_macd >= previous_signal) & (macd_values < signal_values)\n"
    "\n"
    "if not show_histogram:\n"
    "    hist_values = np.full(len(frame), np.nan, dtype=float)\n"
    "\n"
    "def _plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "VW MACD", "data": _plot_list(macd_values), "color": "#26A69A", "overlay": False},\n'
    '        {"name": "Signal", "data": _plot_list(signal_values), "color": "#FFB300", "overlay": False},\n'
    '        {"name": "Histogram", "data": _plot_list(hist_values), "color": "#90CAF9", "overlay": False},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "VW MACD+", "data": [float(value) if flag and np.isfinite(value) else None for value, flag in zip(macd_values, buy)], "color": "#00C853"},\n'
    '        {"type": "sell", "text": "VW MACD-", "data": [float(value) if flag and np.isfinite(value) else None for value, flag in zip(macd_values, sell)], "color": "#FF1744"},\n'
    "    ],\n"
    '    "layers": [],\n'
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "fast_length": fast_length,\n'
    '        "slow_length": slow_length,\n'
    '        "signal_length": signal_length,\n'
    '        "histogram": show_histogram,\n'
    "    },\n"
    "}\n"
)
