"""Chart-only source for the turtle_trade_channels indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Turtle Trade Channels\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Donchian-style entry and exit channels use only completed prior bars, avoiding\n"
    "# look-ahead in the plotted breakout thresholds.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Turtle Trade Channels"\n'
    'my_indicator_description = "Prior-bar breakout and exit channels inspired by Turtle trading rules."\n'
    "\n"
    "# @param entry_length int 20 Entry channel lookback range=5:100:1\n"
    "# @param exit_length int 10 Exit channel lookback range=2:50:1\n"
    "\n"
    'entry_length = max(2, int(params.get("entry_length", 20)))\n'
    'exit_length = max(2, int(params.get("exit_length", 10)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "entry_upper = high.rolling(entry_length, min_periods=entry_length).max().shift(1)\n"
    "entry_lower = low.rolling(entry_length, min_periods=entry_length).min().shift(1)\n"
    "exit_upper = high.rolling(exit_length, min_periods=exit_length).max().shift(1)\n"
    "exit_lower = low.rolling(exit_length, min_periods=exit_length).min().shift(1)\n"
    "cl = close.to_numpy()\n"
    "long_condition = cl > entry_upper.to_numpy()\n"
    "short_condition = cl < entry_lower.to_numpy()\n"
    "long_edge = long_condition & np.concatenate([[False], ~long_condition[:-1]])\n"
    "short_edge = short_condition & np.concatenate([[False], ~short_condition[:-1]])\n"
    "long_marks = [float(low.iloc[i]) * 0.995 if bool(long_edge[i]) else None for i in range(len(df))]\n"
    "short_marks = [float(high.iloc[i]) * 1.005 if bool(short_edge[i]) else None for i in range(len(df))]\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(v) else float(v) for v in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Entry Upper", "data": plot_list(entry_upper), "color": "#26A69A", "overlay": True},\n'
    '        {"name": "Entry Lower", "data": plot_list(entry_lower), "color": "#EF5350", "overlay": True},\n'
    '        {"name": "Exit Upper", "data": plot_list(exit_upper), "color": "#80CBC4", "overlay": True},\n'
    '        {"name": "Exit Lower", "data": plot_list(exit_lower), "color": "#EF9A9A", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "Turtle+", "data": long_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "Turtle-", "data": short_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
