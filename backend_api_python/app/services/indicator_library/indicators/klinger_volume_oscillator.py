"""Chart-only source for the klinger_volume_oscillator indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Klinger Volume Oscillator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Smooths a signed volume force derived from price trend and range. The\n"
    "# cumulative range state is updated bar by bar using current and prior data.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Klinger Volume Oscillator"\n'
    'my_indicator_description = "Signed volume-force oscillator with a signal line."\n'
    "\n"
    "# @param fast_period int 34 Fast EMA period range=2:200:1\n"
    "# @param slow_period int 55 Slow EMA period range=3:250:1\n"
    "# @param signal_period int 13 Signal EMA period range=2:100:1\n"
    "\n"
    'fast_period = max(2, int(params.get("fast_period", 34)))\n'
    'slow_period = max(fast_period + 1, int(params.get("slow_period", 55)))\n'
    'signal_period = max(2, int(params.get("signal_period", 13)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float).to_numpy()\n'
    'low = df["low"].astype(float).to_numpy()\n'
    'close = df["close"].astype(float).to_numpy()\n'
    'volume = df["volume"].astype(float).clip(lower=0.0).to_numpy()\n'
    "price_sum = high + low + close\n"
    "bar_range = np.maximum(0.0, high - low)\n"
    "force = np.full(len(df), np.nan)\n"
    "previous_trend = 0.0\n"
    "previous_range = 0.0\n"
    "cumulative_range = 0.0\n"
    "previous_price_sum = np.nan\n"
    "for i in range(len(df)):\n"
    "    if not np.isfinite(price_sum[i]) or not np.isfinite(bar_range[i]) or not np.isfinite(volume[i]):\n"
    "        continue\n"
    "    if np.isfinite(previous_price_sum):\n"
    "        if price_sum[i] > previous_price_sum:\n"
    "            current_trend = 1.0\n"
    "        elif price_sum[i] < previous_price_sum:\n"
    "            current_trend = -1.0\n"
    "        else:\n"
    "            current_trend = previous_trend if previous_trend != 0.0 else 1.0\n"
    "        if previous_trend == 0.0 or current_trend == previous_trend:\n"
    "            cumulative_range += bar_range[i]\n"
    "        else:\n"
    "            cumulative_range = previous_range + bar_range[i]\n"
    "    else:\n"
    "        current_trend = 1.0\n"
    "        cumulative_range = bar_range[i]\n"
    "    if cumulative_range > 0.0:\n"
    "        ratio = bar_range[i] / cumulative_range\n"
    "        force[i] = volume[i] * abs(2.0 * ratio - 1.0) * current_trend * 100.0\n"
    "    previous_trend = current_trend\n"
    "    previous_range = bar_range[i]\n"
    "    previous_price_sum = price_sum[i]\n"
    "volume_force = pd.Series(force, index=df.index)\n"
    "fast = volume_force.ewm(span=fast_period, adjust=False, min_periods=fast_period).mean()\n"
    "slow = volume_force.ewm(span=slow_period, adjust=False, min_periods=slow_period).mean()\n"
    "kvo = fast - slow\n"
    "signal = kvo.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "KVO", "data": plot_list(kvo), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
