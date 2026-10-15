"""Reviewed backend calculation for the half_trend indicator."""

from app.services.indicator_library.runtime import (
    Any,
    Mapping,
    _atr,
    _integer,
    _line,
    _number,
    _output,
    _series,
    np,
    pd,
)


def _half_trend(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    amplitude = _integer(params, "amplitude", 2, minimum=1, maximum=30)
    atr_period = _integer(params, "atr_period", 100, minimum=2, maximum=200)
    deviation = _number(params, "channel_deviation", 2, minimum=0.25, maximum=6)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    atr = _atr(df, atr_period).to_numpy()
    prior_high = high.rolling(amplitude, min_periods=amplitude).max().shift(1).to_numpy()
    prior_low = low.rolling(amplitude, min_periods=amplitude).min().shift(1).to_numpy()
    trend = np.zeros(len(df), dtype=int)
    line = np.full(len(df), np.nan)
    upper = np.full(len(df), np.nan)
    lower = np.full(len(df), np.nan)
    for index in range(len(df)):
        trend[index] = trend[index - 1] if index else 1
        if np.isfinite(prior_high[index]) and close.iloc[index] > prior_high[index]:
            trend[index] = 1
        elif np.isfinite(prior_low[index]) and close.iloc[index] < prior_low[index]:
            trend[index] = -1
        if np.isfinite(atr[index]):
            center = prior_low[index] if trend[index] > 0 else prior_high[index]
            center = close.iloc[index] if not np.isfinite(center) else center
            line[index] = (
                max(center, line[index - 1])
                if index and trend[index] == trend[index - 1] == 1 and np.isfinite(line[index - 1])
                else min(center, line[index - 1])
                if index and trend[index] == trend[index - 1] == -1 and np.isfinite(line[index - 1])
                else center
            )
            upper[index], lower[index] = line[index] + deviation * atr[index], line[index] - deviation * atr[index]
    previous = np.concatenate(([0], trend[:-1]))
    buys = (trend == 1) & (previous == -1)
    sells = (trend == -1) & (previous == 1)
    return {
        **_output(
            "HalfTrend",
            [
                _line("half_trend", "HalfTrend", line, overlay=True, color="#2962ff"),
                _line("half_trend_upper", "Upper", upper, overlay=True, color="#26a69a"),
                _line("half_trend_lower", "Lower", lower, overlay=True, color="#ef5350"),
            ],
        ),
        "signals": [
            {
                "type": "buy",
                "text": "HT+",
                "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))],
                "color": "#00e676",
            },
            {
                "type": "sell",
                "text": "HT-",
                "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))],
                "color": "#ff5252",
            },
        ],
    }


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] HalfTrend\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal swing-channel trend line. A direction change can only use extrema\n"
    "# confirmed by the prior bars, avoiding centered-window lookahead.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] HalfTrend"\n'
    'my_indicator_description = "Swing-channel trend line with ATR bands and chart-only reversal markers."\n'
    "\n"
    "# @param amplitude int 2 Swing lookback range=1:30:1\n"
    "# @param atr_period int 100 ATR period range=2:200:1\n"
    "# @param channel_deviation float 2.0 ATR band multiplier range=0.25:6.0:0.25\n"
    "\n"
    'amplitude = max(1, int(params.get("amplitude", 2)))\n'
    'atr_period = max(2, int(params.get("atr_period", 100)))\n'
    'channel_deviation = max(0.05, float(params.get("channel_deviation", 2.0)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "previous_close = close.shift(1)\n"
    "true_range = pd.concat([\n"
    "    high - low,\n"
    "    (high - previous_close).abs(),\n"
    "    (low - previous_close).abs(),\n"
    "], axis=1).max(axis=1)\n"
    "atr = true_range.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean().to_numpy()\n"
    "prior_high = high.rolling(amplitude, min_periods=amplitude).max().shift(1).to_numpy()\n"
    "prior_low = low.rolling(amplitude, min_periods=amplitude).min().shift(1).to_numpy()\n"
    "cl = close.to_numpy()\n"
    "lo = low.to_numpy()\n"
    "hi = high.to_numpy()\n"
    "trend = np.zeros(len(df), dtype=int)\n"
    "line = np.full(len(df), np.nan)\n"
    "upper = np.full(len(df), np.nan)\n"
    "lower = np.full(len(df), np.nan)\n"
    "for i in range(len(df)):\n"
    "    if i == 0:\n"
    "        trend[i] = 1\n"
    "    else:\n"
    "        trend[i] = trend[i - 1]\n"
    "        if np.isfinite(prior_high[i]) and cl[i] > prior_high[i]:\n"
    "            trend[i] = 1\n"
    "        elif np.isfinite(prior_low[i]) and cl[i] < prior_low[i]:\n"
    "            trend[i] = -1\n"
    "    if not np.isfinite(atr[i]):\n"
    "        continue\n"
    "    half_width = float(atr[i]) * channel_deviation\n"
    "    center = prior_low[i] if trend[i] >= 0 else prior_high[i]\n"
    "    if not np.isfinite(center):\n"
    "        center = cl[i]\n"
    "    raw_line = float(center)\n"
    "    if i > 0 and np.isfinite(line[i - 1]):\n"
    "        if trend[i] == trend[i - 1] == 1:\n"
    "            raw_line = max(raw_line, line[i - 1])\n"
    "        elif trend[i] == trend[i - 1] == -1:\n"
    "            raw_line = min(raw_line, line[i - 1])\n"
    "    line[i] = raw_line\n"
    "    upper[i] = raw_line + half_width\n"
    "    lower[i] = raw_line - half_width\n"
    "\n"
    "previous_trend = np.concatenate([[0], trend[:-1]])\n"
    "buy = (trend == 1) & (previous_trend == -1)\n"
    "sell = (trend == -1) & (previous_trend == 1)\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "buy_marks = [float(lo[i]) * 0.995 if buy[i] else None for i in range(len(df))]\n"
    "sell_marks = [float(hi[i]) * 1.005 if sell[i] else None for i in range(len(df))]\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "HalfTrend", "data": plot_list(line), "color": "#2962FF", "overlay": True},\n'
    '        {"name": "HalfTrend Upper", "data": plot_list(upper), "color": "#26A69A", "overlay": True},\n'
    '        {"name": "HalfTrend Lower", "data": plot_list(lower), "color": "#EF5350", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "HT+", "data": buy_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "HT-", "data": sell_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)

compute = _half_trend
