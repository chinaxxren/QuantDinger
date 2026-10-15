"""Chart-only source for the g_channels indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] G Channels\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Recursive high/low channel with a causal average line. Signals are visual only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] G Channels"\n'
    'my_indicator_description = "Recursive high/low channel with trend-bias midline and breakout markers."\n'
    "\n"
    "# @param length int 100 Channel length range=20:240:5\n"
    "# @param signal_mode str close Midline signal mode choices=close,channel\n"
    "\n"
    'length = int(params.get("length", 100))\n'
    'signal_mode = str(params.get("signal_mode", "close"))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    "n = len(df)\n"
    "cl = close.to_numpy()\n"
    "\n"
    "upper = np.full(n, np.nan)\n"
    "lower = np.full(n, np.nan)\n"
    "mid = np.full(n, np.nan)\n"
    "\n"
    "if n > 0:\n"
    "    upper[0] = cl[0]\n"
    "    lower[0] = cl[0]\n"
    "    mid[0] = cl[0]\n"
    "\n"
    "for i in range(1, n):\n"
    "    previous_gap = (upper[i - 1] - lower[i - 1]) / max(1, length)\n"
    "    upper[i] = max(cl[i], upper[i - 1]) - previous_gap\n"
    "    lower[i] = min(cl[i], lower[i - 1]) + previous_gap\n"
    "    if lower[i] > upper[i]:\n"
    "        center = (upper[i] + lower[i]) / 2.0\n"
    "        upper[i] = center\n"
    "        lower[i] = center\n"
    "    mid[i] = (upper[i] + lower[i]) / 2.0\n"
    "\n"
    'if signal_mode == "channel":\n'
    "    long_condition = cl > upper\n"
    "    short_condition = cl < lower\n"
    "else:\n"
    "    long_condition = cl > mid\n"
    "    short_condition = cl < mid\n"
    "\n"
    "long_edge = long_condition & np.concatenate([[False], ~long_condition[:-1]])\n"
    "short_edge = short_condition & np.concatenate([[False], ~short_condition[:-1]])\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(v) else float(v) for v in values]\n"
    "\n"
    "long_marks = [float(low.iloc[i]) * 0.995 if bool(long_edge[i]) else None for i in range(n)]\n"
    "short_marks = [float(high.iloc[i]) * 1.005 if bool(short_edge[i]) else None for i in range(n)]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "G Upper", "data": plot_list(upper), "color": "#42A5F5", "overlay": True},\n'
    '        {"name": "G Mid", "data": plot_list(mid), "color": "#FFB300", "overlay": True},\n'
    '        {"name": "G Lower", "data": plot_list(lower), "color": "#42A5F5", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "G+", "data": long_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "G-", "data": short_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
