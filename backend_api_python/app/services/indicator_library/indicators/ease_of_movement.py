"""Reviewed backend calculation for the ease_of_movement indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _number, _output, _series, np, pd


def _ease_of_movement(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14, minimum=2, maximum=200)
    volume_divisor = _number(params, "volume_divisor", 10000, minimum=1, maximum=1_000_000_000)
    high, low = _series(df, "high"), _series(df, "low")
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    midpoint = (high + low) / 2
    box_ratio = (volume / volume_divisor) / (high - low).replace(0, np.nan)
    raw = midpoint.diff() / box_ratio.replace(0, np.nan)
    values = raw.rolling(period, min_periods=period).mean()
    return _output("Ease of Movement", [_line("ease_of_movement", f"EOM({period})", values, color="#26a69a")])


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Ease of Movement\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Relates midpoint price movement to the range and volume of each bar, then\n"
    "# smooths it with a trailing simple average. Zero-volume bars remain undefined.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Ease of Movement"\n'
    'my_indicator_description = "Volume-normalized price movement with a smoothed EOM line."\n'
    "\n"
    "# @param period int 14 Smoothing period range=2:200:1\n"
    "# @param volume_divisor float 10000.0 Volume scaling divisor range=1.0:1000000000.0:1.0\n"
    "\n"
    'period = max(2, int(params.get("period", 14)))\n'
    'volume_divisor = max(1.0, float(params.get("volume_divisor", 10000.0)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'volume = df["volume"].astype(float).clip(lower=0.0)\n'
    "midpoint = (high + low) / 2.0\n"
    "midpoint_move = midpoint.diff()\n"
    "box_ratio = (volume / volume_divisor) / (high - low).replace(0.0, np.nan)\n"
    "eom_raw = midpoint_move / box_ratio.replace(0.0, np.nan)\n"
    "eom = eom_raw.rolling(period, min_periods=period).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "EOM", "data": plot_list(eom), "color": "#26A69A", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)

compute = _ease_of_movement
