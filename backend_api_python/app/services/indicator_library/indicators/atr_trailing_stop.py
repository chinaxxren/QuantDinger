"""Reviewed backend calculation for the atr_trailing_stop indicator."""

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


def _atr_trailing_stop(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "atr_length", 14, minimum=2, maximum=100)
    multiplier = _number(params, "atr_multiplier", 3, minimum=0.5, maximum=8)
    source_name = str(params.get("source", "close")).lower()
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    source = (high + low) / 2 if source_name == "hl2" else close
    source_values = source.to_numpy()
    atr_values = _atr(df, period).to_numpy()
    high_values, low_values = high.to_numpy(), low.to_numpy()
    long_stop, short_stop = np.full(len(df), np.nan), np.full(len(df), np.nan)
    direction = np.zeros(len(df), dtype=int)
    for index in range(len(df)):
        if not np.isfinite(source_values[index]) or not np.isfinite(atr_values[index]):
            continue
        long_candidate = source_values[index] - multiplier * atr_values[index]
        short_candidate = source_values[index] + multiplier * atr_values[index]
        prev_direction = direction[index - 1] if index else 0
        prev_long = long_stop[index - 1] if index else np.nan
        prev_short = short_stop[index - 1] if index else np.nan
        if prev_direction >= 0:
            direction[index] = 1 if prev_direction == 0 or source_values[index] >= prev_long else -1
        else:
            direction[index] = -1 if source_values[index] <= prev_short else 1
        if direction[index] > 0:
            long_stop[index] = (
                max(prev_long, long_candidate) if np.isfinite(prev_long) and prev_direction > 0 else long_candidate
            )
            short_stop[index] = short_candidate
        else:
            short_stop[index] = (
                min(prev_short, short_candidate) if np.isfinite(prev_short) and prev_direction < 0 else short_candidate
            )
            long_stop[index] = long_candidate
    active = np.where(direction > 0, long_stop, short_stop)
    previous_direction = np.concatenate(([0], direction[:-1]))
    buys, sells = (direction > 0) & (previous_direction <= 0), (direction < 0) & (previous_direction >= 0)
    return {
        **_output(
            "ATR Trailing Stop",
            [
                _line("atr_stop", "ATR Stop", active, overlay=True, color="#ffb300"),
                _line("atr_long_stop", "Long Stop", long_stop, overlay=True, color="#26a69a"),
                _line("atr_short_stop", "Short Stop", short_stop, overlay=True, color="#ef5350"),
            ],
        ),
        "signals": [
            {
                "type": "buy",
                "text": "ATR Buy",
                "data": [float(low_values[index]) * 0.995 if buys[index] else None for index in range(len(df))],
                "color": "#00c853",
            },
            {
                "type": "sell",
                "text": "ATR Sell",
                "data": [float(high_values[index]) * 1.005 if sells[index] else None for index in range(len(df))],
                "color": "#ff1744",
            },
        ],
    }


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] ATR Trailing Stop\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# A causal ATR trailing stop that follows the current close direction.\n"
    "# It is a chart-only overlay and does not submit or manage orders.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] ATR Trailing Stop"\n'
    'my_indicator_description = "Causal ATR trailing stop with direction flips and chart-only markers."\n'
    "\n"
    "# @param atr_length int 14 ATR lookback period range=2:100:1\n"
    "# @param atr_multiplier float 3.0 ATR distance multiplier range=0.5:8.0:0.1\n"
    "# @param source str close Price source choices=close,hl2\n"
    "\n"
    "try:\n"
    '    atr_length = max(2, min(100, int(params.get("atr_length", 14))))\n'
    "except (TypeError, ValueError):\n"
    "    atr_length = 14\n"
    "try:\n"
    '    atr_multiplier = float(params.get("atr_multiplier", 3.0))\n'
    "except (TypeError, ValueError):\n"
    "    atr_multiplier = 3.0\n"
    "if not np.isfinite(atr_multiplier):\n"
    "    atr_multiplier = 3.0\n"
    "atr_multiplier = max(0.5, min(8.0, atr_multiplier))\n"
    'source_name = str(params.get("source", "close")).strip().lower()\n'
    "\n"
    "frame = df.copy()\n"
    'high = frame["high"].astype(float)\n'
    'low = frame["low"].astype(float)\n'
    'close = frame["close"].astype(float)\n'
    'source = close if source_name != "hl2" else (high + low) / 2.0\n'
    "previous_close = close.shift(1)\n"
    "true_range = pd.concat(\n"
    "    [high - low, (high - previous_close).abs(), (low - previous_close).abs()],\n"
    "    axis=1,\n"
    ").max(axis=1)\n"
    "atr = true_range.ewm(\n"
    "    alpha=1.0 / atr_length,\n"
    "    adjust=False,\n"
    "    min_periods=atr_length,\n"
    ").mean()\n"
    "\n"
    "source_values = source.to_numpy(dtype=float)\n"
    "atr_values = atr.to_numpy(dtype=float)\n"
    "high_values = high.to_numpy(dtype=float)\n"
    "low_values = low.to_numpy(dtype=float)\n"
    "n = len(frame)\n"
    "long_stop = np.full(n, np.nan, dtype=float)\n"
    "short_stop = np.full(n, np.nan, dtype=float)\n"
    "direction = np.zeros(n, dtype=int)\n"
    "\n"
    "for i in range(n):\n"
    "    if not np.isfinite(source_values[i]) or not np.isfinite(atr_values[i]):\n"
    "        continue\n"
    "    long_candidate = source_values[i] - atr_multiplier * atr_values[i]\n"
    "    short_candidate = source_values[i] + atr_multiplier * atr_values[i]\n"
    "    previous_direction = direction[i - 1] if i else 0\n"
    "    previous_long = long_stop[i - 1] if i else np.nan\n"
    "    previous_short = short_stop[i - 1] if i else np.nan\n"
    "\n"
    "    if previous_direction >= 0:\n"
    "        direction[i] = 1 if previous_direction == 0 or source_values[i] >= previous_long else -1\n"
    "    else:\n"
    "        direction[i] = -1 if source_values[i] <= previous_short else 1\n"
    "\n"
    "    if direction[i] > 0:\n"
    "        long_stop[i] = (\n"
    "            max(previous_long, long_candidate)\n"
    "            if np.isfinite(previous_long) and previous_direction > 0\n"
    "            else long_candidate\n"
    "        )\n"
    "        short_stop[i] = short_candidate\n"
    "    else:\n"
    "        short_stop[i] = (\n"
    "            min(previous_short, short_candidate)\n"
    "            if np.isfinite(previous_short) and previous_direction < 0\n"
    "            else short_candidate\n"
    "        )\n"
    "        long_stop[i] = long_candidate\n"
    "\n"
    "active_stop = np.where(direction > 0, long_stop, short_stop)\n"
    "previous_direction = np.concatenate(([0], direction[:-1]))\n"
    "buy = (direction > 0) & (previous_direction <= 0)\n"
    "sell = (direction < 0) & (previous_direction >= 0)\n"
    "\n"
    "def _plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "buy_marks = [\n"
    "    float(low_values[i]) * 0.995 if buy[i] and np.isfinite(low_values[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "sell_marks = [\n"
    "    float(high_values[i]) * 1.005 if sell[i] and np.isfinite(high_values[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "ATR Stop", "data": _plot_list(active_stop), "color": "#FFB300", "overlay": True},\n'
    '        {"name": "Long Stop", "data": _plot_list(long_stop), "color": "#26A69A", "overlay": True},\n'
    '        {"name": "Short Stop", "data": _plot_list(short_stop), "color": "#EF5350", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "ATR Buy", "data": buy_marks, "color": "#00C853"},\n'
    '        {"type": "sell", "text": "ATR Sell", "data": sell_marks, "color": "#FF1744"},\n'
    "    ],\n"
    '    "layers": [],\n'
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "atr_length": atr_length,\n'
    '        "atr_multiplier": atr_multiplier,\n'
    '        "source": "hl2" if source_name == "hl2" else "close",\n'
    '        "direction": [int(value) for value in direction],\n'
    "    },\n"
    "}\n"
)

compute = _atr_trailing_stop
