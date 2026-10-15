"""Chart-only source for the relative_volatility_index indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Relative Volatility Index\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Assigns rolling price standard deviation to up/down movement and compares\n"
    "# their Wilder-smoothed totals. The calculation uses only trailing data.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Relative Volatility Index"\n'
    'my_indicator_description = "Directional volatility oscillator normalized to a 0-100 scale."\n'
    "\n"
    "# @param period int 14 Volatility and smoothing period range=2:200:1\n"
    "\n"
    'period = max(2, int(params.get("period", 14)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "change = close.diff()\n"
    "volatility = close.rolling(period, min_periods=period).std(ddof=0)\n"
    "up_volatility = volatility.where(change > 0.0, 0.0)\n"
    "down_volatility = volatility.where(change < 0.0, 0.0)\n"
    "up_average = up_volatility.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()\n"
    "down_average = down_volatility.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()\n"
    "volatility_sum = up_average + down_average\n"
    "rvi = 100.0 * up_average / volatility_sum.replace(0.0, np.nan)\n"
    "rvi = rvi.where(volatility_sum != 0.0, 50.0).clip(0.0, 100.0)\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "RVI", "data": plot_list(rvi), "color": "#7E57C2", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
