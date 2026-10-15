"""Chart-only source for the false_breakout indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] False Breakout (Expo)\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal false-breakout detector adapted from MiniBT's\n"
    "# False Breakout (Expo) indicator. It produces chart lines and visual\n"
    "# markers only; it never creates, submits, or manages trading orders.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] False Breakout (Expo)"\n'
    "my_indicator_description = (\n"
    '    "Consecutive new-high/new-low false-breakout detector with causal levels "\n'
    '    "and chart-only reversal signals."\n'
    ")\n"
    "\n"
    "# @param prd int 20 New-high/new-low lookback range=2:200:1\n"
    "# @param minperiod int 5 Minimum separation between the two breakout events range=1:200:1\n"
    "# @param maxperiod int 5 Signal validity window after the latest breakout range=0:200:1\n"
    "# @param ma_type string None Channel smoothing: None, WMA, or HMA\n"
    "# @param length int 10 Smoothing period for WMA/HMA range=2:200:1\n"
    "# @param aggressive bool False Use low/high for the high/low channel sources\n"
    "\n"
    "\n"
    "def as_bool(value, default=False):\n"
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
    "def finite(value):\n"
    "    return bool(np.isfinite(value))\n"
    "\n"
    "\n"
    "def wma(values, period):\n"
    '    """Trailing weighted average; missing values stay unavailable."""\n'
    "    values = np.asarray(values, dtype=float)\n"
    "    result = np.full(len(values), np.nan, dtype=float)\n"
    "    if period <= 0:\n"
    "        return result\n"
    "    weights = np.arange(1, period + 1, dtype=float)\n"
    "    denominator = float(np.sum(weights))\n"
    "    for index in range(period - 1, len(values)):\n"
    "        window = values[index - period + 1:index + 1]\n"
    "        if np.all(np.isfinite(window)):\n"
    "            result[index] = float(np.dot(window, weights) / denominator)\n"
    "    return result\n"
    "\n"
    "\n"
    "def hma(values, period):\n"
    "    period = max(2, int(period))\n"
    "    half = max(1, period // 2)\n"
    "    root = max(1, int(np.sqrt(period)))\n"
    "    raw = 2.0 * wma(values, half) - wma(values, period)\n"
    "    return wma(raw, root)\n"
    "\n"
    "\n"
    "def smooth(values, ma_type, period):\n"
    "    normalized = str(ma_type).strip().lower()\n"
    '    if normalized in ("none", "", "💎"):\n'
    "        return np.asarray(values, dtype=float).copy()\n"
    '    if normalized == "wma":\n'
    "        return wma(values, period)\n"
    '    if normalized == "hma":\n'
    "        return hma(values, period)\n"
    "    return np.asarray(values, dtype=float).copy()\n"
    "\n"
    "\n"
    "def rolling_extreme(values, period, find_max):\n"
    "    values = np.asarray(values, dtype=float)\n"
    "    result = np.full(len(values), np.nan, dtype=float)\n"
    "    for index in range(period - 1, len(values)):\n"
    "        window = values[index - period + 1:index + 1]\n"
    "        if np.all(np.isfinite(window)):\n"
    "            result[index] = float(np.max(window) if find_max else np.min(window))\n"
    "    return result\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    'prd = clamp_int(params.get("prd", 20), 20, 2, 200)\n'
    'minperiod = clamp_int(params.get("minperiod", 5), 5, 1, 200)\n'
    'maxperiod = clamp_int(params.get("maxperiod", 5), 5, 0, 200)\n'
    'length = clamp_int(params.get("length", 10), 10, 2, 200)\n'
    'ma_type = str(params.get("ma_type", "None")).strip()\n'
    'if ma_type not in ("None", "WMA", "HMA", "none", "wma", "hma", "💎"):\n'
    '    ma_type = "None"\n'
    'aggressive = as_bool(params.get("aggressive", False), False)\n'
    "\n"
    "\n"
    "df = df.copy()\n"
    'high = pd.to_numeric(df["high"], errors="coerce").to_numpy(dtype=float)\n'
    'low = pd.to_numeric(df["low"], errors="coerce").to_numpy(dtype=float)\n'
    'close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)\n'
    "n = len(close)\n"
    "\n"
    "# Normal mode detects new extremes in wick prices. Aggressive mode uses the\n"
    "# opposite wick for the channel, matching MiniBT's documented behavior.\n"
    "hi_source = low if aggressive else high\n"
    "lo_source = high if aggressive else low\n"
    "hi_raw = rolling_extreme(hi_source, prd, True)\n"
    "lo_raw = rolling_extreme(lo_source, prd, False)\n"
    "hi = smooth(hi_raw, ma_type, length)\n"
    "lo = smooth(lo_raw, ma_type, length)\n"
    "\n"
    "val = np.full(n, np.nan, dtype=float)\n"
    "count = np.zeros(n, dtype=int)\n"
    "false_break_up = np.full(n, np.nan, dtype=float)\n"
    "false_break_down = np.full(n, np.nan, dtype=float)\n"
    "long_signal = np.zeros(n, dtype=bool)\n"
    "short_signal = np.zeros(n, dtype=bool)\n"
    "\n"
    "# These are the latest two confirmed channel-break bars. Keeping the indices\n"
    "# as state avoids looking ahead and reproduces the minperiod/maxperiod window.\n"
    "latest_breakout = None\n"
    "previous_breakout = None\n"
    "current_count = 0\n"
    "current_val = np.nan\n"
    "active_up_level = np.nan\n"
    "active_down_level = np.nan\n"
    "\n"
    "for i in range(n):\n"
    "    previous_val = current_val\n"
    "    previous_close = close[i - 1] if i > 0 else np.nan\n"
    "    previous_count = current_count\n"
    "\n"
    "    cond_hi = (\n"
    "        i >= 2\n"
    "        and finite(hi[i])\n"
    "        and finite(hi[i - 1])\n"
    "        and finite(hi[i - 2])\n"
    "        and hi[i] > hi[i - 1]\n"
    "        and hi[i - 1] <= hi[i - 2]\n"
    "    )\n"
    "    cond_lo = (\n"
    "        i >= 2\n"
    "        and finite(lo[i])\n"
    "        and finite(lo[i - 1])\n"
    "        and finite(lo[i - 2])\n"
    "        and lo[i] < lo[i - 1]\n"
    "        and lo[i - 1] >= lo[i - 2]\n"
    "    )\n"
    "\n"
    "    # A bar cannot normally be both a new high and a new low, but process both\n"
    "    # deterministically if malformed input makes that possible.\n"
    "    if cond_hi:\n"
    "        previous_breakout = latest_breakout\n"
    "        latest_breakout = i\n"
    "        current_count -= 1\n"
    "        current_val = low[i] if finite(low[i]) else current_val\n"
    "    if cond_lo:\n"
    "        previous_breakout = latest_breakout\n"
    "        latest_breakout = i\n"
    "        current_count += 1\n"
    "        current_val = high[i] if finite(high[i]) else current_val\n"
    "\n"
    "    # Pine's crossunder/crossover compare the current and previous values of\n"
    "    # both series. This is causal even though the trigger level can change.\n"
    "    cross_down = (\n"
    "        finite(close[i])\n"
    "        and finite(current_val)\n"
    "        and finite(previous_close)\n"
    "        and finite(previous_val)\n"
    "        and close[i] < current_val\n"
    "        and previous_close >= previous_val\n"
    "    )\n"
    "    cross_up = (\n"
    "        finite(close[i])\n"
    "        and finite(current_val)\n"
    "        and finite(previous_close)\n"
    "        and finite(previous_val)\n"
    "        and close[i] > current_val\n"
    "        and previous_close <= previous_val\n"
    "    )\n"
    "\n"
    "    window_ready = (\n"
    "        latest_breakout is not None\n"
    "        and previous_breakout is not None\n"
    "        and previous_breakout + minperiod < latest_breakout\n"
    "        and i - maxperiod <= latest_breakout\n"
    "    )\n"
    "    if window_ready and current_count < -1 and cross_down:\n"
    "        short_signal[i] = True\n"
    "        active_up_level = current_val\n"
    "        current_count = 0\n"
    "    elif window_ready and current_count > 1 and cross_up:\n"
    "        long_signal[i] = True\n"
    "        active_down_level = current_val\n"
    "        current_count = 0\n"
    "\n"
    "    # Horizontal lines start when the signal is confirmed and remain visible\n"
    "    # until the next signal of the same type. This avoids repainting historical\n"
    "    # bars when a later bar confirms a false breakout.\n"
    "    if finite(active_up_level):\n"
    "        false_break_up[i] = active_up_level\n"
    "    if finite(active_down_level):\n"
    "        false_break_down[i] = active_down_level\n"
    "\n"
    "    val[i] = current_val\n"
    "    count[i] = current_count\n"
    "\n"
    "long_marks = [\n"
    "    float(low[i]) if long_signal[i] and finite(low[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "short_marks = [\n"
    "    float(high[i]) if short_signal[i] and finite(high[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    "        {\n"
    '            "name": "False Break Up",\n'
    '            "data": plot_list(false_break_up),\n'
    '            "color": "#f23645",\n'
    '            "width": 2,\n'
    '            "overlay": True,\n'
    "        },\n"
    "        {\n"
    '            "name": "False Break Down",\n'
    '            "data": plot_list(false_break_down),\n'
    '            "color": "#6ce5a0",\n'
    '            "width": 2,\n'
    '            "overlay": True,\n'
    "        },\n"
    "    ],\n"
    '    "signals": [\n'
    "        {\n"
    '            "type": "buy",\n'
    '            "text": "False Break Down",\n'
    '            "data": long_marks,\n'
    '            "color": "#6ce5a0",\n'
    '            "anchor": "low",\n'
    '            "shape": "triangle",\n'
    "        },\n"
    "        {\n"
    '            "type": "sell",\n'
    '            "text": "False Break Up",\n'
    '            "data": short_marks,\n'
    '            "color": "#f23645",\n'
    '            "anchor": "high",\n'
    '            "shape": "inverted_triangle",\n'
    "        },\n"
    "    ],\n"
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "prd": prd,\n'
    '        "minperiod": minperiod,\n'
    '        "maxperiod": maxperiod,\n'
    '        "ma_type": ma_type.lower(),\n'
    '        "length": length,\n'
    '        "aggressive": aggressive,\n'
    '        "hi": plot_list(hi),\n'
    '        "lo": plot_list(lo),\n'
    '        "val": plot_list(val),\n'
    '        "count": [int(value) for value in count],\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
