"""Chart-only source for the trading_abc indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Trading ABC\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal moving-average trend, ZigZag, and ABC retracement detector.\n"
    "# Every event is emitted on the bar that confirms it; historical bars are\n"
    "# never rewritten with information from a later bar.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Trading ABC"\n'
    'my_indicator_description = "Causal moving-average trend, ZigZag, and ABC retracement chart indicator."\n'
    "\n"
    "# @param prd int 8 ZigZag lookback range=2:40:1\n"
    "# @param fiboup float 0.618 Upper Fibonacci retracement range=0.1:1.5:0.001\n"
    "# @param fibodn float 0.382 Lower Fibonacci retracement range=0.1:1.5:0.001\n"
    "# @param errorrate float 5.0 ABC ratio tolerance percent range=0.0:25.0:0.5\n"
    "# @param src_ma str close Moving-average source choices=close,hl2,hlc3,ohlc4\n"
    "# @param malen1 int 50 SMA length range=2:300:1\n"
    "# @param malen2 int 100 SMA length range=2:300:1\n"
    "# @param malen3 int 150 SMA length range=2:300:1\n"
    "# @param malen4 int 200 SMA length range=2:300:1\n"
    "# @param malen5 int 20 EMA length range=2:300:1\n"
    "# @param malen6 int 40 EMA length range=2:300:1\n"
    "# @param showabc bool true Show the ABC retracement line\n"
    "# @param keepabc bool true Keep confirmed ABC lines visible\n"
    "# @param showcloud bool true Use the moving-average trend filter\n"
    "# @param showzigzag bool true Show the causal ZigZag points\n"
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
    "    return max(minimum, min(maximum, parsed))\n"
    "\n"
    "\n"
    "def _as_bool(value, default):\n"
    "    if isinstance(value, bool):\n"
    "        return value\n"
    "    if value is None:\n"
    "        return default\n"
    '    return str(value).strip().lower() not in ("0", "false", "no", "off", "")\n'
    "\n"
    "\n"
    'prd = _clamp_int(params.get("prd", 8), 8, 2, 40)\n'
    'fiboup = _clamp_float(params.get("fiboup", 0.618), 0.618, 0.1, 1.5)\n'
    'fibodn = _clamp_float(params.get("fibodn", 0.382), 0.382, 0.1, 1.5)\n'
    'errorrate = _clamp_float(params.get("errorrate", 5.0), 5.0, 0.0, 25.0)\n'
    'src_ma = str(params.get("src_ma", "close")).strip().lower()\n'
    'if src_ma not in ("close", "hl2", "hlc3", "ohlc4"):\n'
    '    src_ma = "close"\n'
    "\n"
    'malen1 = _clamp_int(params.get("malen1", 50), 50, 2, 300)\n'
    'malen2 = _clamp_int(params.get("malen2", 100), 100, 2, 300)\n'
    'malen3 = _clamp_int(params.get("malen3", 150), 150, 2, 300)\n'
    'malen4 = _clamp_int(params.get("malen4", 200), 200, 2, 300)\n'
    'malen5 = _clamp_int(params.get("malen5", 20), 20, 2, 300)\n'
    'malen6 = _clamp_int(params.get("malen6", 40), 40, 2, 300)\n'
    'showabc = _as_bool(params.get("showabc", True), True)\n'
    'keepabc = _as_bool(params.get("keepabc", True), True)\n'
    'showcloud = _as_bool(params.get("showcloud", True), True)\n'
    'showzigzag = _as_bool(params.get("showzigzag", True), True)\n'
    "\n"
    "\n"
    "df = df.copy()\n"
    'open_values = df["open"].astype(float).to_numpy()\n'
    'high_values = df["high"].astype(float).to_numpy()\n'
    'low_values = df["low"].astype(float).to_numpy()\n'
    'close_values = df["close"].astype(float).to_numpy()\n'
    "n = len(df)\n"
    "\n"
    'if src_ma == "hl2":\n'
    '    ma_source = (df["high"].astype(float) + df["low"].astype(float)) / 2.0\n'
    'elif src_ma == "hlc3":\n'
    "    ma_source = (\n"
    '        df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)\n'
    "    ) / 3.0\n"
    'elif src_ma == "ohlc4":\n'
    "    ma_source = (\n"
    '        df["open"].astype(float)\n'
    '        + df["high"].astype(float)\n'
    '        + df["low"].astype(float)\n'
    '        + df["close"].astype(float)\n'
    "    ) / 4.0\n"
    "else:\n"
    '    ma_source = df["close"].astype(float)\n'
    "\n"
    "sma_lengths = (malen1, malen2, malen3, malen4)\n"
    "ema_lengths = (malen5, malen6)\n"
    "ma_series = [\n"
    "    ma_source.rolling(length, min_periods=length).mean().to_numpy(dtype=float)\n"
    "    for length in sma_lengths\n"
    "]\n"
    "ma_series.extend(\n"
    "    [ma_source.ewm(span=length, adjust=False, min_periods=length).mean().to_numpy(dtype=float) for length in ema_lengths]\n"
    ")\n"
    "\n"
    "# The trend filter only changes after two consecutive qualifying bars.\n"
    "trend = np.zeros(n, dtype=float)\n"
    "upper_count = np.zeros(n, dtype=float)\n"
    "lower_count = np.zeros(n, dtype=float)\n"
    "up_streak = 0\n"
    "down_streak = 0\n"
    "current_trend = 0\n"
    "for i in range(n):\n"
    "    body_top = max(open_values[i], close_values[i])\n"
    "    body_bottom = min(open_values[i], close_values[i])\n"
    "    upper = 0\n"
    "    lower = 0\n"
    "    for ma in ma_series:\n"
    "        if np.isfinite(ma[i]):\n"
    "            if ma[i] > body_top:\n"
    "                upper += 1\n"
    "            elif ma[i] < body_bottom:\n"
    "                lower += 1\n"
    "    upper_count[i] = upper\n"
    "    lower_count[i] = lower\n"
    "    if showcloud and lower > 0 and upper == 0:\n"
    "        up_streak += 1\n"
    "        down_streak = 0\n"
    "    elif showcloud and upper > 0 and lower == 0:\n"
    "        down_streak += 1\n"
    "        up_streak = 0\n"
    "    else:\n"
    "        up_streak = 0\n"
    "        down_streak = 0\n"
    "    if up_streak >= 2:\n"
    "        current_trend = 1\n"
    "    elif down_streak >= 2:\n"
    "        current_trend = -1\n"
    "    trend[i] = current_trend\n"
    "\n"
    "# Causal ZigZag. A point is created or updated only at the current bar using\n"
    "# the trailing lookback window; no future candle is used to back-fill a pivot.\n"
    "zz_direction = 0\n"
    "zz_points = []\n"
    "zz_plot = np.full(n, np.nan, dtype=float)\n"
    "zz_direction_plot = np.zeros(n, dtype=float)\n"
    "abc_line = np.full(n, np.nan, dtype=float)\n"
    "abc_rate_plot = np.full(n, np.nan, dtype=float)\n"
    "abc_state = np.zeros(n, dtype=float)\n"
    "abc_events = [None] * n\n"
    "abc_point_events = [None] * n\n"
    "abc_active = False\n"
    "abc_start = -1\n"
    "abc_is_bullish = False\n"
    "abc_end_index = -1\n"
    "abc_end_value = np.nan\n"
    "\n"
    "for i in range(n):\n"
    "    start = max(0, i - prd + 1)\n"
    "    window_high = high_values[start : i + 1]\n"
    "    window_low = low_values[start : i + 1]\n"
    "    current_high = high_values[i]\n"
    "    current_low = low_values[i]\n"
    "    is_high = np.isfinite(current_high) and current_high >= np.nanmax(window_high)\n"
    "    is_low = np.isfinite(current_low) and current_low <= np.nanmin(window_low)\n"
    "\n"
    "    pivot_kind = None\n"
    "    pivot_value = np.nan\n"
    "    if is_high and not is_low:\n"
    '        pivot_kind = "high"\n'
    "        pivot_value = current_high\n"
    "    elif is_low and not is_high:\n"
    '        pivot_kind = "low"\n'
    "        pivot_value = current_low\n"
    "    elif is_high and is_low:\n"
    "        # A one-candle range can be both extremes. Keep the existing direction\n"
    "        # when possible, otherwise use the larger candle excursion.\n"
    "        if zz_direction > 0:\n"
    '            pivot_kind = "high"\n'
    "            pivot_value = current_high\n"
    "        elif zz_direction < 0:\n"
    '            pivot_kind = "low"\n'
    "            pivot_value = current_low\n"
    "        elif np.isfinite(open_values[i]) and close_values[i] >= open_values[i]:\n"
    '            pivot_kind = "high"\n'
    "            pivot_value = current_high\n"
    "        else:\n"
    '            pivot_kind = "low"\n'
    "            pivot_value = current_low\n"
    "\n"
    "    if pivot_kind is not None:\n"
    '        next_direction = 1 if pivot_kind == "high" else -1\n'
    "        if not zz_points:\n"
    "            zz_points.append((i, float(pivot_value), pivot_kind))\n"
    "            zz_direction = next_direction\n"
    "            zz_plot[i] = float(pivot_value)\n"
    "            abc_point_events[i] = pivot_kind.upper()\n"
    "        elif next_direction == zz_direction and zz_points[-1][2] == pivot_kind:\n"
    "            last_index, last_value, last_kind = zz_points[-1]\n"
    "            should_update = (\n"
    '                pivot_value > last_value if pivot_kind == "high" else pivot_value < last_value\n'
    "            )\n"
    "            if should_update:\n"
    "                zz_points[-1] = (i, float(pivot_value), last_kind)\n"
    "                zz_plot[i] = float(pivot_value)\n"
    "                abc_point_events[i] = pivot_kind.upper()\n"
    "        else:\n"
    "            zz_points.append((i, float(pivot_value), pivot_kind))\n"
    "            zz_direction = next_direction\n"
    "            if len(zz_points) > 5:\n"
    "                zz_points = zz_points[-5:]\n"
    "            zz_plot[i] = float(pivot_value)\n"
    "            abc_point_events[i] = pivot_kind.upper()\n"
    "\n"
    "    if zz_points:\n"
    "        zz_direction_plot[i] = float(zz_direction)\n"
    "\n"
    "    # Confirm an ABC retracement only after the third causal ZigZag point.\n"
    "    if len(zz_points) >= 3:\n"
    "        a = zz_points[-3]\n"
    "        b = zz_points[-2]\n"
    "        c = zz_points[-1]\n"
    "        denominator = c[1] - b[1]\n"
    "        if np.isfinite(denominator) and abs(denominator) > 1e-12:\n"
    "            rate = (a[1] - b[1]) / denominator\n"
    "            lower_rate = fibodn * (1.0 - errorrate / 100.0)\n"
    "            upper_rate = fiboup * (1.0 + errorrate / 100.0)\n"
    "            if lower_rate <= rate <= upper_rate:\n"
    "                if (not abc_active) or abc_end_index != c[0]:\n"
    "                    abc_active = True\n"
    "                    abc_start = i\n"
    '                    abc_is_bullish = c[2] == "low"\n'
    "                    abc_end_index = c[0]\n"
    "                    abc_end_value = c[1]\n"
    '                    abc_events[i] = "ABC Bull" if abc_is_bullish else "ABC Bear"\n'
    "                abc_rate_plot[i] = float(rate)\n"
    "            elif abc_active and i > abc_start + 6:\n"
    "                abc_active = False\n"
    "                abc_end_index = -1\n"
    "                abc_end_value = np.nan\n"
    "\n"
    "    if abc_active:\n"
    "        abc_state[i] = 1.0 if abc_is_bullish else -1.0\n"
    "        if abc_end_index >= 0 and i >= abc_start:\n"
    "            if keepabc or i == abc_start:\n"
    "                abc_line[i] = abc_end_value\n"
    "        abc_bar_count = i - abc_start\n"
    "    else:\n"
    "        abc_bar_count = 999999\n"
    "\n"
    "    previous_low = low_values[i - 1] if i > 0 else np.nan\n"
    "    previous_high = high_values[i - 1] if i > 0 else np.nan\n"
    "    lbounced = False\n"
    "    sbounced = False\n"
    "    for ma in ma_series:\n"
    "        if not np.isfinite(ma[i]):\n"
    "            continue\n"
    "        if i > 0 and np.isfinite(previous_low):\n"
    "            lbounced = lbounced or (\n"
    "                min(low_values[i], previous_low) <= ma[i]\n"
    "                and close_values[i] > ma[i]\n"
    "                and close_values[i] > open_values[i]\n"
    "            )\n"
    "        if i > 0 and np.isfinite(previous_high):\n"
    "            sbounced = sbounced or (\n"
    "                max(high_values[i], previous_high) >= ma[i]\n"
    "                and close_values[i] < ma[i]\n"
    "                and close_values[i] < open_values[i]\n"
    "            )\n"
    "\n"
    "    last_zz_point = zz_points[-1][1] if zz_points else np.nan\n"
    "    long_signal = (\n"
    "        trend[i] == 1\n"
    "        and abc_bar_count <= 6\n"
    "        and abc_active\n"
    "        and abc_is_bullish\n"
    "        and lbounced\n"
    "        and np.isfinite(last_zz_point)\n"
    "        and low_values[i] >= last_zz_point\n"
    "    )\n"
    "    short_signal = (\n"
    "        trend[i] == -1\n"
    "        and abc_bar_count <= 6\n"
    "        and abc_active\n"
    "        and not abc_is_bullish\n"
    "        and sbounced\n"
    "        and np.isfinite(last_zz_point)\n"
    "        and high_values[i] <= last_zz_point\n"
    "    )\n"
    "    if long_signal:\n"
    '        abc_events[i] = "Long"\n'
    "    elif short_signal:\n"
    '        abc_events[i] = "Short"\n'
    "\n"
    "\n"
    "def _plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    "zz_output = _plot_list(zz_plot) if showzigzag else [None] * n\n"
    "abc_output = _plot_list(abc_line) if showabc else [None] * n\n"
    "long_marks = [\n"
    "    float(low_values[i]) * 0.995\n"
    '    if abc_events[i] == "Long" and np.isfinite(low_values[i])\n'
    "    else None\n"
    "    for i in range(n)\n"
    "]\n"
    "short_marks = [\n"
    "    float(high_values[i]) * 1.005\n"
    '    if abc_events[i] == "Short" and np.isfinite(high_values[i])\n'
    "    else None\n"
    "    for i in range(n)\n"
    "]\n"
    "abc_event_marks = [\n"
    '    float(close_values[i]) if abc_events[i] in ("ABC Bull", "ABC Bear") else None\n'
    "    for i in range(n)\n"
    "]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "ZigZag", "data": zz_output, "color": "#9C27B0", "overlay": True},\n'
    '        {"name": "ABC Line", "data": abc_output, "color": "#FFB300", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "ABC", "data": abc_event_marks, "color": "#42A5F5"},\n'
    '        {"type": "buy", "text": "Long", "data": long_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "Short", "data": short_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "metadata": {\n'
    '        "trend": [int(value) for value in trend],\n'
    '        "abc": [int(value) for value in abc_state],\n'
    '        "abc_rate": _plot_list(abc_rate_plot),\n'
    '        "zigzag_direction": [int(value) for value in zz_direction_plot],\n'
    '        "zigzag_events": abc_point_events,\n'
    '        "abc_events": abc_events,\n'
    '        "upper_count": [int(value) for value in upper_count],\n'
    '        "lower_count": [int(value) for value in lower_count],\n'
    '        "causal": True,\n'
    '        "chart_only": True,\n'
    '        "params": {\n'
    '            "prd": prd,\n'
    '            "fiboup": fiboup,\n'
    '            "fibodn": fibodn,\n'
    '            "errorrate": errorrate,\n'
    '            "src_ma": src_ma,\n'
    '            "showabc": showabc,\n'
    '            "keepabc": keepabc,\n'
    '            "showcloud": showcloud,\n'
    '            "showzigzag": showzigzag,\n'
    "        },\n"
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
