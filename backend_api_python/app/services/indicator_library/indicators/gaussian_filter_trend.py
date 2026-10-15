"""Chart-only source for the gaussian_filter_trend indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Gaussian Filter Trend\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# A cascade of causal EMAs approximates Gaussian smoothing. ATR bands provide\n"
    "# an adaptive trend state without centered windows or future-bar dependence.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Gaussian Filter Trend"\n'
    'my_indicator_description = "Cascaded Gaussian-style smoother with ATR trend bands and visual reversal markers."\n'
    "\n"
    "# @param period int 20 Base smoothing period range=2:200:1\n"
    "# @param poles int 3 Number of smoothing stages range=1:6:1\n"
    "# @param atr_period int 14 ATR period range=2:100:1\n"
    "# @param multiplier float 1.5 ATR band multiplier range=0.25:8.0:0.25\n"
    "\n"
    'period = max(2, int(params.get("period", 20)))\n'
    'poles = min(6, max(1, int(params.get("poles", 3))))\n'
    'atr_period = max(2, int(params.get("atr_period", 14)))\n'
    'multiplier = max(0.05, float(params.get("multiplier", 1.5)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    "smooth = close.copy()\n"
    "for _ in range(poles):\n"
    "    smooth = smooth.ewm(span=period, adjust=False, min_periods=period).mean()\n"
    "previous_close = close.shift(1)\n"
    "true_range = pd.concat([\n"
    "    high - low,\n"
    "    (high - previous_close).abs(),\n"
    "    (low - previous_close).abs(),\n"
    "], axis=1).max(axis=1)\n"
    "atr = true_range.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()\n"
    "center = smooth.to_numpy()\n"
    "atr_values = atr.to_numpy()\n"
    "cl = close.to_numpy()\n"
    "trend_line = np.full(len(df), np.nan)\n"
    "trend = np.zeros(len(df), dtype=int)\n"
    "for i in range(len(df)):\n"
    "    if not np.isfinite(center[i]) or not np.isfinite(atr_values[i]):\n"
    "        continue\n"
    "    upper = center[i] + multiplier * atr_values[i]\n"
    "    lower = center[i] - multiplier * atr_values[i]\n"
    "    if i == 0 or trend[i - 1] == 0:\n"
    "        trend[i] = 1 if cl[i] >= center[i] else -1\n"
    "    elif trend[i - 1] > 0:\n"
    "        trend[i] = -1 if cl[i] < lower else 1\n"
    "    else:\n"
    "        trend[i] = 1 if cl[i] > upper else -1\n"
    "    trend_line[i] = lower if trend[i] > 0 else upper\n"
    "previous_trend = np.concatenate([[0], trend[:-1]])\n"
    "buy = (trend == 1) & (previous_trend == -1)\n"
    "sell = (trend == -1) & (previous_trend == 1)\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "lo = low.to_numpy()\n"
    "hi = high.to_numpy()\n"
    "buy_marks = [float(lo[i]) * 0.995 if buy[i] else None for i in range(len(df))]\n"
    "sell_marks = [float(hi[i]) * 1.005 if sell[i] else None for i in range(len(df))]\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Gaussian Filter", "data": plot_list(center), "color": "#2962FF", "overlay": True},\n'
    '        {"name": "Gaussian Trend", "data": plot_list(trend_line), "color": "#FFB300", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "GF+", "data": buy_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "GF-", "data": sell_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
