"""Chart-only source for the delta_rsi_oscillator indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Delta RSI Oscillator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Difference between fast and slow Wilder RSI readings. The spread highlights\n"
    "# momentum acceleration/deceleration; the signal and histogram are chart-only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Delta RSI Oscillator"\n'
    'my_indicator_description = "Fast-minus-slow RSI momentum spread with signal and histogram."\n'
    "\n"
    "# @param fast_period int 7 Fast RSI period range=2:100:1\n"
    "# @param slow_period int 21 Slow RSI period range=3:200:1\n"
    "# @param signal_period int 5 Signal EMA period range=2:100:1\n"
    "\n"
    'fast_period = max(2, int(params.get("fast_period", 7)))\n'
    'slow_period = max(fast_period + 1, int(params.get("slow_period", 21)))\n'
    'signal_period = max(2, int(params.get("signal_period", 5)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "change = close.diff()\n"
    "gain = change.clip(lower=0.0)\n"
    "loss = -change.clip(upper=0.0)\n"
    "\n"
    "def calculate_rsi(period):\n"
    "    average_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()\n"
    "    average_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()\n"
    "    relative_strength = average_gain / average_loss.replace(0.0, np.nan)\n"
    "    values = 100.0 - 100.0 / (1.0 + relative_strength)\n"
    "    values = values.where(average_loss != 0.0, 100.0)\n"
    "    values = values.where(average_gain != 0.0, 0.0)\n"
    "    return values.fillna(50.0)\n"
    "\n"
    "fast_rsi = calculate_rsi(fast_period)\n"
    "slow_rsi = calculate_rsi(slow_period)\n"
    "delta_rsi = fast_rsi - slow_rsi\n"
    "signal = delta_rsi.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()\n"
    "histogram = delta_rsi - signal\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Delta RSI", "data": plot_list(delta_rsi), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},\n'
    '        {"name": "Histogram", "data": plot_list(histogram), "color": "#26A69A", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
