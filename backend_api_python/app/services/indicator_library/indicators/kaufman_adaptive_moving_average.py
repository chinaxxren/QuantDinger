"""Chart-only source for the kaufman_adaptive_moving_average indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Kaufman Adaptive Moving Average\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# KAMA adapts its smoothing constant to the ratio of net price movement to\n"
    "# total path movement. The recursive calculation is strictly causal.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Kaufman Adaptive Moving Average"\n'
    'my_indicator_description = "An adaptive moving average that responds to directional efficiency."\n'
    "\n"
    "# @param period int 10 Efficiency-ratio lookback period range=2:100:1\n"
    "# @param fast_period int 2 Fast EMA-equivalent period range=1:50:1\n"
    "# @param slow_period int 30 Slow EMA-equivalent period range=2:200:1\n"
    "\n"
    'period = max(2, int(params.get("period", 10)))\n'
    'fast_period = max(1, int(params.get("fast_period", 2)))\n'
    'slow_period = max(2, int(params.get("slow_period", 30)))\n'
    "if fast_period >= slow_period:\n"
    '    raise ValueError("fast_period must be less than slow_period")\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "change = close.diff(period).abs()\n"
    "volatility = close.diff().abs().rolling(period, min_periods=period).sum()\n"
    "efficiency = (change / volatility.replace(0.0, np.nan)).clip(0.0, 1.0).fillna(0.0)\n"
    "fast_sc = 2.0 / (fast_period + 1.0)\n"
    "slow_sc = 2.0 / (slow_period + 1.0)\n"
    "smoothing = (efficiency * (fast_sc - slow_sc) + slow_sc) ** 2\n"
    "kama = pd.Series(np.nan, index=close.index, dtype=float)\n"
    "first_valid = period\n"
    "if len(close) > first_valid:\n"
    "    kama.iloc[first_valid] = close.iloc[first_valid]\n"
    "    for i in range(first_valid + 1, len(close)):\n"
    "        kama.iloc[i] = kama.iloc[i - 1] + smoothing.iloc[i] * (close.iloc[i] - kama.iloc[i - 1])\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "KAMA", "data": plot_list(kama), "color": "#AB47BC", "overlay": True},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
