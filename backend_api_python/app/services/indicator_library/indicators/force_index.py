"""Reviewed backend calculation for the force_index indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, _series, pd


def _force_index(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 13, minimum=1, maximum=200)
    raw = _close(df).diff() * _series(df, "volume").fillna(0).clip(lower=0)
    values = raw.ewm(span=period, adjust=False, min_periods=period).mean()
    return _output("Force Index", [_line("force_index", f"Force Index({period})", values)])


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Force Index\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Force Index multiplies close-to-close change by traded volume and smooths\n"
    "# the result. The first bar is undefined because it has no prior close.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Force Index"\n'
    'my_indicator_description = "Volume-weighted price-change momentum with configurable EMA smoothing."\n'
    "\n"
    "# @param period int 13 EMA smoothing period range=1:200:1\n"
    "\n"
    'period = max(1, int(params.get("period", 13)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    'volume = df["volume"].astype(float).clip(lower=0.0)\n'
    "raw_force = close.diff() * volume\n"
    "force_index = raw_force.ewm(span=period, adjust=False, min_periods=period).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Force Index", "data": plot_list(force_index), "color": "#2962FF", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)

compute = _force_index
