"""Chart-only source for the envelope_rsi_signals indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Envelope RSI Signals\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# RSI envelope with causal threshold-crossing markers. Signals are visual only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Envelope RSI Signals"\n'
    'my_indicator_description = "RSI volatility envelope with causal oversold and overbought reversal signals."\n'
    "\n"
    "# @param rsi_length int 14 RSI lookback range=2:50:1\n"
    "# @param envelope_length int 20 Envelope smoothing lookback range=2:100:1\n"
    "# @param envelope_multiplier float 1.5 Envelope deviation multiplier range=0.1:5.0:0.1\n"
    "# @param show_envelope bool True Show RSI envelope bands\n"
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
    "def _clamp_float(value, default, minimum, maximum):\n"
    "    try:\n"
    "        parsed = float(value)\n"
    "    except (TypeError, ValueError):\n"
    "        parsed = default\n"
    "    if not np.isfinite(parsed):\n"
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
    'rsi_length = _clamp_int(params.get("rsi_length", 14), 14, 2, 50)\n'
    'envelope_length = _clamp_int(params.get("envelope_length", 20), 20, 2, 100)\n'
    'envelope_multiplier = _clamp_float(params.get("envelope_multiplier", 1.5), 1.5, 0.1, 5.0)\n'
    'show_envelope = _as_bool(params.get("show_envelope", True), True)\n'
    "\n"
    "frame = df.copy()\n"
    'close = frame["close"].astype(float)\n'
    "delta = close.diff()\n"
    "gain = delta.clip(lower=0.0)\n"
    "loss = (-delta).clip(lower=0.0)\n"
    "avg_gain = gain.ewm(alpha=1.0 / rsi_length, adjust=False, min_periods=rsi_length).mean()\n"
    "avg_loss = loss.ewm(alpha=1.0 / rsi_length, adjust=False, min_periods=rsi_length).mean()\n"
    "up = avg_gain.to_numpy(dtype=float)\n"
    "down = avg_loss.to_numpy(dtype=float)\n"
    "rsi = np.full(len(frame), np.nan, dtype=float)\n"
    "valid = np.isfinite(up) & np.isfinite(down)\n"
    "rsi[valid & (down <= 0.0) & (up > 0.0)] = 100.0\n"
    "rsi[valid & (up <= 0.0) & (down > 0.0)] = 0.0\n"
    "rsi[valid & (up <= 0.0) & (down <= 0.0)] = 50.0\n"
    "normal = valid & (up > 0.0) & (down > 0.0)\n"
    "rsi[normal] = 100.0 - 100.0 / (1.0 + up[normal] / down[normal])\n"
    "\n"
    "rsi_series = pd.Series(rsi, index=frame.index)\n"
    "basis = rsi_series.ewm(span=envelope_length, adjust=False, min_periods=envelope_length).mean().to_numpy(dtype=float)\n"
    "deviation = rsi_series.rolling(envelope_length, min_periods=envelope_length).std(ddof=0).to_numpy(dtype=float)\n"
    "upper = np.clip(basis + envelope_multiplier * deviation, 0.0, 100.0)\n"
    "lower = np.clip(basis - envelope_multiplier * deviation, 0.0, 100.0)\n"
    "\n"
    "previous_rsi = np.concatenate(([np.nan], rsi[:-1]))\n"
    "previous_upper = np.concatenate(([np.nan], upper[:-1]))\n"
    "previous_lower = np.concatenate(([np.nan], lower[:-1]))\n"
    "finite = np.isfinite(rsi) & np.isfinite(basis)\n"
    "buy = finite & np.isfinite(previous_rsi) & np.isfinite(previous_lower) & (previous_rsi <= previous_lower) & (rsi > lower)\n"
    "sell = finite & np.isfinite(previous_rsi) & np.isfinite(previous_upper) & (previous_rsi >= previous_upper) & (rsi < upper)\n"
    "\n"
    "if not show_envelope:\n"
    "    upper = np.full(len(frame), np.nan, dtype=float)\n"
    "    lower = np.full(len(frame), np.nan, dtype=float)\n"
    "\n"
    'close_values = frame["close"].astype(float).to_numpy(dtype=float)\n'
    'low_values = frame["low"].astype(float).to_numpy(dtype=float)\n'
    'high_values = frame["high"].astype(float).to_numpy(dtype=float)\n'
    "buy_marks = [float(rsi[i]) if buy[i] and np.isfinite(rsi[i]) else None for i in range(len(frame))]\n"
    "sell_marks = [float(rsi[i]) if sell[i] and np.isfinite(rsi[i]) else None for i in range(len(frame))]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "RSI", "data": _plot_list(rsi), "color": "#7E57C2", "overlay": False, "width": 2},\n'
    '        {"name": "RSI Basis", "data": _plot_list(basis), "color": "#FFB300", "overlay": False},\n'
    '        {"name": "Envelope Upper", "data": _plot_list(upper), "color": "#EF5350", "overlay": False},\n'
    '        {"name": "Envelope Lower", "data": _plot_list(lower), "color": "#26A69A", "overlay": False},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "RSI Buy", "data": buy_marks, "color": "#00C853"},\n'
    '        {"type": "sell", "text": "RSI Sell", "data": sell_marks, "color": "#FF1744"},\n'
    "    ],\n"
    '    "layers": [],\n'
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "rsi_length": rsi_length,\n'
    '        "envelope_length": envelope_length,\n'
    '        "envelope_multiplier": envelope_multiplier,\n'
    '        "show_envelope": show_envelope,\n'
    '        "overbought": 70.0,\n'
    '        "oversold": 30.0,\n'
    "    },\n"
    "}\n"
)
