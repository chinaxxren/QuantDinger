"""Reviewed backend calculation for the atr_rope indicator."""

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


def _atr_rope(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "atr_period", 14, minimum=2, maximum=100)
    multiplier = _number(params, "multiplier", 1.5, minimum=0.25, maximum=8)
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    atr = _atr(df, period).to_numpy()
    closes = close.to_numpy()
    rope = np.full(len(df), np.nan)
    direction = np.zeros(len(df), dtype=int)
    for index in range(len(df)):
        if not np.isfinite(atr[index]):
            continue
        threshold = atr[index] * multiplier
        if index == 0 or not np.isfinite(rope[index - 1]):
            rope[index] = closes[index]
            continue
        previous = rope[index - 1]
        if closes[index] > previous + threshold:
            rope[index], direction[index] = closes[index] - threshold, 1
        elif closes[index] < previous - threshold:
            rope[index], direction[index] = closes[index] + threshold, -1
        else:
            rope[index], direction[index] = previous, direction[index - 1]
    previous = np.concatenate(([0], direction[:-1]))
    buys, sells = (direction == 1) & (previous != 1), (direction == -1) & (previous != -1)
    return {
        **_output("ATR Rope", [_line("atr_rope", "ATR Rope", rope, overlay=True, color="#26a69a")]),
        "signals": [
            {
                "type": "buy",
                "text": "Rope+",
                "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))],
                "color": "#00e676",
            },
            {
                "type": "sell",
                "text": "Rope-",
                "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))],
                "color": "#ff5252",
            },
        ],
    }


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] ATR Rope\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal ATR-step trend filter. The rope only moves after price crosses an\n"
    "# ATR-scaled threshold; markers show state transitions for charting only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] ATR Rope"\n'
    'my_indicator_description = "ATR-step trend filter with a trailing rope and chart-only direction-change markers."\n'
    "\n"
    "# @param atr_period int 14 ATR period range=2:100:1\n"
    "# @param multiplier float 1.5 ATR threshold multiplier range=0.25:8.0:0.25\n"
    "\n"
    'atr_period = max(2, int(params.get("atr_period", 14)))\n'
    'multiplier = max(0.05, float(params.get("multiplier", 1.5)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "prev_close = close.shift(1)\n"
    "tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)\n"
    "atr = tr.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean().to_numpy()\n"
    "cl = close.to_numpy()\n"
    "rope = np.full(len(df), np.nan)\n"
    "direction = np.zeros(len(df), dtype=int)\n"
    "for i in range(len(df)):\n"
    "    if not np.isfinite(atr[i]):\n"
    "        continue\n"
    "    threshold = max(float(atr[i]) * multiplier, 0.0)\n"
    "    if i == 0 or not np.isfinite(rope[i - 1]):\n"
    "        rope[i] = cl[i]\n"
    "        direction[i] = 0\n"
    "        continue\n"
    "    previous = rope[i - 1]\n"
    "    if cl[i] > previous + threshold:\n"
    "        rope[i] = cl[i] - threshold\n"
    "        direction[i] = 1\n"
    "    elif cl[i] < previous - threshold:\n"
    "        rope[i] = cl[i] + threshold\n"
    "        direction[i] = -1\n"
    "    else:\n"
    "        rope[i] = previous\n"
    "        direction[i] = direction[i - 1]\n"
    "\n"
    "long_marks = [float(low.iloc[i]) * 0.995 if direction[i] == 1 and direction[i - 1] != 1 else None for i in range(len(df))]\n"
    "short_marks = [float(high.iloc[i]) * 1.005 if direction[i] == -1 and direction[i - 1] != -1 else None for i in range(len(df))]\n"
    "rope_values = [None if not np.isfinite(v) else float(v) for v in rope]\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [{"name": "ATR Rope", "data": rope_values, "color": "#26A69A", "overlay": True}],\n'
    '    "signals": [\n'
    '        {"type": "buy", "text": "Rope↥", "data": long_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "Rope↧", "data": short_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)

compute = _atr_rope
