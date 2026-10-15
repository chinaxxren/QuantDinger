"""Chart-only source for the rsi_momentum indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] RSI Momentum\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Wilder-style RSI shown in its own indicator pane. No orders are generated.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] RSI Momentum"\n'
    'my_indicator_description = "Wilder RSI momentum oscillator with configurable period."\n'
    "\n"
    "# @param length int 14 RSI lookback period range=2:50:1\n"
    "\n"
    'length = max(2, int(params.get("length", 14)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "delta = close.diff()\n"
    "gain = delta.clip(lower=0.0)\n"
    "loss = -delta.clip(upper=0.0)\n"
    "avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()\n"
    "avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()\n"
    "relative_strength = avg_gain / avg_loss.replace(0.0, np.nan)\n"
    "rsi = 100.0 - (100.0 / (1.0 + relative_strength))\n"
    "rsi = rsi.where(avg_loss != 0.0, 100.0)\n"
    "rsi = rsi.where(~((avg_gain == 0.0) & (avg_loss == 0.0)), 50.0)\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "RSI", "data": [None if pd.isna(v) else float(v) for v in rsi], "color": "#7E57C2", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
