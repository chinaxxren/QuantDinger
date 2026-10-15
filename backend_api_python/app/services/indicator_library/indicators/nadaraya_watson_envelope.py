"""Chart-only source for the nadaraya_watson_envelope indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Nadaraya-Watson Envelope\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal Gaussian-kernel smoother with ATR envelope bands. No future bars are\n"
    "# used, so the line is stable once a candle closes. Signals are visual only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Nadaraya-Watson Envelope"\n'
    'my_indicator_description = "Causal Gaussian-kernel smoother with ATR envelope bands for mean reversion zones."\n'
    "\n"
    "# @param lookback int 64 Kernel lookback window range=20:160:4\n"
    "# @param bandwidth float 8.0 Gaussian bandwidth range=2.0:30.0:0.5\n"
    "# @param atr_period int 21 ATR period range=5:80:1\n"
    "# @param envelope_multiplier float 2.0 ATR envelope multiplier range=0.5:5.0:0.25\n"
    "\n"
    'lookback = int(params.get("lookback", 64))\n'
    'bandwidth = float(params.get("bandwidth", 8.0))\n'
    'atr_period = int(params.get("atr_period", 21))\n'
    'envelope_multiplier = float(params.get("envelope_multiplier", 2.0))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "n = len(df)\n"
    "cl = close.to_numpy()\n"
    "\n"
    "smooth = np.full(n, np.nan)\n"
    "for i in range(n):\n"
    "    start = max(0, i - lookback + 1)\n"
    "    window = cl[start:i + 1]\n"
    "    distance = np.arange(len(window) - 1, -1, -1, dtype=float)\n"
    "    weights = np.exp(-(distance * distance) / (2.0 * bandwidth * bandwidth))\n"
    "    weight_sum = weights.sum()\n"
    "    smooth[i] = float((window * weights).sum() / weight_sum) if weight_sum > 0 else cl[i]\n"
    "\n"
    "prev_close = close.shift(1)\n"
    "tr = pd.concat([\n"
    "    high - low,\n"
    "    (high - prev_close).abs(),\n"
    "    (low - prev_close).abs(),\n"
    "], axis=1).max(axis=1)\n"
    "atr = tr.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()\n"
    "upper = smooth + envelope_multiplier * atr.to_numpy()\n"
    "lower = smooth - envelope_multiplier * atr.to_numpy()\n"
    "\n"
    "below_lower = close.to_numpy() < lower\n"
    "above_upper = close.to_numpy() > upper\n"
    "reclaim_lower = (close.to_numpy() > lower) & np.concatenate([[False], below_lower[:-1]])\n"
    "reject_upper = (close.to_numpy() < upper) & np.concatenate([[False], above_upper[:-1]])\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(v) else float(v) for v in values]\n"
    "\n"
    "long_marks = [float(low.iloc[i]) * 0.995 if bool(reclaim_lower[i]) else None for i in range(n)]\n"
    "short_marks = [float(high.iloc[i]) * 1.005 if bool(reject_upper[i]) else None for i in range(n)]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "NW Smooth", "data": plot_list(smooth), "color": "#FFB300", "overlay": True},\n'
    '        {"name": "NW Upper", "data": plot_list(upper), "color": "#AB47BC", "overlay": True},\n'
    '        {"name": "NW Lower", "data": plot_list(lower), "color": "#AB47BC", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "NW↥", "data": long_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "NW↧", "data": short_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)
