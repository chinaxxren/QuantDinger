"""Reviewed backend calculation for the ultimate_oscillator indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _ultimate_oscillator(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    short = _integer(params, "short_period", 7, minimum=2, maximum=100)
    medium = _integer(params, "medium_period", 14, minimum=3, maximum=150)
    long = _integer(params, "long_period", 28, minimum=4, maximum=250)
    if not short < medium < long:
        raise ValueError("invalid parameter: period ordering")
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    previous_close = close.shift(1)
    true_low = pd.concat([low, previous_close], axis=1).min(axis=1)
    true_high = pd.concat([high, previous_close], axis=1).max(axis=1)
    buying_pressure = close - true_low
    true_range = (true_high - true_low).clip(lower=0)

    def ratio(period: int) -> pd.Series:
        pressure_sum = buying_pressure.rolling(period, min_periods=period).sum()
        range_sum = true_range.rolling(period, min_periods=period).sum().replace(0, np.nan)
        return pressure_sum / range_sum

    values = (100 * (4 * ratio(short) + 2 * ratio(medium) + ratio(long)) / 7).clip(0, 100)
    return _output("Ultimate Oscillator", [_line("ultimate_oscillator", "Ultimate Oscillator", values)])


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Ultimate Oscillator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Combines buying-pressure ratios over three causal lookback horizons to\n"
    "# reduce timeframe sensitivity. Only current and prior OHLC values are used.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Ultimate Oscillator"\n'
    'my_indicator_description = "Buying-pressure oscillator combining three lookback horizons."\n'
    "\n"
    "# @param short_period int 7 Short buying-pressure period range=2:100:1\n"
    "# @param medium_period int 14 Medium buying-pressure period range=3:150:1\n"
    "# @param long_period int 28 Long buying-pressure period range=4:250:1\n"
    "\n"
    'short_period = max(2, int(params.get("short_period", 7)))\n'
    'medium_period = max(short_period + 1, int(params.get("medium_period", 14)))\n'
    'long_period = max(medium_period + 1, int(params.get("long_period", 28)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "previous_close = close.shift(1)\n"
    "true_low = pd.concat([low, previous_close], axis=1).min(axis=1)\n"
    "true_high = pd.concat([high, previous_close], axis=1).max(axis=1)\n"
    "buying_pressure = close - true_low\n"
    "true_range = (true_high - true_low).clip(lower=0.0)\n"
    "\n"
    "def buying_pressure_ratio(period):\n"
    "    pressure_sum = buying_pressure.rolling(period, min_periods=period).sum()\n"
    "    range_sum = true_range.rolling(period, min_periods=period).sum()\n"
    "    return pressure_sum / range_sum.replace(0.0, np.nan)\n"
    "\n"
    "short_ratio = buying_pressure_ratio(short_period)\n"
    "medium_ratio = buying_pressure_ratio(medium_period)\n"
    "long_ratio = buying_pressure_ratio(long_period)\n"
    "oscillator = 100.0 * (4.0 * short_ratio + 2.0 * medium_ratio + long_ratio) / 7.0\n"
    "oscillator = oscillator.replace([np.inf, -np.inf], np.nan).clip(0.0, 100.0)\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Ultimate Oscillator", "data": plot_list(oscillator), "color": "#2962FF", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)

compute = _ultimate_oscillator
