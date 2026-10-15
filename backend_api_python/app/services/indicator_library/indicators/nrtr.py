"""Reviewed backend calculation for the nrtr indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _number, _output, _series, np, pd


def _nrtr(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    percentage = _number(params, "percentage", 1, minimum=0.25, maximum=5)
    volatility_multiplier = _number(params, "mult", 0, minimum=0, maximum=3)
    period = _integer(params, "length", 20, minimum=5, maximum=100)
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    closes = close.to_numpy()
    average = close.rolling(period, min_periods=period).mean().to_numpy()
    std = close.rolling(period, min_periods=period).std(ddof=0).to_numpy()
    long_stop, short_stop, trend = np.full(len(df), np.nan), np.full(len(df), np.nan), np.zeros(len(df), dtype=int)
    peak = trough = active = np.nan
    for index in range(len(df)):
        if index < period or not np.isfinite(closes[index]):
            continue
        rate = percentage / 100
        if (
            volatility_multiplier > 0
            and np.isfinite(average[index])
            and average[index] != 0
            and np.isfinite(std[index])
        ):
            rate = max(0.0001, std[index] * volatility_multiplier / abs(average[index]))
        if trend[index - 1] >= 0 if index else True:
            peak = closes[index] if not np.isfinite(peak) else max(peak, closes[index])
            active = peak * (1 - rate)
            if closes[index] <= active:
                trend[index], trough, active = -1, closes[index], closes[index] * (1 + rate)
                short_stop[index] = active
            else:
                trend[index] = 1
                long_stop[index] = (
                    max(active, long_stop[index - 1]) if index and np.isfinite(long_stop[index - 1]) else active
                )
        else:
            trough = closes[index] if not np.isfinite(trough) else min(trough, closes[index])
            active = trough * (1 + rate)
            if closes[index] >= active:
                trend[index], peak, active = 1, closes[index], closes[index] * (1 - rate)
                long_stop[index] = active
            else:
                trend[index] = -1
                short_stop[index] = (
                    min(active, short_stop[index - 1]) if index and np.isfinite(short_stop[index - 1]) else active
                )
    previous = np.concatenate(([0], trend[:-1]))
    buys, sells = (trend == 1) & (previous == -1), (trend == -1) & (previous == 1)
    return {
        **_output(
            "NRTR",
            [
                _line("nrtr_long", "NRTR Long Stop", long_stop, overlay=True, color="#00e676"),
                _line("nrtr_short", "NRTR Short Stop", short_stop, overlay=True, color="#ff5252"),
            ],
        ),
        "signals": [
            {
                "type": "buy",
                "text": "NRTR+",
                "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))],
                "color": "#00e676",
            },
            {
                "type": "sell",
                "text": "NRTR-",
                "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))],
                "color": "#ff5252",
            },
        ],
    }


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] NRTR\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Nick Rypock Trailing Reverse percentage stop with optional volatility\n"
    "# adjustment. Trend flips are chart annotations only, never orders.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] NRTR"\n'
    'my_indicator_description = "Percentage-based trailing stop with optional volatility adjustment."\n'
    "\n"
    "# @param percentage float 1.0 Fixed stop percentage range=0.25:5.0:0.25\n"
    "# @param mult float 0.0 Volatility adjustment multiplier range=0.0:3.0:0.1\n"
    "# @param length int 20 Volatility lookback period range=5:100:1\n"
    "\n"
    'percentage = max(0.01, float(params.get("percentage", 1.0)))\n'
    'mult = max(0.0, float(params.get("mult", 0.0)))\n'
    'length = max(2, int(params.get("length", 20)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    "n = len(df)\n"
    "cl = close.to_numpy()\n"
    "mean = close.rolling(length, min_periods=length).mean().to_numpy()\n"
    "std = close.rolling(length, min_periods=length).std(ddof=0).to_numpy()\n"
    "long_stop = np.full(n, np.nan)\n"
    "short_stop = np.full(n, np.nan)\n"
    "trend = np.zeros(n, dtype=int)\n"
    "peak = trough = active_stop = np.nan\n"
    "for i in range(n):\n"
    "    if i < length or not np.isfinite(cl[i]):\n"
    "        continue\n"
    "    k = percentage / 100.0\n"
    "    if mult > 0.0 and np.isfinite(mean[i]) and mean[i] != 0.0 and np.isfinite(std[i]):\n"
    "        k = max(0.0001, std[i] * mult / abs(mean[i]))\n"
    "    if trend[i - 1] >= 0 if i > 0 else True:\n"
    "        peak = cl[i] if not np.isfinite(peak) else max(peak, cl[i])\n"
    "        active_stop = peak * (1.0 - k)\n"
    "        if cl[i] <= active_stop:\n"
    "            trend[i] = -1\n"
    "            trough = cl[i]\n"
    "            active_stop = trough * (1.0 + k)\n"
    "            short_stop[i] = active_stop\n"
    "        else:\n"
    "            trend[i] = 1\n"
    "            long_stop[i] = max(active_stop, long_stop[i - 1]) if i > 0 and np.isfinite(long_stop[i - 1]) else active_stop\n"
    "    else:\n"
    "        trough = cl[i] if not np.isfinite(trough) else min(trough, cl[i])\n"
    "        active_stop = trough * (1.0 + k)\n"
    "        if cl[i] >= active_stop:\n"
    "            trend[i] = 1\n"
    "            peak = cl[i]\n"
    "            active_stop = peak * (1.0 - k)\n"
    "            long_stop[i] = active_stop\n"
    "        else:\n"
    "            trend[i] = -1\n"
    "            short_stop[i] = min(active_stop, short_stop[i - 1]) if i > 0 and np.isfinite(short_stop[i - 1]) else active_stop\n"
    "    if i + 1 < n and trend[i + 1] == 0:\n"
    "        trend[i + 1] = trend[i]\n"
    "\n"
    "previous_trend = np.concatenate([[0], trend[:-1]])\n"
    "buy_flip = (trend == 1) & (previous_trend == -1)\n"
    "sell_flip = (trend == -1) & (previous_trend == 1)\n"
    "buy_marks = [float(low.iloc[i]) * 0.995 if bool(buy_flip[i]) else None for i in range(n)]\n"
    "sell_marks = [float(high.iloc[i]) * 1.005 if bool(sell_flip[i]) else None for i in range(n)]\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(v) else float(v) for v in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "NRTR Long Stop", "data": plot_list(long_stop), "color": "#00E676", "overlay": True},\n'
    '        {"name": "NRTR Short Stop", "data": plot_list(short_stop), "color": "#FF5252", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "NRTR+", "data": buy_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "NRTR-", "data": sell_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)

compute = _nrtr
