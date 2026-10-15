"""Chart-only source for the chaikin_money_flow indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Chaikin Money Flow\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Rolling volume-weighted close-location value. Zero-range bars contribute no\n"
    "# money flow, and the ratio is undefined when the window has no traded volume.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Chaikin Money Flow"\n'
    'my_indicator_description = "Rolling volume-weighted buying and selling pressure oscillator."\n'
    "\n"
    "# @param period int 20 Rolling period range=2:200:1\n"
    "\n"
    'period = max(2, int(params.get("period", 20)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    'volume = df["volume"].astype(float).clip(lower=0.0)\n'
    "price_range = high - low\n"
    "money_flow_multiplier = ((close - low) - (high - close)) / price_range.replace(0.0, np.nan)\n"
    "money_flow_multiplier = money_flow_multiplier.replace([np.inf, -np.inf], np.nan).fillna(0.0)\n"
    "raw_money_flow = money_flow_multiplier * volume\n"
    "volume_sum = volume.rolling(period, min_periods=period).sum()\n"
    "flow_sum = raw_money_flow.rolling(period, min_periods=period).sum()\n"
    "cmf = (flow_sum / volume_sum.replace(0.0, np.nan)).clip(-1.0, 1.0)\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "CMF", "data": plot_list(cmf), "color": "#26A69A", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
