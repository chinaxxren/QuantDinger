"""Chart-only source for the balance_of_power indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Balance of Power\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Measures close location within each bar's open-to-close range relative to\n"
    "# the full high-low range. Zero-range bars are reported as neutral.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Balance of Power"\n'
    'my_indicator_description = "Per-bar buying and selling pressure from open, high, low, and close."\n'
    "\n"
    "# @param smooth_period int 1 Smoothing period range=1:100:1\n"
    "\n"
    'smooth_period = max(1, int(params.get("smooth_period", 1)))\n'
    "\n"
    "df = df.copy()\n"
    'open_price = df["open"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "bar_range = high - low\n"
    "bop = ((close - open_price) / bar_range.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan)\n"
    "bop = bop.where(bar_range != 0.0, 0.0).clip(-1.0, 1.0)\n"
    "if smooth_period > 1:\n"
    "    bop = bop.rolling(smooth_period, min_periods=smooth_period).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "BOP", "data": plot_list(bop), "color": "#26A69A", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
