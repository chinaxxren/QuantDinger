"""Chart-only source for the smt_divergences indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] SMT Divergences\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal swing-high/swing-low divergence detector. Optional comparison data\n"
    "# can be supplied through params; without it the indicator still exposes the\n"
    "# primary symbol's confirmed swing levels but does not fabricate SMT signals.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] SMT Divergences"\n'
    "my_indicator_description = (\n"
    '    "Confirmed swing divergence detector with optional comparison series and "\n'
    '    "chart-only SMT markers."\n'
    ")\n"
    "\n"
    "# @param length int 3 Pivot lookback and confirmation width range=2:20:1\n"
    "# @param use_sym1 bool True Enable comparison series 1\n"
    "# @param sym1 string None Comparison series 1 identifier or payload\n"
    "# @param use_sym2 bool True Enable comparison series 2\n"
    "# @param sym2 string None Comparison series 2 identifier or payload\n"
    "# @param bull_color string #ff1100 Swing-high divergence color\n"
    "# @param bear_color string #2157f3 Swing-low divergence color\n"
    "# @param show_dash bool False Retained for source compatibility\n"
    "\n"
    'length = max(2, min(20, int(params.get("length", 3))))\n'
    'use_sym1 = bool(params.get("use_sym1", True))\n'
    'use_sym2 = bool(params.get("use_sym2", True))\n'
    'bull_color = str(params.get("bull_color", "#ff1100"))\n'
    'bear_color = str(params.get("bear_color", "#2157f3"))\n'
    "\n"
    "# Comparison K-lines are optional because the chart-indicator execution\n"
    "# contract currently receives one symbol's bars. Integrations that have\n"
    "# already loaded comparison data may pass either:\n"
    '#   params["sym1"] = {"high": [...], "low": [...], "close": [...]}\n'
    '# or params["sym1_high"], params["sym1_low"], params["sym1_close"] arrays.\n'
    "def _as_array(value):\n"
    "    if value is None or isinstance(value, str):\n"
    "        return None\n"
    "    try:\n"
    "        values = np.asarray(value, dtype=float).reshape(-1)\n"
    "    except Exception:\n"
    "        return None\n"
    "    return values if len(values) else None\n"
    "\n"
    "\n"
    "def _comparison_array(name, field, n):\n"
    "    payload = params.get(name)\n"
    "    value = None\n"
    "    if isinstance(payload, dict):\n"
    "        value = payload.get(field)\n"
    '        if value is None and field != "close":\n'
    '            value = payload.get("close")\n'
    "    if value is None:\n"
    '        value = params.get(name + "_" + field)\n'
    "    values = _as_array(value)\n"
    "    if values is None:\n"
    "        return None\n"
    "    # Comparison data is aligned by the tail, matching the MiniBT adapter.\n"
    "    aligned = np.full(n, np.nan, dtype=float)\n"
    "    if len(values) >= n:\n"
    "        aligned[:] = values[-n:]\n"
    "    else:\n"
    "        aligned[n - len(values):] = values\n"
    "    return aligned\n"
    "\n"
    "\n"
    "df = df.copy()\n"
    'open_price = df["open"].astype(float).to_numpy(dtype=float)\n'
    'high = df["high"].astype(float).to_numpy(dtype=float)\n'
    'low = df["low"].astype(float).to_numpy(dtype=float)\n'
    'close = df["close"].astype(float).to_numpy(dtype=float)\n'
    "n = len(df)\n"
    "\n"
    "\n"
    "def _confirmed_pivots(values, want_high):\n"
    '    """Return pivot values at their causal right-side confirmation bar."""\n'
    "    events = np.full(n, np.nan, dtype=float)\n"
    "    pivot_indexes = np.full(n, -1, dtype=int)\n"
    "    for confirmation in range(2 * length, n):\n"
    "        pivot = confirmation - length\n"
    "        left = values[pivot - length:pivot]\n"
    "        right = values[pivot + 1:confirmation + 1]\n"
    "        candidate = values[pivot]\n"
    "        if not np.isfinite(candidate) or not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):\n"
    "            continue\n"
    "        if want_high:\n"
    "            valid = candidate >= np.max(left) and candidate > np.max(right)\n"
    "        else:\n"
    "            valid = candidate <= np.min(left) and candidate < np.min(right)\n"
    "        if valid:\n"
    "            events[confirmation] = candidate\n"
    "            pivot_indexes[confirmation] = pivot\n"
    "    return events, pivot_indexes\n"
    "\n"
    "\n"
    "def _fixnan(events):\n"
    "    values = np.full(n, np.nan, dtype=float)\n"
    "    last = np.nan\n"
    "    for i in range(n):\n"
    "        if np.isfinite(events[i]):\n"
    "            last = events[i]\n"
    "        values[i] = last\n"
    "    return values\n"
    "\n"
    "\n"
    "primary_high_events, primary_high_indexes = _confirmed_pivots(high, True)\n"
    "primary_low_events, primary_low_indexes = _confirmed_pivots(low, False)\n"
    "pivot_high = _fixnan(primary_high_events)\n"
    "pivot_low = _fixnan(primary_low_events)\n"
    "\n"
    "div_high = np.full(n, np.nan, dtype=float)\n"
    "div_low = np.full(n, np.nan, dtype=float)\n"
    "high_source_tag = np.zeros(n, dtype=int)\n"
    "low_source_tag = np.zeros(n, dtype=int)\n"
    "smt_high = np.zeros(n, dtype=int)\n"
    "smt_low = np.zeros(n, dtype=int)\n"
    "\n"
    "\n"
    "def _process_comparison(bit, name):\n"
    '    comparison_high = _comparison_array(name, "high", n)\n'
    '    comparison_low = _comparison_array(name, "low", n)\n'
    '    comparison_close = _comparison_array(name, "close", n)\n'
    "    if comparison_high is None and comparison_close is not None:\n"
    "        comparison_high = comparison_close.copy()\n"
    "    if comparison_low is None and comparison_close is not None:\n"
    "        comparison_low = comparison_close.copy()\n"
    "    if comparison_high is None or comparison_low is None:\n"
    "        return False\n"
    "\n"
    "    comparison_high_events, _ = _confirmed_pivots(comparison_high, True)\n"
    "    comparison_low_events, _ = _confirmed_pivots(comparison_low, False)\n"
    "\n"
    "    previous_primary_high = np.nan\n"
    "    previous_comparison_high = np.nan\n"
    "    previous_primary_low = np.nan\n"
    "    previous_comparison_low = np.nan\n"
    "    for i in range(n):\n"
    "        primary_high_value = primary_high_events[i]\n"
    "        comparison_high_value = comparison_high_events[i]\n"
    "        if np.isfinite(primary_high_value):\n"
    "            if np.isfinite(comparison_high_value):\n"
    "                if (\n"
    "                    np.isfinite(previous_primary_high)\n"
    "                    and np.isfinite(previous_comparison_high)\n"
    "                    and (primary_high_value - previous_primary_high)\n"
    "                    * (comparison_high_value - previous_comparison_high) < 0.0\n"
    "                ):\n"
    "                    div_high[i] = primary_high_value\n"
    "                    high_source_tag[i] += bit\n"
    "                    smt_high[i] += 1\n"
    "                previous_primary_high = primary_high_value\n"
    "                previous_comparison_high = comparison_high_value\n"
    "            else:\n"
    "                # Do not pair a primary pivot with a stale comparison pivot.\n"
    "                previous_primary_high = np.nan\n"
    "                previous_comparison_high = np.nan\n"
    "\n"
    "        primary_low_value = primary_low_events[i]\n"
    "        comparison_low_value = comparison_low_events[i]\n"
    "        if np.isfinite(primary_low_value):\n"
    "            if np.isfinite(comparison_low_value):\n"
    "                if (\n"
    "                    np.isfinite(previous_primary_low)\n"
    "                    and np.isfinite(previous_comparison_low)\n"
    "                    and (primary_low_value - previous_primary_low)\n"
    "                    * (comparison_low_value - previous_comparison_low) < 0.0\n"
    "                ):\n"
    "                    div_low[i] = primary_low_value\n"
    "                    low_source_tag[i] += bit\n"
    "                    smt_low[i] += 1\n"
    "                previous_primary_low = primary_low_value\n"
    "                previous_comparison_low = comparison_low_value\n"
    "            else:\n"
    "                previous_primary_low = np.nan\n"
    "                previous_comparison_low = np.nan\n"
    "    return True\n"
    "\n"
    "\n"
    "comparison_names = []\n"
    'if use_sym1 and _process_comparison(1, "sym1"):\n'
    '    comparison_names.append(str(params.get("sym1_name", params.get("sym1", "sym1"))))\n'
    'if use_sym2 and _process_comparison(2, "sym2"):\n'
    '    comparison_names.append(str(params.get("sym2_name", params.get("sym2", "sym2"))))\n'
    "\n"
    "# The first comparison pass writes the divergence endpoint; subsequent passes\n"
    "# add another source tag and count without changing the endpoint value.\n"
    "# Rebuild source-specific counters from the accumulated tags so both symbols\n"
    "# remain visible when they diverge on the same confirmation bar.\n"
    "for i in range(n):\n"
    "    smt_high[i] = 1 if high_source_tag[i] else 0\n"
    "    smt_low[i] = 1 if low_source_tag[i] else 0\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    "def int_list(values):\n"
    "    return [int(value) if value else None for value in values]\n"
    "\n"
    'high_text = "SMT High"\n'
    'low_text = "SMT Low"\n'
    "if comparison_names:\n"
    '    high_text = "SMT High: " + " | ".join(comparison_names)\n'
    '    low_text = "SMT Low: " + " | ".join(comparison_names)\n'
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Pivot High", "data": plot_list(pivot_high), "color": bull_color, "overlay": True},\n'
    '        {"name": "Pivot Low", "data": plot_list(pivot_low), "color": bear_color, "overlay": True},\n'
    '        {"name": "SMT High Divergence", "data": plot_list(div_high), "color": bull_color, "overlay": True, "width": 1.5},\n'
    '        {"name": "SMT Low Divergence", "data": plot_list(div_low), "color": bear_color, "overlay": True, "width": 1.5},\n'
    "    ],\n"
    '    "signals": [\n'
    "        {\n"
    '            "type": "buy",\n'
    '            "text": low_text,\n'
    '            "data": [float(low[i]) if low_source_tag[i] and np.isfinite(low[i]) else None for i in range(n)],\n'
    '            "color": bear_color,\n'
    "        },\n"
    "        {\n"
    '            "type": "sell",\n'
    '            "text": high_text,\n'
    '            "data": [float(high[i]) if high_source_tag[i] and np.isfinite(high[i]) else None for i in range(n)],\n'
    '            "color": bull_color,\n'
    "        },\n"
    "    ],\n"
    '    "metadata": {\n'
    '        "smt_high": int_list(smt_high),\n'
    '        "smt_low": int_list(smt_low),\n'
    '        "div_high_tag": int_list(high_source_tag),\n'
    '        "div_low_tag": int_list(low_source_tag),\n'
    '        "comparison_data_used": bool(comparison_names),\n'
    '        "causal": True,\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
