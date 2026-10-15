"""Chart-only source for the coppock_curve indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Coppock Curve\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Weighted moving average of two rate-of-change series. All comparisons are\n"
    "# against prior closes and the weighted average is trailing (not centered).\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Coppock Curve"\n'
    'my_indicator_description = "Long-term momentum curve from weighted dual rate-of-change readings."\n'
    "\n"
    "# @param long_roc int 14 Long ROC period range=2:200:1\n"
    "# @param short_roc int 11 Short ROC period range=2:200:1\n"
    "# @param wma_period int 10 Weighted moving average period range=2:100:1\n"
    "\n"
    'long_roc = max(2, int(params.get("long_roc", 14)))\n'
    'short_roc = max(2, int(params.get("short_roc", 11)))\n'
    'wma_period = max(2, int(params.get("wma_period", 10)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "long_base = close.shift(long_roc).replace(0.0, np.nan)\n"
    "short_base = close.shift(short_roc).replace(0.0, np.nan)\n"
    "roc_sum = 100.0 * ((close / long_base - 1.0) + (close / short_base - 1.0))\n"
    "weights = np.arange(1.0, wma_period + 1.0)\n"
    "weight_total = float(weights.sum())\n"
    "def weighted_average(values):\n"
    "    return float(np.dot(values, weights) / weight_total)\n"
    "\n"
    "coppock = roc_sum.rolling(wma_period, min_periods=wma_period).apply(weighted_average, raw=True)\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Coppock Curve", "data": plot_list(coppock), "color": "#2962FF", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
