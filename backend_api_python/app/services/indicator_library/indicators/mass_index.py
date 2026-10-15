"""Reviewed backend calculation for the mass_index indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _ema, _integer, _line, _output, _series, np, pd


def _mass_index(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    ema_period = _integer(params, "ema_period", 9, minimum=2, maximum=100)
    sum_period = _integer(params, "sum_period", 25, minimum=2, maximum=200)
    bar_range = (_series(df, "high") - _series(df, "low")).clip(lower=0)
    first = _ema(bar_range, ema_period)
    second = _ema(first, ema_period)
    values = (first / second.replace(0, np.nan)).rolling(sum_period, min_periods=sum_period).sum()
    return _output("Mass Index", [_line("mass_index", "Mass Index", values, color="#ab47bc")])


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Mass Index\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Sums the ratio of a range EMA to its second EMA over a trailing window.\n"
    "# This volatility-expansion measure is causal and does not imply trade signals.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Mass Index"\n'
    'my_indicator_description = "Range-expansion index from double-smoothed high-low movement."\n'
    "\n"
    "# @param ema_period int 9 Range EMA period range=2:100:1\n"
    "# @param sum_period int 25 Rolling sum period range=2:200:1\n"
    "\n"
    'aema_period = max(2, int(params.get("ema_period", 9)))\n'
    'sum_period = max(2, int(params.get("sum_period", 25)))\n'
    "\n"
    "df = df.copy()\n"
    'bar_range = (df["high"].astype(float) - df["low"].astype(float)).clip(lower=0.0)\n'
    "first_ema = bar_range.ewm(span=aema_period, adjust=False, min_periods=aema_period).mean()\n"
    "second_ema = first_ema.ewm(span=aema_period, adjust=False, min_periods=aema_period).mean()\n"
    "ema_ratio = first_ema / second_ema.replace(0.0, np.nan)\n"
    "mass_index = ema_ratio.rolling(sum_period, min_periods=sum_period).sum()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Mass Index", "data": plot_list(mass_index), "color": "#AB47BC", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)

compute = _mass_index
