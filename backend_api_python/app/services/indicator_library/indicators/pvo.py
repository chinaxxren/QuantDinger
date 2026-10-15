"""Chart-only source for the pvo indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# Percentage Volume Oscillator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Percentage difference between short and long volume EMAs, with a signal line\n"
    "# and histogram. EMA seeding follows the library convention: the first value is\n"
    "# the simple average of the first complete period.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "Percentage Volume Oscillator"\n'
    'my_indicator_description = "Percentage difference between short and long volume EMAs."\n'
    "\n"
    "# @param short_period int 12 Short volume EMA period range=2:100:1\n"
    "# @param long_period int 26 Long volume EMA period range=3:200:1\n"
    "# @param signal_period int 9 Signal EMA period range=1:100:1\n"
    "\n"
    'short_period = int(params.get("short_period", 12))\n'
    'long_period = int(params.get("long_period", 26))\n'
    'signal_period = int(params.get("signal_period", 9))\n'
    'volume = pd.to_numeric(df["volume"], errors="coerce").clip(lower=0.0)\n'
    "\n"
    "def seeded_ema(values, period):\n"
    '    numeric = pd.to_numeric(values, errors="coerce")\n'
    "    data = numeric.to_numpy(dtype=float, copy=False)\n"
    "    result = pd.Series(np.nan, index=numeric.index, dtype=float)\n"
    "    valid_positions = np.flatnonzero(np.isfinite(data))\n"
    "    if len(valid_positions) < period:\n"
    "        return result\n"
    "    seed_position = valid_positions[period - 1]\n"
    "    result.iloc[seed_position] = float(np.mean(data[valid_positions[:period]]))\n"
    "    alpha = 2.0 / (period + 1.0)\n"
    "    for index in range(seed_position + 1, len(data)):\n"
    "        current = data[index]\n"
    "        previous = result.iloc[index - 1]\n"
    "        result.iloc[index] = previous if not np.isfinite(current) else previous + alpha * (current - previous)\n"
    "    return result\n"
    "\n"
    "short_ema = seeded_ema(volume, short_period)\n"
    "long_ema = seeded_ema(volume, long_period)\n"
    "pvo = 100.0 * (short_ema - long_ema) / long_ema.replace(0.0, np.nan)\n"
    "pvo = pvo.replace([np.inf, -np.inf], np.nan)\n"
    "signal = seeded_ema(pvo, signal_period)\n"
    "histogram = pvo - signal\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"key": "pvo", "title": "PVO", "data": pvo.tolist(), "color": "#2962ff", "overlay": False},\n'
    '        {"key": "signal", "title": "Signal", "data": signal.tolist(), "color": "#ff6d00", "overlay": False},\n'
    '        {"key": "histogram", "title": "Histogram", "data": histogram.tolist(), "type": "histogram", "color": "#26a69a", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
