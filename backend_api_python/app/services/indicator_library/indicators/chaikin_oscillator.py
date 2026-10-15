"""Reviewed backend calculation for the chaikin_oscillator indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _chaikin_oscillator(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast_period", 3, minimum=1, maximum=100)
    slow = _integer(params, "slow_period", 10, minimum=2, maximum=200)
    if fast >= slow:
        raise ValueError("invalid parameter: fast_period")
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    multiplier = ((2 * close - high - low) / (high - low).replace(0, np.nan)).fillna(0)
    ad = (multiplier * volume).cumsum()
    values = (
        ad.ewm(span=fast, adjust=False, min_periods=fast).mean()
        - ad.ewm(span=slow, adjust=False, min_periods=slow).mean()
    )
    return _output("Chaikin Oscillator", [_line("chaikin_oscillator", "Chaikin Oscillator", values, color="#42a5f5")])


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Chaikin Oscillator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# The oscillator is the difference between fast and slow EMAs of the\n"
    "# accumulation/distribution line, using only current and prior bars.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Chaikin Oscillator"\n'
    'my_indicator_description = "Fast-minus-slow EMA of volume-weighted accumulation and distribution."\n'
    "\n"
    "# @param fast_period int 3 Fast EMA period range=1:100:1\n"
    "# @param slow_period int 10 Slow EMA period range=2:200:1\n"
    "\n"
    'fast_period = max(1, int(params.get("fast_period", 3)))\n'
    'slow_period = max(2, int(params.get("slow_period", 10)))\n'
    "if fast_period >= slow_period:\n"
    '    raise ValueError("fast_period must be less than slow_period")\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    'volume = df["volume"].astype(float).clip(lower=0.0)\n'
    "bar_range = high - low\n"
    "money_flow_multiplier = ((2.0 * close - high - low) / bar_range.replace(0.0, np.nan)).fillna(0.0)\n"
    "accumulation_distribution = (money_flow_multiplier * volume).cumsum()\n"
    "fast = accumulation_distribution.ewm(span=fast_period, adjust=False, min_periods=fast_period).mean()\n"
    "slow = accumulation_distribution.ewm(span=slow_period, adjust=False, min_periods=slow_period).mean()\n"
    "chaikin = fast - slow\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Chaikin Oscillator", "data": plot_list(chaikin), "color": "#42A5F5", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)

compute = _chaikin_oscillator
