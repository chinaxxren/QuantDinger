"""Chart-only source for the market_structure_oscillator indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Market Structure Oscillator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal structure-position oscillator. No future pivots or orders are used.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Market Structure Oscillator"\n'
    'my_indicator_description = "Causal market-structure position oscillator with trend confirmation and crossover markers."\n'
    "\n"
    "# @param structure_length int 20 Structure lookback range=3:200:1\n"
    "# @param signal_length int 5 Oscillator signal smoothing range=2:50:1\n"
    "# @param volume_length int 20 Volume bias lookback range=2:200:1\n"
    "# @param show_signal bool True Show signal line\n"
    "\n"
    "\n"
    "def _clamp_int(value, default, minimum, maximum):\n"
    "    try:\n"
    "        parsed = int(value)\n"
    "    except (TypeError, ValueError):\n"
    "        parsed = default\n"
    "    return max(minimum, min(maximum, parsed))\n"
    "\n"
    "\n"
    "def _as_bool(value, default):\n"
    "    if value is None:\n"
    "        return default\n"
    "    if isinstance(value, bool):\n"
    "        return value\n"
    '    return str(value).strip().lower() not in ("false", "0", "no", "off", "")\n'
    "\n"
    "\n"
    "def _plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    'structure_length = _clamp_int(params.get("structure_length", 20), 20, 3, 200)\n'
    'signal_length = _clamp_int(params.get("signal_length", 5), 5, 2, 50)\n'
    'volume_length = _clamp_int(params.get("volume_length", 20), 20, 2, 200)\n'
    'show_signal = _as_bool(params.get("show_signal", True), True)\n'
    "\n"
    "frame = df.copy()\n"
    'high = frame["high"].astype(float)\n'
    'low = frame["low"].astype(float)\n'
    'close = frame["close"].astype(float)\n'
    'volume = frame["volume"].astype(float)\n'
    "n = len(frame)\n"
    "\n"
    "# Use only completed bars before the current bar for structure boundaries.\n"
    "prior_high = high.shift(1).rolling(structure_length, min_periods=structure_length).max().to_numpy(dtype=float)\n"
    "prior_low = low.shift(1).rolling(structure_length, min_periods=structure_length).min().to_numpy(dtype=float)\n"
    "close_values = close.to_numpy(dtype=float)\n"
    "range_size = prior_high - prior_low\n"
    "position = np.full(n, np.nan, dtype=float)\n"
    "valid_range = np.isfinite(close_values) & np.isfinite(prior_high) & np.isfinite(prior_low) & (range_size > 0.0)\n"
    "position[valid_range] = ((close_values[valid_range] - prior_low[valid_range]) / range_size[valid_range]) * 2.0 - 1.0\n"
    "\n"
    "# A short EMA slope provides a causal trend component, while relative volume\n"
    "# supplies a small confirmation term without changing the oscillator scale.\n"
    "ema = close.ewm(span=signal_length, adjust=False, min_periods=signal_length).mean().to_numpy(dtype=float)\n"
    "ema_previous = np.concatenate(([np.nan], ema[:-1]))\n"
    "atr_like = (high - low).rolling(structure_length, min_periods=structure_length).mean().to_numpy(dtype=float)\n"
    "trend_component = np.zeros(n, dtype=float)\n"
    "valid_trend = np.isfinite(close_values) & np.isfinite(ema_previous) & np.isfinite(atr_like) & (atr_like > 0.0)\n"
    "trend_component[valid_trend] = np.clip((close_values[valid_trend] - ema_previous[valid_trend]) / atr_like[valid_trend], -1.0, 1.0)\n"
    "\n"
    "volume_average = volume.shift(1).rolling(volume_length, min_periods=volume_length).mean().to_numpy(dtype=float)\n"
    "volume_bias = np.zeros(n, dtype=float)\n"
    "volume_values = volume.to_numpy(dtype=float)\n"
    "valid_volume = np.isfinite(volume_values) & np.isfinite(volume_average) & (volume_average > 0.0)\n"
    "volume_bias[valid_volume] = np.clip((volume_values[valid_volume] / volume_average[valid_volume]) - 1.0, -1.0, 1.0)\n"
    'candle_direction = np.sign(close_values - frame["open"].astype(float).to_numpy(dtype=float))\n'
    "volume_component = np.nan_to_num(candle_direction * volume_bias, nan=0.0, posinf=0.0, neginf=0.0)\n"
    "\n"
    "oscillator = 100.0 * (0.65 * position + 0.25 * trend_component + 0.10 * volume_component)\n"
    "signal = pd.Series(oscillator, index=frame.index).ewm(span=signal_length, adjust=False, min_periods=signal_length).mean().to_numpy(dtype=float)\n"
    "if not show_signal:\n"
    "    signal = np.full(n, np.nan, dtype=float)\n"
    "\n"
    "previous_oscillator = np.concatenate(([np.nan], oscillator[:-1]))\n"
    "previous_signal = np.concatenate(([np.nan], signal[:-1]))\n"
    "finite_cross = np.isfinite(oscillator) & np.isfinite(signal) & np.isfinite(previous_oscillator) & np.isfinite(previous_signal)\n"
    "buy = finite_cross & (previous_oscillator <= previous_signal) & (oscillator > signal) & (oscillator < 0.0)\n"
    "sell = finite_cross & (previous_oscillator >= previous_signal) & (oscillator < signal) & (oscillator > 0.0)\n"
    "\n"
    "buy_marks = [float(oscillator[i]) if buy[i] else None for i in range(n)]\n"
    "sell_marks = [float(oscillator[i]) if sell[i] else None for i in range(n)]\n"
    "zero = [0.0] * n\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Structure Oscillator", "data": _plot_list(oscillator), "color": "#42A5F5", "overlay": False, "width": 2},\n'
    '        {"name": "Signal", "data": _plot_list(signal), "color": "#FFB300", "overlay": False},\n'
    '        {"name": "Zero", "data": zero, "color": "#777777", "overlay": False, "width": 1},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "Bullish Structure", "data": buy_marks, "color": "#00C853"},\n'
    '        {"type": "sell", "text": "Bearish Structure", "data": sell_marks, "color": "#FF1744"},\n'
    "    ],\n"
    '    "layers": [],\n'
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "structure_length": structure_length,\n'
    '        "signal_length": signal_length,\n'
    '        "volume_length": volume_length,\n'
    '        "show_signal": show_signal,\n'
    "    },\n"
    "}\n"
)
