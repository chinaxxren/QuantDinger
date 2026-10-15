"""Chart-only source for the twin_optimized_trend_tracker indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Twin Optimized Trend Tracker\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal moving-average trend tracker with twin OTT lines.  The original\n"
    "# TradingView presentation offsets the twin lines by two bars; this source\n"
    "# preserves that visual delay without reading future bars.\n"
    "# Signals are chart markers only and never submit or manage orders.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Twin Optimized Trend Tracker"\n'
    "my_indicator_description = (\n"
    '    "Twin optimized trend tracker with selectable moving averages, causal "\n'
    '    "trailing stops, and chart-only reversal markers."\n'
    ")\n"
    "\n"
    "# @param length int 40 Moving-average length range=1:200:1\n"
    "# @param percent float 1.0 OTT percentage range=0.01:20.0:0.01\n"
    "# @param coeff float 0.001 Twin-line coefficient range=0.0:0.1:0.0001\n"
    "# @param ma_type string VAR Moving average: SMA, EMA, WMA, TMA, VAR, WWMA, ZLEMA, TSF\n"
    "# @param var_length int 9 CMO lookback for VAR range=2:100:1\n"
    "# @param source string close Price source: close, hl2, hlc3, or ohlc4\n"
    "# @param ma_seed string first Recursive seed: first or zero\n"
    "# @param show_support bool True Show the moving-average support line\n"
    "# @param show_signals bool True Show buy/sell chart markers\n"
    "# @param qty int 1 Compatibility quantity (visual only)\n"
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
    "def finite_or_none(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    "def selected_source(frame, name):\n"
    '    normalized = str(name or "close").strip().lower()\n'
    "    columns = {\n"
    '        "close": frame["close"].astype(float).to_numpy(copy=True),\n'
    '        "hl2": ((frame["high"].astype(float) + frame["low"].astype(float)) / 2.0).to_numpy(copy=True),\n'
    '        "hlc3": ((frame["high"].astype(float) + frame["low"].astype(float) + frame["close"].astype(float)) / 3.0).to_numpy(copy=True),\n'
    '        "ohlc4": ((frame["open"].astype(float) + frame["high"].astype(float) + frame["low"].astype(float) + frame["close"].astype(float)) / 4.0).to_numpy(copy=True),\n'
    "    }\n"
    '    return columns.get(normalized, columns["close"]), normalized if normalized in columns else "close"\n'
    "\n"
    "\n"
    "def rolling_sma(values, period):\n"
    "    result = np.full(len(values), np.nan, dtype=float)\n"
    "    running = 0.0\n"
    "    count = 0\n"
    "    for i, value in enumerate(values):\n"
    "        if np.isfinite(value):\n"
    "            running += float(value)\n"
    "            count += 1\n"
    "        if i >= period:\n"
    "            old = values[i - period]\n"
    "            if np.isfinite(old):\n"
    "                running -= float(old)\n"
    "                count -= 1\n"
    "        if i >= period - 1 and count == period:\n"
    "            result[i] = running / period\n"
    "    return result\n"
    "\n"
    "\n"
    "def recursive_ema(values, period, seed_mode, alpha_override=None):\n"
    "    result = np.full(len(values), np.nan, dtype=float)\n"
    "    alpha = float(alpha_override if alpha_override is not None else 2.0 / (period + 1.0))\n"
    "    previous = 0.0\n"
    "    started = False\n"
    "    for i, value in enumerate(values):\n"
    "        if not np.isfinite(value):\n"
    "            if started:\n"
    "                result[i] = previous\n"
    "            continue\n"
    "        if not started:\n"
    '            if seed_mode == "zero":\n'
    "                previous = alpha * float(value)\n"
    "            else:\n"
    "                previous = float(value)\n"
    "            started = True\n"
    "        else:\n"
    "            previous = alpha * float(value) + (1.0 - alpha) * previous\n"
    "        result[i] = previous\n"
    "    return result\n"
    "\n"
    "\n"
    "def wma(values, period):\n"
    "    result = np.full(len(values), np.nan, dtype=float)\n"
    "    weights = np.arange(1, period + 1, dtype=float)\n"
    "    denominator = float(np.sum(weights))\n"
    "    for i in range(period - 1, len(values)):\n"
    "        window = values[i - period + 1 : i + 1]\n"
    "        if np.all(np.isfinite(window)):\n"
    "            result[i] = float(np.dot(window, weights) / denominator)\n"
    "    return result\n"
    "\n"
    "\n"
    "def tsf(values, period):\n"
    "    result = np.full(len(values), np.nan, dtype=float)\n"
    "    x = np.arange(period, dtype=float)\n"
    "    x_mean = float(np.mean(x))\n"
    "    denominator = float(np.sum((x - x_mean) ** 2))\n"
    "    for i in range(period - 1, len(values)):\n"
    "        window = values[i - period + 1 : i + 1]\n"
    "        if not np.all(np.isfinite(window)) or denominator == 0.0:\n"
    "            continue\n"
    "        y_mean = float(np.mean(window))\n"
    "        slope = float(np.sum((x - x_mean) * (window - y_mean)) / denominator)\n"
    "        intercept = y_mean - slope * x_mean\n"
    "        result[i] = intercept + slope * float(period - 1)\n"
    "    return result\n"
    "\n"
    "\n"
    "def var_average(values, period, cmo_period, seed_mode):\n"
    "    delta = np.full(len(values), np.nan, dtype=float)\n"
    "    if len(values) > 1:\n"
    "        delta[1:] = values[1:] - values[:-1]\n"
    "    up = np.where(np.isfinite(delta) & (delta > 0.0), delta, 0.0)\n"
    "    down = np.where(np.isfinite(delta) & (delta < 0.0), -delta, 0.0)\n"
    "    up_sum = rolling_sma(up, cmo_period) * cmo_period\n"
    "    down_sum = rolling_sma(down, cmo_period) * cmo_period\n"
    "    denominator = up_sum + down_sum\n"
    "    cmo = np.divide(\n"
    "        up_sum - down_sum,\n"
    "        denominator,\n"
    "        out=np.zeros(len(values), dtype=float),\n"
    "        where=np.isfinite(denominator) & (denominator > 0.0),\n"
    "    )\n"
    "    result = np.full(len(values), np.nan, dtype=float)\n"
    "    previous = 0.0\n"
    "    started = False\n"
    "    alpha_base = 2.0 / (period + 1.0)\n"
    "    for i, value in enumerate(values):\n"
    "        if not np.isfinite(value):\n"
    "            if started:\n"
    "                result[i] = previous\n"
    "            continue\n"
    "        if not started:\n"
    '            previous = 0.0 if seed_mode == "zero" else float(value)\n'
    "            started = True\n"
    "        adaptive_alpha = float(np.clip(alpha_base * abs(cmo[i]), 0.0, 1.0))\n"
    "        previous = adaptive_alpha * float(value) + (1.0 - adaptive_alpha) * previous\n"
    "        result[i] = previous\n"
    "    return result\n"
    "\n"
    "\n"
    'length = clamp_int(params.get("length", 40), 40, 1, 200)\n'
    'percent = clamp_float(params.get("percent", 1.0), 1.0, 0.01, 20.0)\n'
    'coeff = clamp_float(params.get("coeff", 0.001), 0.001, 0.0, 0.1)\n'
    'var_length = clamp_int(params.get("var_length", 9), 9, 2, 100)\n'
    'ma_type = str(params.get("ma_type", "VAR") or "VAR").strip().upper()\n'
    'if ma_type not in ("SMA", "EMA", "WMA", "TMA", "VAR", "WWMA", "ZLEMA", "TSF"):\n'
    '    ma_type = "VAR"\n'
    'ma_seed = str(params.get("ma_seed", "first") or "first").strip().lower()\n'
    'if ma_seed not in ("first", "zero"):\n'
    '    ma_seed = "first"\n'
    'show_support = as_bool(params.get("show_support", True), True)\n'
    'show_signals = as_bool(params.get("show_signals", True), True)\n'
    'qty = clamp_int(params.get("qty", 1), 1, 1, 1000000)\n'
    'prices, source_name = selected_source(df, params.get("source", "close"))\n'
    "n = len(prices)\n"
    "\n"
    'if ma_type == "SMA":\n'
    "    ma_avg = rolling_sma(prices, length)\n"
    'elif ma_type == "EMA":\n'
    "    ma_avg = recursive_ema(prices, length, ma_seed)\n"
    'elif ma_type == "WMA":\n'
    "    ma_avg = wma(prices, length)\n"
    'elif ma_type == "TMA":\n'
    "    ma_avg = rolling_sma(rolling_sma(prices, max(1, (length + 1) // 2)), max(1, length // 2 + 1))\n"
    'elif ma_type == "VAR":\n'
    "    ma_avg = var_average(prices, length, var_length, ma_seed)\n"
    'elif ma_type == "WWMA":\n'
    "    ma_avg = recursive_ema(prices, length, ma_seed, alpha_override=1.0 / length)\n"
    'elif ma_type == "ZLEMA":\n'
    "    lag = max(1, (length - 1) // 2)\n"
    "    adjusted = prices.copy()\n"
    "    for i in range(len(adjusted)):\n"
    "        if i >= lag and np.isfinite(prices[i]) and np.isfinite(prices[i - lag]):\n"
    "            adjusted[i] = prices[i] + (prices[i] - prices[i - lag])\n"
    "        elif not np.isfinite(prices[i]):\n"
    "            adjusted[i] = np.nan\n"
    "    ma_avg = recursive_ema(adjusted, length, ma_seed)\n"
    "else:\n"
    "    ma_avg = tsf(prices, length)\n"
    "\n"
    "# OTT stop rails are ratcheted one bar at a time.  No future data is used.\n"
    "long_stop = np.full(n, np.nan, dtype=float)\n"
    "short_stop = np.full(n, np.nan, dtype=float)\n"
    "direction = np.full(n, np.nan, dtype=float)\n"
    "mt = np.full(n, np.nan, dtype=float)\n"
    "ott = np.full(n, np.nan, dtype=float)\n"
    "\n"
    "for i in range(n):\n"
    "    if not np.isfinite(ma_avg[i]):\n"
    "        if i:\n"
    "            direction[i] = direction[i - 1]\n"
    "        continue\n"
    "    long_stop[i] = ma_avg[i] * (1.0 - percent / 100.0)\n"
    "    short_stop[i] = ma_avg[i] * (1.0 + percent / 100.0)\n"
    "    if i == 0 or not np.isfinite(direction[i - 1]):\n"
    "        direction[i] = 1.0\n"
    "    else:\n"
    "        previous_long = long_stop[i - 1]\n"
    "        previous_short = short_stop[i - 1]\n"
    "        if np.isfinite(previous_long) and ma_avg[i] > previous_long:\n"
    "            long_stop[i] = max(long_stop[i], previous_long)\n"
    "        if np.isfinite(previous_short) and ma_avg[i] < previous_short:\n"
    "            short_stop[i] = min(short_stop[i], previous_short)\n"
    "        if direction[i - 1] < 0 and ma_avg[i] > previous_short:\n"
    "            direction[i] = 1.0\n"
    "        elif direction[i - 1] > 0 and ma_avg[i] < previous_long:\n"
    "            direction[i] = -1.0\n"
    "        else:\n"
    "            direction[i] = direction[i - 1]\n"
    "    mt[i] = long_stop[i] if direction[i] > 0 else short_stop[i]\n"
    "    if np.isfinite(mt[i]):\n"
    "        adjustment = (200.0 + percent) / 200.0 if ma_avg[i] > mt[i] else (200.0 - percent) / 200.0\n"
    "        ott[i] = mt[i] * adjustment\n"
    "\n"
    "# The two twin lines are intentionally delayed by two completed bars.  This is\n"
    "# equivalent to raw[i - 2] on the current bar and remains strictly causal.\n"
    "ott_up_raw = ott * (1.0 + coeff)\n"
    "ott_dn_raw = ott * (1.0 - coeff)\n"
    "ott_up = np.full(n, np.nan, dtype=float)\n"
    "ott_dn = np.full(n, np.nan, dtype=float)\n"
    "if n > 2:\n"
    "    ott_up[2:] = ott_up_raw[:-2]\n"
    "    ott_dn[2:] = ott_dn_raw[:-2]\n"
    "\n"
    "previous_ma = np.concatenate(([np.nan], ma_avg[:-1]))\n"
    "previous_up = np.concatenate(([np.nan], ott_up[:-1]))\n"
    "previous_dn = np.concatenate(([np.nan], ott_dn[:-1]))\n"
    "buy = np.isfinite(ma_avg) & np.isfinite(ott_up) & np.isfinite(previous_ma) & np.isfinite(previous_up) & (previous_ma <= previous_up) & (ma_avg > ott_up)\n"
    "sell = np.isfinite(ma_avg) & np.isfinite(ott_dn) & np.isfinite(previous_ma) & np.isfinite(previous_dn) & (previous_ma >= previous_dn) & (ma_avg < ott_dn)\n"
    "\n"
    'low = df["low"].astype(float).to_numpy(copy=True)\n'
    'high = df["high"].astype(float).to_numpy(copy=True)\n'
    "buy_marks = [float(low[i]) * 0.995 if show_signals and buy[i] and np.isfinite(low[i]) else None for i in range(n)]\n"
    "sell_marks = [float(high[i]) * 1.005 if show_signals and sell[i] and np.isfinite(high[i]) else None for i in range(n)]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "MAvg", "data": finite_or_none(ma_avg) if show_support else [None] * n, "color": "#0585E1", "overlay": True},\n'
    '        {"name": "OTT Upper", "data": finite_or_none(ott_up), "color": "#008000", "overlay": True},\n'
    '        {"name": "OTT Lower", "data": finite_or_none(ott_dn), "color": "#FF0000", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "Buy", "data": buy_marks, "color": "#00C853"},\n'
    '        {"type": "sell", "text": "Sell", "data": sell_marks, "color": "#FF0000"},\n'
    "    ],\n"
    '    "layers": [],\n'
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "ma_type": ma_type,\n'
    '        "length": length,\n'
    '        "percent": percent,\n'
    '        "coeff": coeff,\n'
    '        "var_length": var_length,\n'
    '        "source": source_name,\n'
    '        "ma_seed": ma_seed,\n'
    '        "show_support": show_support,\n'
    '        "show_signals": show_signals,\n'
    '        "qty": qty,\n'
    '        "ott": finite_or_none(ott),\n'
    '        "ott_up_raw": finite_or_none(ott_up_raw),\n'
    '        "ott_dn_raw": finite_or_none(ott_dn_raw),\n'
    '        "long_stop": finite_or_none(long_stop),\n'
    '        "short_stop": finite_or_none(short_stop),\n'
    '        "direction": finite_or_none(direction),\n'
    '        "buy_label": buy_marks,\n'
    '        "sell_label": sell_marks,\n'
    '        "long_signal": [bool(value) for value in buy],\n'
    '        "short_signal": [bool(value) for value in sell],\n'
    "    },\n"
    "}\n"
)
