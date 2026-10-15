"""Chart-only source for the bollinger_bands indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Bollinger Bands\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Simple moving average with population-standard-deviation bands. Chart only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Bollinger Bands"\n'
    'my_indicator_description = "Moving-average volatility bands with configurable period and deviation."\n'
    "\n"
    "# @param length int 20 Moving average period range=5:100:1\n"
    "# @param deviation float 2.0 Standard deviation multiplier range=0.5:4.0:0.1\n"
    "\n"
    'length = max(2, int(params.get("length", 20)))\n'
    'deviation = max(0.1, float(params.get("deviation", 2.0)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "middle = close.rolling(length, min_periods=length).mean()\n"
    "std = close.rolling(length, min_periods=length).std(ddof=0)\n"
    "upper = middle + deviation * std\n"
    "lower = middle - deviation * std\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(v) else float(v) for v in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "BB Upper", "data": plot_list(upper), "color": "#42A5F5", "overlay": True},\n'
    '        {"name": "BB Middle", "data": plot_list(middle), "color": "#FFA726", "overlay": True},\n'
    '        {"name": "BB Lower", "data": plot_list(lower), "color": "#42A5F5", "overlay": True},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
