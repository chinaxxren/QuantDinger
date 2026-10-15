"""Chart-only source for the price_radio indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] John Ehlers The Price Radio\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Chart-only AM/FM demodulation of the candle-body price signal. The AM\n"
    "# envelope uses a four-bar rectifier peak followed by an SMA; the FM line\n"
    "# clamps the signal and applies Ehlers' causal Super Smoother recurrence.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] John Ehlers The Price Radio"\n'
    'my_indicator_description = "AM volatility envelope and FM Super Smoother of candle-body price movement."\n'
    "\n"
    "# @param am_period int 8 AM envelope smoothing period range=2:100:1\n"
    "# @param fm_period int 30 FM Super Smoother period range=3:100:1\n"
    "# @param fm_gain float 10.0 FM demodulator input gain range=0.1:100.0:0.1\n"
    "\n"
    'am_period = max(2, int(params.get("am_period", 8)))\n'
    'fm_period = max(3, int(params.get("fm_period", 30)))\n'
    'fm_gain = max(0.1, float(params.get("fm_gain", 10.0)))\n'
    "\n"
    "df = df.copy()\n"
    'open_price = df["open"].astype(float).to_numpy()\n'
    'close = df["close"].astype(float).to_numpy()\n'
    "n = len(df)\n"
    "\n"
    "# The source signal is the candle body's signed price movement.\n"
    "signal = close - open_price\n"
    "rectified_peak = pd.Series(np.abs(signal)).rolling(4, min_periods=4).max()\n"
    "am = rectified_peak.rolling(am_period, min_periods=am_period).mean().to_numpy()\n"
    "\n"
    "# Clamp amplitude before low-pass integration, as in the FM demodulator.\n"
    "fm_input = np.clip(fm_gain * signal, -1.0, 1.0)\n"
    "a1 = float(np.exp(-1.4142135623730951 * np.pi / fm_period))\n"
    "b1 = 2.0 * a1 * float(np.cos(1.4142135623730951 * np.pi / fm_period))\n"
    "c2 = b1\n"
    "c3 = -(a1 * a1)\n"
    "c1 = 1.0 - c2 - c3\n"
    "fm = np.full(n, np.nan, dtype=float)\n"
    "if n:\n"
    "    # Seed with the first available input. Subsequent values use only current\n"
    "    # and prior inputs/outputs, so appending candles leaves the prefix intact.\n"
    "    fm[0] = c1 * fm_input[0]\n"
    "    if n > 1:\n"
    "        fm[1] = c1 * (fm_input[1] + fm_input[0]) / 2.0 + c2 * fm[0]\n"
    "    for i in range(2, n):\n"
    "        fm[i] = (\n"
    "            c1 * (fm_input[i] + fm_input[i - 1]) / 2.0\n"
    "            + c2 * fm[i - 1]\n"
    "            + c3 * fm[i - 2]\n"
    "        )\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "AM", "data": plot_list(am), "color": "#EF5350", "overlay": False},\n'
    '        {"name": "FM", "data": plot_list(fm), "color": "#42A5F5", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
