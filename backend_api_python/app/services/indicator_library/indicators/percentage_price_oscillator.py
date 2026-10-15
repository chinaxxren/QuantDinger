"""Chart-only source for the percentage_price_oscillator indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Percentage Price Oscillator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Expresses the fast/slow EMA spread as a percentage of the slow EMA, with a\n"
    "# trailing signal EMA and histogram. All smoothing is causal.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Percentage Price Oscillator"\n'
    'my_indicator_description = "Percentage-scaled EMA spread with signal and histogram."\n'
    "\n"
    "# @param fast_period int 12 Fast EMA period range=2:100:1\n"
    "# @param slow_period int 26 Slow EMA period range=3:200:1\n"
    "# @param signal_period int 9 Signal EMA period range=2:100:1\n"
    "\n"
    'fast_period = max(2, int(params.get("fast_period", 12)))\n'
    'slow_period = max(fast_period + 1, int(params.get("slow_period", 26)))\n'
    'signal_period = max(2, int(params.get("signal_period", 9)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "fast = close.ewm(span=fast_period, adjust=False, min_periods=fast_period).mean()\n"
    "slow = close.ewm(span=slow_period, adjust=False, min_periods=slow_period).mean()\n"
    "ppo = 100.0 * (fast - slow) / slow.replace(0.0, np.nan)\n"
    "ppo = ppo.replace([np.inf, -np.inf], np.nan)\n"
    "signal = ppo.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()\n"
    "histogram = ppo - signal\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "PPO", "data": plot_list(ppo), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},\n'
    '        {"name": "Histogram", "data": plot_list(histogram), "color": "#26A69A", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
