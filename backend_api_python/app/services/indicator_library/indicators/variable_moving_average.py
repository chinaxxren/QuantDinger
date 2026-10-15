"""Chart-only source for the variable_moving_average indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Variable Moving Average\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# VIDYA-style adaptive average. The Chande momentum ratio adjusts the EMA\n"
    "# smoothing coefficient on each bar; all values are causal.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Variable Moving Average"\n'
    'my_indicator_description = "VIDYA-style adaptive moving average driven by normalized price momentum."\n'
    "\n"
    "# @param period int 20 Base smoothing period range=2:200:1\n"
    "# @param momentum_period int 9 Momentum normalization period range=2:100:1\n"
    "# @param signal_period int 9 Signal EMA period range=2:100:1\n"
    "\n"
    'period = max(2, int(params.get("period", 20)))\n'
    'momentum_period = max(2, int(params.get("momentum_period", 9)))\n'
    'signal_period = max(2, int(params.get("signal_period", 9)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "change = close.diff()\n"
    "up = change.clip(lower=0.0).rolling(momentum_period, min_periods=momentum_period).sum()\n"
    "down = (-change.clip(upper=0.0)).rolling(momentum_period, min_periods=momentum_period).sum()\n"
    "absolute_momentum = ((up - down).abs() / (up + down).replace(0.0, np.nan)).fillna(0.0).to_numpy()\n"
    "cl = close.to_numpy()\n"
    "vidya = np.full(len(df), np.nan)\n"
    "base_alpha = 2.0 / (period + 1.0)\n"
    "for i in range(len(df)):\n"
    "    if not np.isfinite(cl[i]):\n"
    "        continue\n"
    "    alpha = base_alpha * min(1.0, max(0.0, float(absolute_momentum[i])))\n"
    "    if i == 0 or not np.isfinite(vidya[i - 1]):\n"
    "        vidya[i] = cl[i]\n"
    "    else:\n"
    "        vidya[i] = alpha * cl[i] + (1.0 - alpha) * vidya[i - 1]\n"
    "vidya_series = pd.Series(vidya, index=df.index)\n"
    "signal = vidya_series.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean().to_numpy()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "VIDYA", "data": plot_list(vidya), "color": "#2962FF", "overlay": True},\n'
    '        {"name": "VIDYA Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": True},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
