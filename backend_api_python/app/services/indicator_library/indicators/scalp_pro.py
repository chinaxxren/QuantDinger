"""Chart-only source for the scalp_pro indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Scalp Pro\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Ehlers two-pole SuperSmoother MACD-style oscillator.  All values are\n"
    "# calculated from the current and completed historical bars only; signals are\n"
    "# chart markers and never submit or manage orders.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Scalp Pro"\n'
    "my_indicator_description = (\n"
    '    "Scalp Pro SuperSmoother MACD oscillator with causal crossover markers."\n'
    ")\n"
    "\n"
    "# @param fast_length int 8 Fast SuperSmoother period range=1:200:1\n"
    "# @param slow_length int 10 Slow SuperSmoother period range=2:500:1\n"
    "# @param smooth_length int 8 Signal smoothing period range=1:200:1\n"
    "# @param scale float 10000000.0 MACD display scale range=0.0001:100000000.0:0.0001\n"
    "# @param source string close Price source: close, hl2, hlc3, or ohlc4\n"
    "# @param show_fill bool True Fill area between MACD and signal\n"
    "# @param show_signals bool True Show buy/sell chart markers\n"
    "# @param qty int 1 Compatibility quantity; visual only\n"
    "\n"
    "\n"
    "def as_bool(value, default):\n"
    "    if value is None:\n"
    "        return default\n"
    "    text = str(value).strip().lower()\n"
    '    if text in ("false", "0", "no", "off"):\n'
    "        return False\n"
    '    if text in ("true", "1", "yes", "on"):\n'
    "        return True\n"
    "    return bool(value)\n"
    "\n"
    "\n"
    "def clamp_int(value, default, minimum, maximum):\n"
    "    try:\n"
    "        parsed = int(value)\n"
    "    except (TypeError, ValueError):\n"
    "        parsed = default\n"
    "    return min(maximum, max(minimum, parsed))\n"
    "\n"
    "\n"
    "def clamp_float(value, default, minimum, maximum):\n"
    "    try:\n"
    "        parsed = float(value)\n"
    "    except (TypeError, ValueError):\n"
    "        parsed = default\n"
    "    if not np.isfinite(parsed):\n"
    "        parsed = default\n"
    "    return min(maximum, max(minimum, parsed))\n"
    "\n"
    "\n"
    "def selected_source(frame, name):\n"
    '    normalized = str(name or "close").strip().lower()\n'
    '    open_price = frame["open"].astype(float).to_numpy(copy=True)\n'
    '    high = frame["high"].astype(float).to_numpy(copy=True)\n'
    '    low = frame["low"].astype(float).to_numpy(copy=True)\n'
    '    close = frame["close"].astype(float).to_numpy(copy=True)\n'
    "    columns = {\n"
    '        "close": close,\n'
    '        "hl2": (high + low) / 2.0,\n'
    '        "hlc3": (high + low + close) / 3.0,\n'
    '        "ohlc4": (open_price + high + low + close) / 4.0,\n'
    "    }\n"
    "    if normalized not in columns:\n"
    '        normalized = "close"\n'
    "    return columns[normalized], normalized\n"
    "\n"
    "\n"
    "def super_smoother(values, length):\n"
    '    """Apply the causal Ehlers two-pole SuperSmoother filter."""\n'
    "    result = np.full(len(values), np.nan, dtype=float)\n"
    "    angle = 1.414 * np.pi / float(length)\n"
    "    decay = np.exp(-angle)\n"
    "    c2 = 2.0 * decay * np.cos(angle)\n"
    "    c3 = -(decay * decay)\n"
    "    c1 = 1.0 - c2 - c3\n"
    "    previous_price = 0.0\n"
    "    previous_one = 0.0\n"
    "    previous_two = 0.0\n"
    "    for i, value in enumerate(values):\n"
    "        if not np.isfinite(value):\n"
    "            continue\n"
    "        filtered = (\n"
    "            c1 * (float(value) + previous_price) / 2.0\n"
    "            + c2 * previous_one\n"
    "            + c3 * previous_two\n"
    "        )\n"
    "        result[i] = filtered\n"
    "        previous_price = float(value)\n"
    "        previous_two = previous_one\n"
    "        previous_one = filtered\n"
    "    return result\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    'fast_length = clamp_int(params.get("fast_length", 8), 8, 1, 200)\n'
    'slow_length = clamp_int(params.get("slow_length", 10), 10, 2, 500)\n'
    "if slow_length <= fast_length:\n"
    "    slow_length = min(500, fast_length + 1)\n"
    'smooth_length = clamp_int(params.get("smooth_length", 8), 8, 1, 200)\n'
    'scale = clamp_float(params.get("scale", 10000000.0), 10000000.0, 0.0001, 100000000.0)\n'
    'source, source_name = selected_source(df, params.get("source", "close"))\n'
    'show_fill = as_bool(params.get("show_fill", True), True)\n'
    'show_signals = as_bool(params.get("show_signals", True), True)\n'
    'qty = clamp_int(params.get("qty", 1), 1, 1, 1000000)\n'
    "\n"
    "fast_smoothed = super_smoother(source, fast_length)\n"
    "slow_smoothed = super_smoother(source, slow_length)\n"
    "macd = (fast_smoothed - slow_smoothed) * scale\n"
    "signal = super_smoother(macd, smooth_length)\n"
    "\n"
    "previous_macd = np.concatenate(([np.nan], macd[:-1]))\n"
    "previous_signal = np.concatenate(([np.nan], signal[:-1]))\n"
    "finite_cross = (\n"
    "    np.isfinite(macd)\n"
    "    & np.isfinite(signal)\n"
    "    & np.isfinite(previous_macd)\n"
    "    & np.isfinite(previous_signal)\n"
    ")\n"
    "buy = finite_cross & (previous_macd <= previous_signal) & (macd > signal)\n"
    "sell = finite_cross & (previous_macd >= previous_signal) & (macd < signal)\n"
    "\n"
    "if show_signals:\n"
    "    buy_marks = [float(macd[i]) if buy[i] else None for i in range(len(macd))]\n"
    "    sell_marks = [float(macd[i]) if sell[i] else None for i in range(len(macd))]\n"
    "else:\n"
    "    buy_marks = [None] * len(macd)\n"
    "    sell_marks = [None] * len(macd)\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    "        {\n"
    '            "name": "MACD",\n'
    '            "data": plot_list(macd),\n'
    '            "color": "#217A21",\n'
    '            "overlay": False,\n'
    '            "width": 2,\n'
    "        },\n"
    "        {\n"
    '            "name": "Signal",\n'
    '            "data": plot_list(signal),\n'
    '            "color": "#FFFF00",\n'
    '            "overlay": False,\n'
    '            "width": 1,\n'
    "        },\n"
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "Buy", "data": buy_marks, "color": "#00C853"},\n'
    '        {"type": "sell", "text": "Sell", "data": sell_marks, "color": "#FF0000"},\n'
    "    ],\n"
    '    "layers": [],\n'
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "fast_length": fast_length,\n'
    '        "slow_length": slow_length,\n'
    '        "smooth_length": smooth_length,\n'
    '        "scale": scale,\n'
    '        "source": source_name,\n'
    '        "show_fill": show_fill,\n'
    '        "show_signals": show_signals,\n'
    '        "qty": qty,\n'
    '        "ssmooth": plot_list(fast_smoothed),\n'
    '        "ssmooth2": plot_list(slow_smoothed),\n'
    '        "macd": plot_list(macd),\n'
    '        "signal": plot_list(signal),\n'
    '        "long_signal": [bool(value) for value in buy],\n'
    '        "short_signal": [bool(value) for value in sell],\n'
    "    },\n"
    "}\n"
)
