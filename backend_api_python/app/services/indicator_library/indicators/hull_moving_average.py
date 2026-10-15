"""Chart-only source for the hull_moving_average indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Hull Moving Average\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# HMA combines weighted moving averages to reduce lag while retaining a\n"
    "# smooth trend line. All rolling windows are trailing and causal.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Hull Moving Average"\n'
    'my_indicator_description = "Reduced-lag weighted moving average for trend visualization."\n'
    "\n"
    "# @param period int 20 HMA lookback period range=2:200:1\n"
    "\n"
    'period = max(2, int(params.get("period", 20)))\n'
    "half_period = max(1, period // 2)\n"
    "sqrt_period = max(1, int(np.sqrt(period)))\n"
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "\n"
    "def weighted_average(window):\n"
    "    weights = np.arange(1, len(window) + 1, dtype=float)\n"
    "    return float(np.dot(window, weights) / weights.sum())\n"
    "\n"
    "wma_half = close.rolling(half_period, min_periods=half_period).apply(weighted_average, raw=True)\n"
    "wma_full = close.rolling(period, min_periods=period).apply(weighted_average, raw=True)\n"
    "raw_hma = 2.0 * wma_half - wma_full\n"
    "hma = raw_hma.rolling(sqrt_period, min_periods=sqrt_period).apply(weighted_average, raw=True)\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "HMA", "data": plot_list(hma), "color": "#FFB300", "overlay": True},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
