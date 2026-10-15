"""Reviewed backend calculation for the chandelier_exit indicator."""

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


def _chandelier(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 22, minimum=5, maximum=100)
    multiplier = _number(params, "atr_multiplier", 3, minimum=1, maximum=6)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    atr = _atr(df, period)
    long_candidate = high.rolling(period, min_periods=period).max() - multiplier * atr
    short_candidate = low.rolling(period, min_periods=period).min() + multiplier * atr
    trend = np.zeros(len(df), dtype=int)
    stop = np.full(len(df), np.nan)
    for index in range(len(df)):
        if not np.isfinite(long_candidate.iloc[index]) or not np.isfinite(short_candidate.iloc[index]):
            continue
        previous_trend = trend[index - 1] if index else 0
        previous_stop = stop[index - 1] if index else np.nan
        if previous_trend == 0:
            trend[index] = (
                1 if close.iloc[index] >= (long_candidate.iloc[index] + short_candidate.iloc[index]) / 2 else -1
            )
            stop[index] = long_candidate.iloc[index] if trend[index] > 0 else short_candidate.iloc[index]
        elif previous_trend > 0:
            trend[index] = -1 if close.iloc[index] < previous_stop else 1
            stop[index] = (
                short_candidate.iloc[index] if trend[index] < 0 else max(previous_stop, long_candidate.iloc[index])
            )
        else:
            trend[index] = 1 if close.iloc[index] > previous_stop else -1
            stop[index] = (
                long_candidate.iloc[index] if trend[index] > 0 else min(previous_stop, short_candidate.iloc[index])
            )
    previous = np.concatenate(([0], trend[:-1]))
    buys, sells = (trend == 1) & (previous != 1), (trend == -1) & (previous != -1)
    return {
        **_output(
            "Chandelier Exit", [_line("chandelier_stop", "Chandelier Stop", stop, overlay=True, color="#ffb300")]
        ),
        "signals": [
            {
                "type": "buy",
                "text": "CE+",
                "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))],
                "color": "#00e676",
            },
            {
                "type": "sell",
                "text": "CE-",
                "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))],
                "color": "#ff5252",
            },
        ],
    }


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Chandelier Exit\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# ATR-based trailing levels from rolling extremes. The displayed stop follows\n"
    "# the active direction and only emits chart markers on confirmed flips.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Chandelier Exit"\n'
    'my_indicator_description = "ATR trailing stop levels based on rolling highs and lows."\n'
    "\n"
    "# @param length int 22 Extreme and ATR lookback period range=5:100:1\n"
    "# @param atr_multiplier float 3.0 ATR stop multiplier range=1.0:6.0:0.25\n"
    "\n"
    'length = max(2, int(params.get("length", 22)))\n'
    'atr_multiplier = max(0.1, float(params.get("atr_multiplier", 3.0)))\n'
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
    "atr = true_range.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()\n"
    "long_candidate = high.rolling(length, min_periods=length).max() - atr_multiplier * atr\n"
    "short_candidate = low.rolling(length, min_periods=length).min() + atr_multiplier * atr\n"
    "n = len(df)\n"
    "cl = close.to_numpy()\n"
    "long_values = long_candidate.to_numpy()\n"
    "short_values = short_candidate.to_numpy()\n"
    "trend = np.zeros(n, dtype=int)\n"
    "stop = np.full(n, np.nan)\n"
    "for i in range(n):\n"
    "    if pd.isna(long_values[i]) or pd.isna(short_values[i]):\n"
    "        continue\n"
    "    prior_trend = trend[i - 1] if i > 0 else 0\n"
    "    prior_stop = stop[i - 1] if i > 0 else np.nan\n"
    "    if prior_trend == 0:\n"
    "        trend[i] = 1 if cl[i] >= (long_values[i] + short_values[i]) / 2.0 else -1\n"
    "        stop[i] = long_values[i] if trend[i] > 0 else short_values[i]\n"
    "    elif prior_trend > 0:\n"
    "        if cl[i] < prior_stop:\n"
    "            trend[i] = -1\n"
    "            stop[i] = short_values[i]\n"
    "        else:\n"
    "            trend[i] = 1\n"
    "            stop[i] = max(prior_stop, long_values[i])\n"
    "    else:\n"
    "        if cl[i] > prior_stop:\n"
    "            trend[i] = 1\n"
    "            stop[i] = long_values[i]\n"
    "        else:\n"
    "            trend[i] = -1\n"
    "            stop[i] = min(prior_stop, short_values[i])\n"
    "long_flip = (trend == 1) & np.concatenate([[False], trend[:-1] != 1])\n"
    "short_flip = (trend == -1) & np.concatenate([[False], trend[:-1] != -1])\n"
    "long_marks = [float(low.iloc[i]) * 0.995 if bool(long_flip[i]) else None for i in range(n)]\n"
    "short_marks = [float(high.iloc[i]) * 1.005 if bool(short_flip[i]) else None for i in range(n)]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Chandelier Stop", "data": [None if pd.isna(v) else float(v) for v in stop], "color": "#FFB300", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "CE+", "data": long_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "CE-", "data": short_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)

compute = _chandelier
