"""Chart-only source for the two_b_reversal_pattern indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] 2B Reversal Pattern (Expo)\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# A causal two-stage reversal detector: price first breaks a confirmed swing,\n"
    "# then reverses through the breakout candle's opposite extreme. Signals are\n"
    "# visual only and never place trades.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] 2B Reversal Pattern (Expo)"\n'
    "my_indicator_description = (\n"
    '    "Confirmed swing false-break reversals with causal pending levels and chart-only signals."\n'
    ")\n"
    "\n"
    "# @param prd int 20 Swing pivot period range=2:100:1\n"
    "# @param max_break int 10 Maximum confirmation window; zero means unlimited range=0:200:1\n"
    "# @param min_break int 3 Minimum bars before reversal confirmation range=1:100:1\n"
    "# @param setup_src string close Source for the first breakout: close or wick\n"
    "# @param confirm_src string close Source for the reversal confirmation: close or wick\n"
    "# @param cancel_on_invalid_cross bool True Cancel a pending setup after its window expires\n"
    "# @param allow_multiple bool False Keep multiple pending setups\n"
    "# @param signal_mode string Custom Preset: Custom, Original, Relaxed, or Aggressive\n"
    "# @param bUp string #6ce5a0 Upward 2B line color\n"
    "# @param bDn string #f23645 Downward 2B line color\n"
    "# @param pCol string #00FFFF Swing and pending level color\n"
    "\n"
    'prd = max(2, int(params.get("prd", 20)))\n'
    'max_break = max(0, int(params.get("max_break", 10)))\n'
    'min_break = max(1, int(params.get("min_break", 3)))\n'
    'setup_src = str(params.get("setup_src", "close")).strip().lower()\n'
    'confirm_src = str(params.get("confirm_src", "close")).strip().lower()\n'
    'cancel_on_invalid_cross = params.get("cancel_on_invalid_cross", True)\n'
    'allow_multiple = params.get("allow_multiple", False)\n'
    'signal_mode = str(params.get("signal_mode", "Custom")).strip().lower()\n'
    'b_up = str(params.get("bUp", "#6ce5a0"))\n'
    'b_down = str(params.get("bDn", "#f23645"))\n'
    'pivot_color = str(params.get("pCol", "#00FFFF"))\n'
    "\n"
    "\n"
    "def as_bool(value, default=True):\n"
    "    if value is None:\n"
    "        return default\n"
    '    if str(value).strip().lower() in ("false", "0", "no", "off"):\n'
    "        return False\n"
    '    if str(value).strip().lower() in ("true", "1", "yes", "on"):\n'
    "        return True\n"
    "    return bool(value)\n"
    "\n"
    "\n"
    "cancel_on_invalid_cross = as_bool(cancel_on_invalid_cross)\n"
    "allow_multiple = as_bool(allow_multiple, False)\n"
    'if signal_mode == "original":\n'
    "    min_break, max_break = 3, 10\n"
    '    setup_src, confirm_src = "close", "close"\n'
    "    cancel_on_invalid_cross, allow_multiple = True, False\n"
    'elif signal_mode == "relaxed":\n'
    "    min_break, max_break = 1, 30\n"
    '    setup_src, confirm_src = "close", "close"\n'
    "    cancel_on_invalid_cross, allow_multiple = True, False\n"
    'elif signal_mode == "aggressive":\n'
    "    min_break, max_break = 1, 0\n"
    '    setup_src, confirm_src = "wick", "wick"\n'
    "    cancel_on_invalid_cross, allow_multiple = False, True\n"
    'elif signal_mode != "custom":\n'
    '    raise ValueError("signal_mode must be Custom, Original, Relaxed, or Aggressive")\n'
    "\n"
    'if setup_src not in ("close", "wick"):\n'
    '    raise ValueError("setup_src must be close or wick")\n'
    'if confirm_src not in ("close", "wick"):\n'
    '    raise ValueError("confirm_src must be close or wick")\n'
    "\n"
    "\n"
    "df = df.copy()\n"
    'open_price = df["open"].astype(float) if "open" in df else df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "open_values = open_price.to_numpy(dtype=float)\n"
    "high_values = high.to_numpy(dtype=float)\n"
    "low_values = low.to_numpy(dtype=float)\n"
    "close_values = close.to_numpy(dtype=float)\n"
    "n = len(df)\n"
    "\n"
    "ph_level = np.full(n, np.nan, dtype=float)\n"
    "pl_level = np.full(n, np.nan, dtype=float)\n"
    "bo_pending = np.full(n, np.nan, dtype=float)\n"
    "bo_break_up = np.full(n, np.nan, dtype=float)\n"
    "bo_break_down = np.full(n, np.nan, dtype=float)\n"
    "long_signal = np.zeros(n, dtype=bool)\n"
    "short_signal = np.zeros(n, dtype=bool)\n"
    "\n"
    "\n"
    "def finite(value):\n"
    "    return np.isfinite(value)\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not finite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    "def crossed_up(source_now, source_before, level):\n"
    "    return (\n"
    "        finite(source_now)\n"
    "        and finite(source_before)\n"
    "        and finite(level)\n"
    "        and source_before <= level\n"
    "        and source_now > level\n"
    "    )\n"
    "\n"
    "\n"
    "def crossed_down(source_now, source_before, level):\n"
    "    return (\n"
    "        finite(source_now)\n"
    "        and finite(source_before)\n"
    "        and finite(level)\n"
    "        and source_before >= level\n"
    "        and source_now < level\n"
    "    )\n"
    "\n"
    "\n"
    '# Each pending entry describes the first break. kind="high" means price broke\n'
    '# a swing high and must later fall through the breakout candle low; kind="low"\n'
    "# is the symmetric bullish false break.\n"
    "pending = []\n"
    "last_ph = np.nan\n"
    "last_pl = np.nan\n"
    "last_setup_up = np.nan\n"
    "last_setup_down = np.nan\n"
    "last_confirm_up = np.nan\n"
    "last_confirm_down = np.nan\n"
    "\n"
    "for i in range(n):\n"
    "    pivot_index = i - prd\n"
    "    if pivot_index >= prd:\n"
    "        pivot_high = high_values[pivot_index]\n"
    "        pivot_low = low_values[pivot_index]\n"
    "        left_high = high_values[pivot_index - prd:pivot_index]\n"
    "        right_high = high_values[pivot_index + 1:i + 1]\n"
    "        left_low = low_values[pivot_index - prd:pivot_index]\n"
    "        right_low = low_values[pivot_index + 1:i + 1]\n"
    "        if (\n"
    "            finite(pivot_high)\n"
    "            and len(left_high) == prd\n"
    "            and len(right_high) == prd\n"
    "            and np.all(np.isfinite(left_high))\n"
    "            and np.all(np.isfinite(right_high))\n"
    "            and pivot_high > np.max(left_high)\n"
    "            and pivot_high > np.max(right_high)\n"
    "        ):\n"
    "            last_ph = float(pivot_high)\n"
    "        if (\n"
    "            finite(pivot_low)\n"
    "            and len(left_low) == prd\n"
    "            and len(right_low) == prd\n"
    "            and np.all(np.isfinite(left_low))\n"
    "            and np.all(np.isfinite(right_low))\n"
    "            and pivot_low < np.min(left_low)\n"
    "            and pivot_low < np.min(right_low)\n"
    "        ):\n"
    "            last_pl = float(pivot_low)\n"
    "\n"
    "    ph_level[i] = last_ph if finite(last_ph) else np.nan\n"
    "    pl_level[i] = last_pl if finite(last_pl) else np.nan\n"
    "\n"
    '    if setup_src == "wick":\n'
    "        setup_up_now, setup_up_before = high_values[i], last_setup_up\n"
    "        setup_down_now, setup_down_before = low_values[i], last_setup_down\n"
    "    else:\n"
    "        setup_up_now, setup_up_before = close_values[i], last_setup_up\n"
    "        setup_down_now, setup_down_before = close_values[i], last_setup_down\n"
    "\n"
    "    if finite(last_ph) and crossed_up(setup_up_now, setup_up_before, last_ph):\n"
    "        entry = {\n"
    '            "kind": "high",\n'
    '            "bar": i,\n'
    '            "level": float(low_values[i]),\n'
    '            "pivot_level": float(last_ph),\n'
    "        }\n"
    "        if allow_multiple:\n"
    "            pending.append(entry)\n"
    "        else:\n"
    "            pending = [entry]\n"
    "    if finite(last_pl) and crossed_down(setup_down_now, setup_down_before, last_pl):\n"
    "        entry = {\n"
    '            "kind": "low",\n'
    '            "bar": i,\n'
    '            "level": float(high_values[i]),\n'
    '            "pivot_level": float(last_pl),\n'
    "        }\n"
    "        if allow_multiple:\n"
    "            pending.append(entry)\n"
    "        else:\n"
    "            pending = [entry]\n"
    "\n"
    "    if pending:\n"
    '        bo_pending[i] = float(pending[-1]["level"])\n'
    "\n"
    '    if confirm_src == "wick":\n'
    "        confirm_up_now, confirm_up_before = high_values[i], last_confirm_up\n"
    "        confirm_down_now, confirm_down_before = low_values[i], last_confirm_down\n"
    "    else:\n"
    "        confirm_up_now, confirm_up_before = close_values[i], last_confirm_up\n"
    "        confirm_down_now, confirm_down_before = close_values[i], last_confirm_down\n"
    "\n"
    "    remaining = []\n"
    "    for entry in pending:\n"
    '        age = i - int(entry["bar"])\n'
    "        if age < min_break:\n"
    "            remaining.append(entry)\n"
    "            continue\n"
    "        in_window = max_break == 0 or age <= max_break\n"
    "        if not in_window:\n"
    "            # Expiration is causal: no previous pending line is removed from\n"
    "            # the returned array, only future bars stop displaying it.\n"
    "            continue\n"
    "\n"
    '        is_short_reversal = entry["kind"] == "high"\n'
    "        confirmed = (\n"
    '            crossed_down(confirm_down_now, confirm_down_before, entry["level"])\n'
    "            if is_short_reversal\n"
    '            else crossed_up(confirm_up_now, confirm_up_before, entry["level"])\n'
    "        )\n"
    "        if confirmed:\n"
    "            if is_short_reversal:\n"
    '                bo_break_down[i] = float(entry["level"])\n'
    "                short_signal[i] = True\n"
    "            else:\n"
    '                bo_break_up[i] = float(entry["level"])\n'
    "                long_signal[i] = True\n"
    "            continue\n"
    "\n"
    "        if cancel_on_invalid_cross and max_break > 0 and age == max_break:\n"
    "            continue\n"
    "        remaining.append(entry)\n"
    "    pending = remaining\n"
    "\n"
    "    last_setup_up = setup_up_now if finite(setup_up_now) else last_setup_up\n"
    "    last_setup_down = setup_down_now if finite(setup_down_now) else last_setup_down\n"
    "    last_confirm_up = confirm_up_now if finite(confirm_up_now) else last_confirm_up\n"
    "    last_confirm_down = confirm_down_now if finite(confirm_down_now) else last_confirm_down\n"
    "\n"
    "long_marks = [\n"
    "    float(low_values[i]) * 0.995 if long_signal[i] and finite(low_values[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "short_marks = [\n"
    "    float(high_values[i]) * 1.005 if short_signal[i] and finite(high_values[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Swing High Level", "data": plot_list(ph_level), "color": pivot_color, "overlay": True, "style": "dashed"},\n'
    '        {"name": "Swing Low Level", "data": plot_list(pl_level), "color": pivot_color, "overlay": True, "style": "dashed"},\n'
    '        {"name": "Pending Breakout", "data": plot_list(bo_pending), "color": pivot_color, "overlay": True, "style": "dashed"},\n'
    '        {"name": "2B Break Up", "data": plot_list(bo_break_up), "color": b_up, "overlay": True},\n'
    '        {"name": "2B Break Down", "data": plot_list(bo_break_down), "color": b_down, "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "2B", "data": long_marks, "color": b_up},\n'
    '        {"type": "sell", "text": "2B", "data": short_marks, "color": b_down},\n'
    "    ],\n"
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "prd": prd,\n'
    '        "max_break": max_break,\n'
    '        "min_break": min_break,\n'
    '        "setup_src": setup_src,\n'
    '        "confirm_src": confirm_src,\n'
    '        "cancel_on_invalid_cross": cancel_on_invalid_cross,\n'
    '        "allow_multiple": allow_multiple,\n'
    '        "signal_mode": signal_mode,\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
