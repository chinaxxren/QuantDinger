"""Chart-only source for the itg_scalper indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] ITG Scalper\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal EMA/ATR scalper overlay. Signals are chart markers only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] ITG Scalper"\n'
    'my_indicator_description = "Fast and slow trend filters with ATR scalp bands and causal crossover markers."\n'
    "\n"
    "# @param fast_length int 5 Fast EMA length range=2:50:1\n"
    "# @param slow_length int 13 Slow EMA length range=3:100:1\n"
    "# @param atr_length int 14 ATR lookback range=2:100:1\n"
    "# @param atr_multiplier float 1.5 ATR band multiplier range=0.1:5.0:0.1\n"
    "# @param show_bands bool True Show ATR scalp bands\n"
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
    'fast_length = _clamp_int(params.get("fast_length", 5), 5, 2, 50)\n'
    'slow_length = _clamp_int(params.get("slow_length", 13), 13, 3, 100)\n'
    "if slow_length <= fast_length:\n"
    "    slow_length = min(100, fast_length + 1)\n"
    'atr_length = _clamp_int(params.get("atr_length", 14), 14, 2, 100)\n'
    'atr_multiplier = _clamp_float(params.get("atr_multiplier", 1.5), 1.5, 0.1, 5.0)\n'
    'show_bands = _as_bool(params.get("show_bands", True), True)\n'
    "\n"
    "frame = df.copy()\n"
    'open_values = frame["open"].astype(float).to_numpy(dtype=float)\n'
    'high = frame["high"].astype(float)\n'
    'low = frame["low"].astype(float)\n'
    'close = frame["close"].astype(float)\n'
    "close_values = close.to_numpy(dtype=float)\n"
    "n = len(frame)\n"
    "\n"
    "fast = close.ewm(span=fast_length, adjust=False, min_periods=fast_length).mean().to_numpy(dtype=float)\n"
    "slow = close.ewm(span=slow_length, adjust=False, min_periods=slow_length).mean().to_numpy(dtype=float)\n"
    "true_range = pd.concat(\n"
    "    [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1\n"
    ").max(axis=1)\n"
    "atr = true_range.ewm(alpha=1.0 / atr_length, adjust=False, min_periods=atr_length).mean().to_numpy(dtype=float)\n"
    "\n"
    "basis = slow\n"
    "upper = basis + atr_multiplier * atr\n"
    "lower = basis - atr_multiplier * atr\n"
    "previous_fast = np.concatenate(([np.nan], fast[:-1]))\n"
    "previous_slow = np.concatenate(([np.nan], slow[:-1]))\n"
    "finite_cross = np.isfinite(fast) & np.isfinite(slow) & np.isfinite(previous_fast) & np.isfinite(previous_slow)\n"
    "buy = finite_cross & (previous_fast <= previous_slow) & (fast > slow)\n"
    "sell = finite_cross & (previous_fast >= previous_slow) & (fast < slow)\n"
    "\n"
    "if not show_bands:\n"
    "    upper = np.full(n, np.nan, dtype=float)\n"
    "    lower = np.full(n, np.nan, dtype=float)\n"
    "\n"
    "buy_marks = [float(low.iloc[i]) * 0.995 if buy[i] and np.isfinite(low.iloc[i]) else None for i in range(n)]\n"
    "sell_marks = [float(high.iloc[i]) * 1.005 if sell[i] and np.isfinite(high.iloc[i]) else None for i in range(n)]\n"
    "trend = np.where(np.isfinite(fast) & np.isfinite(slow) & (fast >= slow), 1, -1)\n"
    "trend = [int(value) if np.isfinite(value) else 0 for value in trend]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Fast EMA", "data": _plot_list(fast), "color": "#26A69A", "overlay": True, "width": 1},\n'
    '        {"name": "Slow EMA", "data": _plot_list(slow), "color": "#FFB300", "overlay": True, "width": 2},\n'
    '        {"name": "Scalp Upper", "data": _plot_list(upper), "color": "#90CAF9", "overlay": True},\n'
    '        {"name": "Scalp Lower", "data": _plot_list(lower), "color": "#90CAF9", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "ITG Buy", "data": buy_marks, "color": "#00C853"},\n'
    '        {"type": "sell", "text": "ITG Sell", "data": sell_marks, "color": "#FF1744"},\n'
    "    ],\n"
    '    "layers": [],\n'
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "fast_length": fast_length,\n'
    '        "slow_length": slow_length,\n'
    '        "atr_length": atr_length,\n'
    '        "atr_multiplier": atr_multiplier,\n'
    '        "show_bands": show_bands,\n'
    '        "trend": trend,\n'
    "    },\n"
    "}\n"
)
