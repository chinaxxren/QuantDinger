"""Chart-only source for the vwap_price_channel indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] VWAP Price Channel\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Rolling volume-weighted typical-price mean and standard-deviation bands.\n"
    "# A rolling window is used so the calculation works consistently on any\n"
    "# chart history without exchange-session assumptions.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] VWAP Price Channel"\n'
    'my_indicator_description = "Rolling volume-weighted price channel with deviation bands."\n'
    "\n"
    "# @param period int 30 Rolling VWAP window range=5:200:1\n"
    "# @param deviation float 1.5 Band deviation multiplier range=0.25:5.0:0.25\n"
    "\n"
    'period = max(2, int(params.get("period", 30)))\n'
    'deviation = max(0.0, float(params.get("deviation", 1.5)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    'volume = df["volume"].astype(float).clip(lower=0.0)\n'
    "typical = (high + low + close) / 3.0\n"
    "weighted_price = typical * volume\n"
    "rolling_volume = volume.rolling(period, min_periods=period).sum()\n"
    "vwap = weighted_price.rolling(period, min_periods=period).sum() / rolling_volume.replace(0.0, np.nan)\n"
    "weighted_sq = (typical * typical * volume).rolling(period, min_periods=period).sum() / rolling_volume.replace(0.0, np.nan)\n"
    "variance = (weighted_sq - vwap * vwap).clip(lower=0.0)\n"
    "std = np.sqrt(variance)\n"
    "upper = vwap + deviation * std\n"
    "lower = vwap - deviation * std\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(v) else float(v) for v in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "VWAP", "data": plot_list(vwap), "color": "#2962FF", "overlay": True},\n'
    '        {"name": "VWAP Upper", "data": plot_list(upper), "color": "#AB47BC", "overlay": True},\n'
    '        {"name": "VWAP Lower", "data": plot_list(lower), "color": "#AB47BC", "overlay": True},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
