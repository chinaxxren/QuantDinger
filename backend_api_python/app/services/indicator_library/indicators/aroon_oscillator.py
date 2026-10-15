"""Chart-only source for the aroon_oscillator indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Aroon Oscillator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Measures how recently rolling highs and lows occurred. The rolling window\n"
    "# includes the current bar and does not use future data.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Aroon Oscillator"\n'
    'my_indicator_description = "Aroon Up/Down lines and oscillator derived from rolling high/low recency."\n'
    "\n"
    "# @param period int 25 Lookback period range=2:200:1\n"
    "\n"
    'period = max(2, int(params.get("period", 25)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float).to_numpy()\n'
    'low = df["low"].astype(float).to_numpy()\n'
    "aroon_up = np.full(len(df), np.nan)\n"
    "aroon_down = np.full(len(df), np.nan)\n"
    "for i in range(period - 1, len(df)):\n"
    "    start = i - period + 1\n"
    "    high_window = high[start:i + 1]\n"
    "    low_window = low[start:i + 1]\n"
    "    if not np.isfinite(high_window).all() or not np.isfinite(low_window).all():\n"
    "        continue\n"
    "    # Use the most recent occurrence when the extreme appears more than once.\n"
    "    high_age = period - 1 - int(np.flatnonzero(high_window == np.max(high_window))[-1])\n"
    "    low_age = period - 1 - int(np.flatnonzero(low_window == np.min(low_window))[-1])\n"
    "    aroon_up[i] = 100.0 * (period - high_age) / period\n"
    "    aroon_down[i] = 100.0 * (period - low_age) / period\n"
    "aroon = aroon_up - aroon_down\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Aroon Up", "data": plot_list(aroon_up), "color": "#26A69A", "overlay": False},\n'
    '        {"name": "Aroon Down", "data": plot_list(aroon_down), "color": "#EF5350", "overlay": False},\n'
    '        {"name": "Aroon Oscillator", "data": plot_list(aroon), "color": "#2962FF", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
