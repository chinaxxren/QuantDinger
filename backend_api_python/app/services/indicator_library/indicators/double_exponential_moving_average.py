"""Chart-only source for the double_exponential_moving_average indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Double Exponential Moving Average\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# DEMA reduces EMA lag by combining a single EMA with the EMA of that EMA.\n"
    "# Every output at index i depends only on data through index i.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Double Exponential Moving Average"\n'
    'my_indicator_description = "A reduced-lag moving average formed from two exponential averages."\n'
    "\n"
    "# @param period int 20 EMA lookback period range=2:200:1\n"
    "\n"
    'period = max(2, int(params.get("period", 20)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "ema_once = close.ewm(span=period, adjust=False, min_periods=period).mean()\n"
    "ema_twice = ema_once.ewm(span=period, adjust=False, min_periods=period).mean()\n"
    "dema = 2.0 * ema_once - ema_twice\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "DEMA", "data": plot_list(dema), "color": "#26A69A", "overlay": True},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
