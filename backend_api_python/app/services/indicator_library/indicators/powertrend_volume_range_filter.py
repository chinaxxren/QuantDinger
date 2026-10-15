"""Chart-only source for the powertrend_volume_range_filter indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] PowerTrend Volume Range Filter\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# A native QuantDinger interpretation of a volume-confirmed range filter.\n"
    "# Signals are chart markers only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] PowerTrend Volume Range Filter"\n'
    'my_indicator_description = "Range Filter trend state confirmed by EMA power and relative volume expansion."\n'
    "\n"
    "# @param range_period int 34 Range smoothing period range=10:120:2\n"
    "# @param range_multiplier float 2.5 Range multiplier range=1.0:6.0:0.25\n"
    "# @param fast_period int 21 Fast EMA period range=5:60:1\n"
    "# @param slow_period int 55 Slow EMA period range=20:160:5\n"
    "# @param volume_period int 34 Volume baseline period range=10:120:2\n"
    "# @param min_relative_volume float 1.05 Minimum relative volume range=0.5:3.0:0.05\n"
    "\n"
    'range_period = int(params.get("range_period", 34))\n'
    'range_multiplier = float(params.get("range_multiplier", 2.5))\n'
    'fast_period = int(params.get("fast_period", 21))\n'
    'slow_period = int(params.get("slow_period", 55))\n'
    'volume_period = int(params.get("volume_period", 34))\n'
    'min_relative_volume = float(params.get("min_relative_volume", 1.05))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'volume = df.get("volume", pd.Series([0.0] * len(df), index=df.index)).astype(float)\n'
    "n = len(df)\n"
    "\n"
    "price_delta = close.diff().abs().fillna(0.0)\n"
    "smooth_range = price_delta.ewm(span=range_period, adjust=False).mean()\n"
    "smooth_range = smooth_range.ewm(span=max(1, range_period * 2 - 1), adjust=False).mean() * range_multiplier\n"
    "\n"
    "cl = close.to_numpy()\n"
    "rng = smooth_range.to_numpy()\n"
    "filt = np.full(n, np.nan)\n"
    "if n > 0:\n"
    "    filt[0] = cl[0]\n"
    "for i in range(1, n):\n"
    "    previous = filt[i - 1]\n"
    "    current_range = 0.0 if np.isnan(rng[i]) else rng[i]\n"
    "    filt[i] = max(previous, cl[i] - current_range) if cl[i] > previous else min(previous, cl[i] + current_range)\n"
    "\n"
    "ema_fast = close.ewm(span=fast_period, adjust=False).mean()\n"
    "ema_slow = close.ewm(span=slow_period, adjust=False).mean()\n"
    "power_line = ema_fast - ema_slow\n"
    "volume_base = volume.ewm(span=volume_period, adjust=False).mean().replace(0, np.nan)\n"
    "relative_volume = (volume / volume_base).replace([np.inf, -np.inf], np.nan).fillna(0.0)\n"
    "\n"
    "range_trend_up = close.to_numpy() > filt\n"
    "range_trend_down = close.to_numpy() < filt\n"
    "power_up = power_line.to_numpy() > 0\n"
    "power_down = power_line.to_numpy() < 0\n"
    "volume_ok = relative_volume.to_numpy() >= min_relative_volume\n"
    "\n"
    "long_condition = range_trend_up & power_up & volume_ok\n"
    "short_condition = range_trend_down & power_down & volume_ok\n"
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
    '        {"name": "Power Range Filter", "data": plot_list(filt), "color": "#00BCD4", "overlay": True},\n'
    '        {"name": "Fast EMA", "data": plot_list(ema_fast), "color": "#FFB300", "overlay": True},\n'
    '        {"name": "Slow EMA", "data": plot_list(ema_slow), "color": "#5C6BC0", "overlay": True},\n'
    '        {"name": "Relative Volume", "data": plot_list(relative_volume), "color": "#26A69A", "overlay": False},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "PT+", "data": long_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "PT-", "data": short_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
