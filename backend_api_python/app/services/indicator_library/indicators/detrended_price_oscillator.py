"""Chart-only source for the detrended_price_oscillator indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Detrended Price Oscillator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Compares price with a lagged trailing moving average to emphasize cyclical\n"
    "# deviation. The average is shifted backward in time, never forward-looking.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Detrended Price Oscillator"\n'
    'my_indicator_description = "Price deviation from a lagged trailing simple moving average."\n'
    "\n"
    "# @param period int 20 Moving average and cycle period range=2:200:1\n"
    "\n"
    'period = max(2, int(params.get("period", 20)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "cycle_offset = period // 2 + 1\n"
    "lagged_average = close.rolling(period, min_periods=period).mean().shift(cycle_offset)\n"
    "dpo = close - lagged_average\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "DPO", "data": plot_list(dpo), "color": "#2962FF", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
