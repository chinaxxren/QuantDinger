"""Reviewed backend calculation for the range_filter indicator."""

from app.services.indicator_library.runtime import (
    Any,
    Mapping,
    _ema,
    _integer,
    _line,
    _number,
    _output,
    _series,
    np,
    pd,
)


def _range_filter(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "sampling_period", 50, minimum=10, maximum=150)
    multiplier = _number(params, "range_multiplier", 3, minimum=1, maximum=6)
    close, high, low = (_series(df, key) for key in ("close", "high", "low"))
    smooth_range = _ema(close.diff().abs().fillna(0), period)
    smooth_range = _ema(smooth_range, max(1, period * 2 - 1)) * multiplier
    closes, ranges = close.to_numpy(), smooth_range.to_numpy()
    filt = np.full(len(df), np.nan)
    up_count, down_count = np.zeros(len(df)), np.zeros(len(df))
    if len(df):
        filt[0] = closes[0]
    for index in range(1, len(df)):
        current_range = ranges[index] if np.isfinite(ranges[index]) else 0
        filt[index] = (
            max(filt[index - 1], closes[index] - current_range)
            if closes[index] > filt[index - 1]
            else min(filt[index - 1], closes[index] + current_range)
        )
        if filt[index] > filt[index - 1]:
            up_count[index], down_count[index] = up_count[index - 1] + 1, 0
        elif filt[index] < filt[index - 1]:
            down_count[index], up_count[index] = down_count[index - 1] + 1, 0
        else:
            up_count[index], down_count[index] = up_count[index - 1], down_count[index - 1]
    upper, lower = filt + ranges, filt - ranges
    long_condition, short_condition = (closes > filt) & (up_count > 0), (closes < filt) & (down_count > 0)
    previous_long, previous_short = (
        np.concatenate(([False], long_condition[:-1])),
        np.concatenate(([False], short_condition[:-1])),
    )
    buys, sells = long_condition & ~previous_long, short_condition & ~previous_short
    return {
        **_output(
            "Range Filter",
            [
                _line("range_filter", "Range Filter", filt, overlay=True, color="#00bcd4"),
                _line("range_upper", "Upper Range", upper, overlay=True, color="#90caf9"),
                _line("range_lower", "Lower Range", lower, overlay=True, color="#90caf9"),
            ],
        ),
        "signals": [
            {
                "type": "buy",
                "text": "RF+",
                "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))],
                "color": "#00e676",
            },
            {
                "type": "sell",
                "text": "RF-",
                "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))],
                "color": "#ff5252",
            },
        ],
    }


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Range Filter\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Volatility-adaptive filter line. Signals are chart markers only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Range Filter"\n'
    'my_indicator_description = "Adaptive price range filter with upper/lower bands and trend flip markers."\n'
    "\n"
    "# @param sampling_period int 50 Range smoothing period range=10:150:5\n"
    "# @param range_multiplier float 3.0 Smoothed range multiplier range=1.0:6.0:0.25\n"
    "\n"
    'sampling_period = int(params.get("sampling_period", 50))\n'
    'range_multiplier = float(params.get("range_multiplier", 3.0))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    "n = len(df)\n"
    "\n"
    "price_delta = close.diff().abs().fillna(0.0)\n"
    "smooth_range = price_delta.ewm(span=sampling_period, adjust=False).mean()\n"
    "smooth_range = smooth_range.ewm(span=max(1, sampling_period * 2 - 1), adjust=False).mean() * range_multiplier\n"
    "\n"
    "cl = close.to_numpy()\n"
    "rng = smooth_range.to_numpy()\n"
    "filt = np.full(n, np.nan)\n"
    "up_count = np.zeros(n, dtype=float)\n"
    "down_count = np.zeros(n, dtype=float)\n"
    "\n"
    "if n > 0:\n"
    "    filt[0] = cl[0]\n"
    "\n"
    "for i in range(1, n):\n"
    "    previous = filt[i - 1]\n"
    "    current_range = 0.0 if np.isnan(rng[i]) else rng[i]\n"
    "    if cl[i] > previous:\n"
    "        filt[i] = max(previous, cl[i] - current_range)\n"
    "    else:\n"
    "        filt[i] = min(previous, cl[i] + current_range)\n"
    "\n"
    "    if filt[i] > filt[i - 1]:\n"
    "        up_count[i] = up_count[i - 1] + 1\n"
    "        down_count[i] = 0\n"
    "    elif filt[i] < filt[i - 1]:\n"
    "        down_count[i] = down_count[i - 1] + 1\n"
    "        up_count[i] = 0\n"
    "    else:\n"
    "        up_count[i] = up_count[i - 1]\n"
    "        down_count[i] = down_count[i - 1]\n"
    "\n"
    "upper_band = filt + rng\n"
    "lower_band = filt - rng\n"
    "long_condition = (close.to_numpy() > filt) & (up_count > 0)\n"
    "short_condition = (close.to_numpy() < filt) & (down_count > 0)\n"
    "long_edge = long_condition & np.concatenate([[False], ~long_condition[:-1]])\n"
    "short_edge = short_condition & np.concatenate([[False], ~short_condition[:-1]])\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(v) else float(v) for v in values]\n"
    "\n"
    "long_marks = [float(low.iloc[i]) * 0.995 if bool(long_edge[i]) else None for i in range(n)]\n"
    "short_marks = [float(high.iloc[i]) * 1.005 if bool(short_edge[i]) else None for i in range(n)]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Range Filter", "data": plot_list(filt), "color": "#00BCD4", "overlay": True},\n'
    '        {"name": "Upper Range", "data": plot_list(upper_band), "color": "#90CAF9", "overlay": True},\n'
    '        {"name": "Lower Range", "data": plot_list(lower_band), "color": "#90CAF9", "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "RF+", "data": long_marks, "color": "#00E676"},\n'
    '        {"type": "sell", "text": "RF-", "data": short_marks, "color": "#FF5252"},\n'
    "    ],\n"
    '    "layers": [],\n'
    "}\n"
)

compute = _range_filter
