"""Reviewed backend calculation for the ulcer_index indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, np, pd


def _ulcer_index(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14, minimum=2, maximum=200)
    close = _close(df)
    high = close.rolling(period, min_periods=period).max()
    drawdown = 100 * (close / high.replace(0, np.nan) - 1)
    values = drawdown.pow(2).rolling(period, min_periods=period).mean().pow(0.5)
    return _output("Ulcer Index", [_line("ulcer_index", "Ulcer Index", values, color="#ef5350")])


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Ulcer Index\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Computes the root-mean-square percentage drawdown from the trailing rolling\n"
    "# high. It measures downside depth and duration without using future prices.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Ulcer Index"\n'
    'my_indicator_description = "Rolling root-mean-square drawdown from recent highs."\n'
    "\n"
    "# @param period int 14 Drawdown and RMS lookback period range=2:200:1\n"
    "\n"
    'period = max(2, int(params.get("period", 14)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "rolling_high = close.rolling(period, min_periods=period).max()\n"
    "drawdown = 100.0 * (close / rolling_high.replace(0.0, np.nan) - 1.0)\n"
    "squared_drawdown = drawdown.pow(2)\n"
    "ulcer_index = squared_drawdown.rolling(period, min_periods=period).mean().pow(0.5)\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Ulcer Index", "data": plot_list(ulcer_index), "color": "#EF5350", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)

compute = _ulcer_index
