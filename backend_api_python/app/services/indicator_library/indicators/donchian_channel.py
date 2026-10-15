"""Chart-only source for the donchian_channel indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Donchian Channel\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Prior-bar rolling extremes avoid including the current candle in the\n"
    "# breakout threshold. Markers are visual annotations only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Donchian Channel"\n'
    'my_indicator_description = "Prior-period high/low channel with a midpoint and breakout markers."\n'
    "\n"
    "# @param length int 20 Channel lookback period range=5:100:1\n"
    "\n"
    'length = max(2, int(params.get("length", 20)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "n = len(df)\n"
    "upper = high.rolling(length, min_periods=length).max().shift(1)\n"
    "lower = low.rolling(length, min_periods=length).min().shift(1)\n"
    "mid = (upper + lower) / 2.0\n"
    "cl = close.to_numpy()\n"
    "up = upper.to_numpy()\n"
    "lo = lower.to_numpy()\n"
    "long_condition = cl > up\n"
    "short_condition = cl < lo\n"
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
    '        {"name": "Donchian Upper", "data": plot_list(upper), "color": "#26A69A", "overlay": True},\n'
    '        {"name": "Donchian Mid", "data": plot_list(mid), "color": "#90A4AE", "overlay": True},\n'
    '        {"name": "Donchian Lower", "data": plot_list(lower), "color": "#EF5350", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "DC+", "data": long_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "DC-", "data": short_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
