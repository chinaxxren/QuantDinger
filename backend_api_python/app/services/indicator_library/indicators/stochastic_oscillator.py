"""Chart-only source for the stochastic_oscillator indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Stochastic Oscillator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Fast %K and smoothed %D oscillator in a separate pane. No trade execution.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Stochastic Oscillator"\n'
    'my_indicator_description = "Stochastic %K and %D momentum oscillator in a separate chart pane."\n'
    "\n"
    "# @param length int 14 %K lookback period range=3:50:1\n"
    "# @param smooth_k int 3 %K smoothing period range=1:20:1\n"
    "# @param smooth_d int 3 %D smoothing period range=1:20:1\n"
    "\n"
    'length = max(2, int(params.get("length", 14)))\n'
    'smooth_k = max(1, int(params.get("smooth_k", 3)))\n'
    'smooth_d = max(1, int(params.get("smooth_d", 3)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "lowest = low.rolling(length, min_periods=length).min()\n"
    "highest = high.rolling(length, min_periods=length).max()\n"
    "span = (highest - lowest).replace(0.0, np.nan)\n"
    "raw_k = 100.0 * (close - lowest) / span\n"
    "percent_k = raw_k.rolling(smooth_k, min_periods=smooth_k).mean()\n"
    "percent_d = percent_k.rolling(smooth_d, min_periods=smooth_d).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(v) else float(v) for v in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "%K", "data": plot_list(percent_k), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "%D", "data": plot_list(percent_d), "color": "#FF6D00", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
