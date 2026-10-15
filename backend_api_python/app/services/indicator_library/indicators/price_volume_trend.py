"""Chart-only source for the price_volume_trend indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Price Volume Trend\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Cumulative volume-weighted percentage price change with an optional signal\n"
    "# average. Accumulation starts at zero and is strictly bar-by-bar causal.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Price Volume Trend"\n'
    'my_indicator_description = "Cumulative percentage price change weighted by volume."\n'
    "\n"
    "# @param signal_period int 21 Signal EMA period range=1:200:1\n"
    "\n"
    'signal_period = max(1, int(params.get("signal_period", 21)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    'volume = df["volume"].astype(float).clip(lower=0.0)\n'
    "previous_close = close.shift(1)\n"
    "base = previous_close.replace(0.0, np.nan)\n"
    "period_return = close.div(base).sub(1.0).replace([np.inf, -np.inf], np.nan).fillna(0.0)\n"
    "pvt = (period_return * volume).cumsum()\n"
    "signal = pvt.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "PVT", "data": plot_list(pvt), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
