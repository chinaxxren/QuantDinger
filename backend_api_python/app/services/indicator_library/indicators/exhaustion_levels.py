"""Chart-only source for the exhaustion_levels indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Exhaustion Levels\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Leledc-style exhaustion counters with persistent support and resistance\n"
    "# levels. This implementation emits chart lines and visual markers only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Exhaustion Levels"\n'
    "my_indicator_description = (\n"
    '    "Causal exhaustion counters with persistent support/resistance levels and "\n'
    '    "chart-only reversal markers."\n'
    ")\n"
    "\n"
    "# @param exhaustion_switch bool True Show exhaustion signal markers\n"
    "# @param level_switch bool True Show persistent exhaustion levels\n"
    "# @param length int 40 Extreme-window length range=2:200:1\n"
    "# @param bars int 10 Exhaustion counter threshold range=1:100:1\n"
    "# @param thickness int 2 Support/resistance line width range=1:5:1\n"
    "\n"
    'exhaustion_switch = bool(params.get("exhaustion_switch", True))\n'
    'level_switch = bool(params.get("level_switch", True))\n'
    'length = max(2, int(params.get("length", 40)))\n'
    'bars = max(1, int(params.get("bars", 10)))\n'
    'thickness = max(1, min(5, int(params.get("thickness", 2))))\n'
    "\n"
    "df = df.copy()\n"
    'open_price = df["open"].astype(float).to_numpy(dtype=float)\n'
    'high = df["high"].astype(float).to_numpy(dtype=float)\n'
    'low = df["low"].astype(float).to_numpy(dtype=float)\n'
    'close = df["close"].astype(float).to_numpy(dtype=float)\n'
    "n = len(df)\n"
    "\n"
    "# The source indicator uses persistent counters. A counter is incremented when\n"
    "# the current close is above/below the close four bars ago; equality leaves it\n"
    "# unchanged. Exhaustion resets the corresponding counter on the trigger bar.\n"
    "bindex = np.zeros(n, dtype=int)\n"
    "sindex = np.zeros(n, dtype=int)\n"
    "exhaustion = np.zeros(n, dtype=int)\n"
    "resistance = np.full(n, np.nan, dtype=float)\n"
    "support = np.full(n, np.nan, dtype=float)\n"
    "\n"
    "b_count = 0\n"
    "s_count = 0\n"
    "last_resistance = np.nan\n"
    "last_support = np.nan\n"
    "for i in range(n):\n"
    "    previous_resistance = last_resistance\n"
    "    previous_support = last_support\n"
    "\n"
    "    if i >= 4 and np.isfinite(close[i]) and np.isfinite(close[i - 4]):\n"
    "        if close[i] > close[i - 4]:\n"
    "            b_count += 1\n"
    "        elif close[i] < close[i - 4]:\n"
    "            s_count += 1\n"
    "\n"
    "    highest_window = high[max(0, i - length + 1):i + 1]\n"
    "    lowest_window = low[max(0, i - length + 1):i + 1]\n"
    "    highest_value = np.max(highest_window) if len(highest_window) and np.isfinite(highest_window).all() else np.nan\n"
    "    lowest_value = np.min(lowest_window) if len(lowest_window) and np.isfinite(lowest_window).all() else np.nan\n"
    "\n"
    "    top_exhaustion = (\n"
    "        b_count > bars\n"
    "        and np.isfinite(close[i])\n"
    "        and np.isfinite(open_price[i])\n"
    "        and np.isfinite(high[i])\n"
    "        and close[i] < open_price[i]\n"
    "        and np.isfinite(highest_value)\n"
    "        and high[i] >= highest_value\n"
    "    )\n"
    "    bottom_exhaustion = (\n"
    "        s_count > bars\n"
    "        and np.isfinite(close[i])\n"
    "        and np.isfinite(open_price[i])\n"
    "        and np.isfinite(low[i])\n"
    "        and close[i] > open_price[i]\n"
    "        and np.isfinite(lowest_value)\n"
    "        and low[i] <= lowest_value\n"
    "    )\n"
    "\n"
    "    # Preserve the original Lelex convention: -1 marks a top and +1 marks a\n"
    "    # bottom. A top takes priority if both conditions are theoretically true.\n"
    "    if top_exhaustion:\n"
    "        exhaustion[i] = -1\n"
    "        b_count = 0\n"
    "    elif bottom_exhaustion:\n"
    "        exhaustion[i] = 1\n"
    "        s_count = 0\n"
    "\n"
    "    bindex[i] = b_count\n"
    "    sindex[i] = s_count\n"
    "\n"
    "    # The levels are stepped forward from the latest exhaustion candle. They\n"
    "    # never depend on future bars and remain stable until a new level appears.\n"
    "    if exhaustion[i] != 0 and np.isfinite(high[i]) and close[i] < open_price[i]:\n"
    "        last_resistance = high[i]\n"
    "    if exhaustion[i] != 0 and np.isfinite(low[i]) and close[i] > open_price[i]:\n"
    "        last_support = low[i]\n"
    "\n"
    "    resistance[i] = last_resistance if np.isfinite(last_resistance) else previous_resistance\n"
    "    support[i] = last_support if np.isfinite(last_support) else previous_support\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "resistance_plot = resistance if level_switch else np.full(n, np.nan, dtype=float)\n"
    "support_plot = support if level_switch else np.full(n, np.nan, dtype=float)\n"
    "long_marks = [\n"
    "    float(low[i]) if exhaustion_switch and exhaustion[i] == 1 and np.isfinite(low[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "short_marks = [\n"
    "    float(high[i]) if exhaustion_switch and exhaustion[i] == -1 and np.isfinite(high[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    "        {\n"
    '            "name": "Exhaustion Resistance",\n'
    '            "data": plot_list(resistance_plot),\n'
    '            "color": "#EF5350",\n'
    '            "overlay": True,\n'
    '            "width": thickness,\n'
    "        },\n"
    "        {\n"
    '            "name": "Exhaustion Support",\n'
    '            "data": plot_list(support_plot),\n'
    '            "color": "#138484",\n'
    '            "overlay": True,\n'
    '            "width": thickness,\n'
    "        },\n"
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "Exhaustion Bottom", "data": long_marks, "color": "#00C853"},\n'
    '        {"type": "sell", "text": "Exhaustion Top", "data": short_marks, "color": "#EF5350"},\n'
    "    ],\n"
    '    "metadata": {\n'
    '        "exhaustion": [int(value) if value else None for value in exhaustion],\n'
    '        "bindex": [int(value) for value in bindex],\n'
    '        "sindex": [int(value) for value in sindex],\n'
    '        "causal": True,\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
