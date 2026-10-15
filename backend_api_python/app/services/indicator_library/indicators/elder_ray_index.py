"""Chart-only source for the elder_ray_index indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Elder Ray Index\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Bull and bear power measure the distance from an EMA to each bar's high and\n"
    "# low. The EMA and current OHLC values are causal and use no future bars.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Elder Ray Index"\n'
    'my_indicator_description = "Bull Power and Bear Power measured against an exponential moving average."\n'
    "\n"
    "# @param period int 13 EMA baseline period range=2:200:1\n"
    "\n"
    'period = max(2, int(params.get("period", 13)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    "baseline = close.ewm(span=period, adjust=False, min_periods=period).mean()\n"
    "bull_power = high - baseline\n"
    "bear_power = low - baseline\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Bull Power", "data": plot_list(bull_power), "color": "#26A69A", "overlay": False},\n'
    '        {"name": "Bear Power", "data": plot_list(bear_power), "color": "#EF5350", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
