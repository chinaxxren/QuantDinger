"""Chart-only source for the wavetrend_oscillator indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] WaveTrend Oscillator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# LazyBear-style ESA/deviation channel index and smoothed signal line.\n"
    "# Oscillator lines are rendered in a separate pane; no trade execution.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] WaveTrend Oscillator"\n'
    'my_indicator_description = "ESA/deviation-based WaveTrend oscillator with signal line."\n'
    "\n"
    "# @param channel_length int 10 Channel index smoothing period range=3:40:1\n"
    "# @param average_length int 21 WaveTrend signal smoothing period range=3:80:1\n"
    "\n"
    'channel_length = max(2, int(params.get("channel_length", 10)))\n'
    'average_length = max(2, int(params.get("average_length", 21)))\n'
    "\n"
    "df = df.copy()\n"
    'ap = (df["high"].astype(float) + df["low"].astype(float) + df["close"].astype(float)) / 3.0\n'
    "esa = ap.ewm(span=channel_length, adjust=False, min_periods=channel_length).mean()\n"
    "deviation = (ap - esa).abs().ewm(span=channel_length, adjust=False, min_periods=channel_length).mean()\n"
    "ci = (ap - esa) / (0.015 * deviation.replace(0.0, np.nan))\n"
    "wt1 = ci.ewm(span=average_length, adjust=False, min_periods=average_length).mean()\n"
    "wt2 = wt1.rolling(4, min_periods=4).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(v) else float(v) for v in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "WT1", "data": plot_list(wt1), "color": "#00BCD4", "overlay": False},\n'
    '        {"name": "WT2", "data": plot_list(wt2), "color": "#FF9800", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
