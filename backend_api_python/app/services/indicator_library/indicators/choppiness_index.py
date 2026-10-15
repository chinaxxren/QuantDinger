"""Chart-only source for the choppiness_index indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Choppiness Index\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Compares the rolling sum of true range with the high-low span over the same\n"
    "# trailing window. Values are clamped to the conventional 0-100 range.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Choppiness Index"\n'
    'my_indicator_description = "Range-versus-true-range measure of market choppiness."\n'
    "\n"
    "# @param period int 14 Rolling period range=2:200:1\n"
    "\n"
    'period = max(2, int(params.get("period", 14)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "previous_close = close.shift(1)\n"
    "true_range = pd.concat([\n"
    "    high - low,\n"
    "    (high - previous_close).abs(),\n"
    "    (low - previous_close).abs(),\n"
    "], axis=1).max(axis=1)\n"
    "range_sum = true_range.rolling(period, min_periods=period).sum()\n"
    "rolling_high = high.rolling(period, min_periods=period).max()\n"
    "rolling_low = low.rolling(period, min_periods=period).min()\n"
    "price_span = (rolling_high - rolling_low).replace(0.0, np.nan)\n"
    "ratio = (range_sum / price_span).replace([np.inf, -np.inf], np.nan)\n"
    "choppiness = 100.0 * np.log10(ratio) / np.log10(float(period))\n"
    "choppiness = choppiness.replace([np.inf, -np.inf], np.nan).clip(0.0, 100.0)\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Choppiness", "data": plot_list(choppiness), "color": "#AB47BC", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
