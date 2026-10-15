"""Chart-only source for the rsi_divergence_indicator indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] RSI Divergence Indicator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Confirmed RSI pivot divergences in a separate pane. The original MiniBT\n"
    "# page includes strategy execution, but this library source intentionally\n"
    "# keeps only causal chart lines and visual signals.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] RSI Divergence Indicator"\n'
    "my_indicator_description = (\n"
    '    "Confirmed regular and hidden RSI divergences with chart-only markers."\n'
    ")\n"
    "\n"
    "# @param length int 9 RSI lookback period range=2:100:1\n"
    "# @param source str close RSI source: close, hl2, hlc3, open, high, or low\n"
    "# @param pivot_left int 1 Pivot left lookback range=1:20:1\n"
    "# @param pivot_right int 3 Pivot right confirmation lookback range=1:20:1\n"
    "# @param range_lower int 5 Minimum distance between pivots range=1:500:1\n"
    "# @param range_upper int 60 Maximum distance between pivots range=2:1000:1\n"
    "# @param plot_bull bool True Show regular bullish divergences\n"
    "# @param plot_hidden_bull bool True Show hidden bullish divergences\n"
    "# @param plot_bear bool True Show regular bearish divergences\n"
    "# @param plot_hidden_bear bool False Show hidden bearish divergences\n"
    "\n"
    'length = max(2, int(params.get("length", params.get("len", 9))))\n'
    'source_name = str(params.get("source", params.get("src", "close"))).lower()\n'
    'pivot_left = max(1, int(params.get("pivot_left", params.get("lbL", 1))))\n'
    'pivot_right = max(1, int(params.get("pivot_right", params.get("lbR", 3))))\n'
    'range_lower = max(1, int(params.get("range_lower", 5)))\n'
    'range_upper = max(range_lower, int(params.get("range_upper", 60)))\n'
    'plot_bull = bool(params.get("plot_bull", True))\n'
    'plot_hidden_bull = bool(params.get("plot_hidden_bull", True))\n'
    'plot_bear = bool(params.get("plot_bear", True))\n'
    'plot_hidden_bear = bool(params.get("plot_hidden_bear", False))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'open_price = df["open"].astype(float) if "open" in df else close\n'
    "source_map = {\n"
    '    "close": close,\n'
    '    "hl2": (high + low) / 2.0,\n'
    '    "hlc3": (high + low + close) / 3.0,\n'
    '    "open": open_price,\n'
    '    "high": high,\n'
    '    "low": low,\n'
    "}\n"
    "price_source = source_map.get(source_name, close)\n"
    "\n"
    "# Use a causal Wilder RSI. The source series is selected only from the current\n"
    "# and already closed bars, and the first valid value is seeded after `length`.\n"
    "delta = price_source.diff()\n"
    "gain = delta.clip(lower=0.0)\n"
    "loss = (-delta).clip(lower=0.0)\n"
    "avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()\n"
    "avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()\n"
    "relative_strength = avg_gain / avg_loss.replace(0.0, np.nan)\n"
    "rsi = (100.0 - 100.0 / (1.0 + relative_strength)).clip(0.0, 100.0)\n"
    "rsi = rsi.where(avg_loss > 0.0, 100.0)\n"
    "rsi = rsi.where(~((avg_gain == 0.0) & (avg_loss == 0.0)), 50.0)\n"
    "\n"
    "rsi_values = rsi.to_numpy(dtype=float)\n"
    "low_values = low.to_numpy(dtype=float)\n"
    "high_values = high.to_numpy(dtype=float)\n"
    "n = len(df)\n"
    "\n"
    "pivot_low = np.full(n, np.nan, dtype=float)\n"
    "pivot_high = np.full(n, np.nan, dtype=float)\n"
    "regular_bull = np.zeros(n, dtype=bool)\n"
    "hidden_bull = np.zeros(n, dtype=bool)\n"
    "regular_bear = np.zeros(n, dtype=bool)\n"
    "hidden_bear = np.zeros(n, dtype=bool)\n"
    "\n"
    "# A pivot at p is emitted at p + pivot_right. This keeps all divergence\n"
    "# decisions causal: the right-side confirmation bars have already closed.\n"
    "for confirmation in range(pivot_left + pivot_right, n):\n"
    "    pivot = confirmation - pivot_right\n"
    "    current = rsi_values[pivot]\n"
    "    left = rsi_values[pivot - pivot_left:pivot]\n"
    "    right = rsi_values[pivot + 1:pivot + pivot_right + 1]\n"
    "    if not np.isfinite(current) or len(left) != pivot_left or len(right) != pivot_right:\n"
    "        continue\n"
    "    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):\n"
    "        continue\n"
    "\n"
    "    if current <= float(np.min(left)) and current < float(np.min(right)):\n"
    "        pivot_low[confirmation] = current\n"
    "    if current >= float(np.max(left)) and current > float(np.max(right)):\n"
    "        pivot_high[confirmation] = current\n"
    "\n"
    "# Compare each confirmed pivot with the immediately preceding pivot of the same\n"
    "# type. Divergence values are placed only on the confirmation bar rather than\n"
    "# backfilled across the historical segment, so appending new bars never rewrites\n"
    "# already-rendered values.\n"
    "previous_low_confirmation = None\n"
    "previous_low_rsi = np.nan\n"
    "previous_low_price = np.nan\n"
    "previous_high_confirmation = None\n"
    "previous_high_rsi = np.nan\n"
    "previous_high_price = np.nan\n"
    "\n"
    "for confirmation in range(n):\n"
    "    current_low_rsi = pivot_low[confirmation]\n"
    "    if np.isfinite(current_low_rsi):\n"
    "        current_low_price = low_values[confirmation - pivot_right]\n"
    "        if previous_low_confirmation is not None:\n"
    "            distance = confirmation - previous_low_confirmation\n"
    "            if range_lower <= distance <= range_upper and np.isfinite(current_low_price):\n"
    "                regular_bull[confirmation] = (\n"
    "                    current_low_price < previous_low_price and current_low_rsi > previous_low_rsi\n"
    "                )\n"
    "                hidden_bull[confirmation] = (\n"
    "                    current_low_price > previous_low_price and current_low_rsi < previous_low_rsi\n"
    "                )\n"
    "        previous_low_confirmation = confirmation\n"
    "        previous_low_rsi = current_low_rsi\n"
    "        previous_low_price = current_low_price\n"
    "\n"
    "    current_high_rsi = pivot_high[confirmation]\n"
    "    if np.isfinite(current_high_rsi):\n"
    "        current_high_price = high_values[confirmation - pivot_right]\n"
    "        if previous_high_confirmation is not None:\n"
    "            distance = confirmation - previous_high_confirmation\n"
    "            if range_lower <= distance <= range_upper and np.isfinite(current_high_price):\n"
    "                regular_bear[confirmation] = (\n"
    "                    current_high_price > previous_high_price and current_high_rsi < previous_high_rsi\n"
    "                )\n"
    "                hidden_bear[confirmation] = (\n"
    "                    current_high_price < previous_high_price and current_high_rsi > previous_high_rsi\n"
    "                )\n"
    "        previous_high_confirmation = confirmation\n"
    "        previous_high_rsi = current_high_rsi\n"
    "        previous_high_price = current_high_price\n"
    "\n"
    "\n"
    "def divergence_values(enabled, condition):\n"
    "    values = np.full(n, np.nan, dtype=float)\n"
    "    mask = enabled & condition & np.isfinite(rsi_values)\n"
    "    values[mask] = rsi_values[mask]\n"
    "    return values\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    "bull_values = divergence_values(plot_bull, regular_bull)\n"
    "hidden_bull_values = divergence_values(plot_hidden_bull, hidden_bull)\n"
    "bear_values = divergence_values(plot_bear, regular_bear)\n"
    "hidden_bear_values = divergence_values(plot_hidden_bear, hidden_bear)\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "RSI", "data": plot_list(rsi_values), "color": "#8D1699", "overlay": False, "width": 2},\n'
    '        {"name": "RSI Upper", "data": [70.0] * n, "color": "#9E9E9E", "overlay": False},\n'
    '        {"name": "RSI Lower", "data": [30.0] * n, "color": "#9E9E9E", "overlay": False},\n'
    '        {"name": "RSI Middle", "data": [50.0] * n, "color": "#9E9E9E", "overlay": False},\n'
    '        {"name": "Bullish Divergence", "data": plot_list(bull_values), "color": "#00C853", "overlay": False, "width": 2},\n'
    '        {"name": "Hidden Bullish Divergence", "data": plot_list(hidden_bull_values), "color": "#66BB6A", "overlay": False, "width": 2},\n'
    '        {"name": "Bearish Divergence", "data": plot_list(bear_values), "color": "#AB47BC", "overlay": False, "width": 2},\n'
    '        {"name": "Hidden Bearish Divergence", "data": plot_list(hidden_bear_values), "color": "#EF5350", "overlay": False, "width": 2},\n'
    "    ],\n"
    '    "signals": [\n'
    "        {\n"
    '            "type": "buy",\n'
    '            "text": "Bull",\n'
    '            "data": plot_list(bull_values),\n'
    '            "color": "#00C853",\n'
    "        },\n"
    "        {\n"
    '            "type": "buy",\n'
    '            "text": "H Bull",\n'
    '            "data": plot_list(hidden_bull_values),\n'
    '            "color": "#66BB6A",\n'
    "        },\n"
    "        {\n"
    '            "type": "sell",\n'
    '            "text": "Bear",\n'
    '            "data": plot_list(bear_values),\n'
    '            "color": "#AB47BC",\n'
    "        },\n"
    "        {\n"
    '            "type": "sell",\n'
    '            "text": "H Bear",\n'
    '            "data": plot_list(hidden_bear_values),\n'
    '            "color": "#EF5350",\n'
    "        },\n"
    "    ],\n"
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "source": source_name if source_name in source_map else "close",\n'
    '        "pivot_left": pivot_left,\n'
    '        "pivot_right": pivot_right,\n'
    '        "range_lower": range_lower,\n'
    '        "range_upper": range_upper,\n'
    '        "regular_bull": [1 if value else None for value in regular_bull],\n'
    '        "hidden_bull": [1 if value else None for value in hidden_bull],\n'
    '        "regular_bear": [1 if value else None for value in regular_bear],\n'
    '        "hidden_bear": [1 if value else None for value in hidden_bear],\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
