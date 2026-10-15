"""Chart-only source for the ichimoku_cloud indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Ichimoku Cloud\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# This chart-safe representation exposes the current Tenkan-sen, Kijun-sen,\n"
    "# and cloud boundaries without forward-shifting values. That keeps each\n"
    "# returned point aligned with its source candle and prevents look-ahead bias.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Ichimoku Cloud"\n'
    'my_indicator_description = "Causal Ichimoku conversion, base, and cloud boundary lines."\n'
    "\n"
    "# @param conversion_period int 9 Conversion line lookback range=2:100:1\n"
    "# @param base_period int 26 Base line lookback range=2:200:1\n"
    "# @param span_b_period int 52 Cloud boundary lookback range=2:300:1\n"
    "\n"
    'conversion_period = max(2, int(params.get("conversion_period", 9)))\n'
    'base_period = max(2, int(params.get("base_period", 26)))\n'
    'span_b_period = max(2, int(params.get("span_b_period", 52)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    "conversion = (high.rolling(conversion_period, min_periods=conversion_period).max() + low.rolling(conversion_period, min_periods=conversion_period).min()) / 2.0\n"
    "base = (high.rolling(base_period, min_periods=base_period).max() + low.rolling(base_period, min_periods=base_period).min()) / 2.0\n"
    "span_a = (conversion + base) / 2.0\n"
    "span_b = (high.rolling(span_b_period, min_periods=span_b_period).max() + low.rolling(span_b_period, min_periods=span_b_period).min()) / 2.0\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Tenkan-sen", "data": plot_list(conversion), "color": "#26A69A", "overlay": True},\n'
    '        {"name": "Kijun-sen", "data": plot_list(base), "color": "#EF5350", "overlay": True},\n'
    '        {"name": "Senkou Span A", "data": plot_list(span_a), "color": "#66BB6A", "overlay": True},\n'
    '        {"name": "Senkou Span B", "data": plot_list(span_b), "color": "#AB47BC", "overlay": True},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
