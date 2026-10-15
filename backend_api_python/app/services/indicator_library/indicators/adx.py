"""Reviewed backend calculation for the adx indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, _wilder, np, pd


def _adx(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 14)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    smooth_tr = _wilder(tr, period)
    smooth_plus = _wilder(plus_dm, period)
    smooth_minus = _wilder(minus_dm, period)
    plus_di = 100 * smooth_plus / smooth_tr.replace(0, np.nan)
    minus_di = 100 * smooth_minus / smooth_tr.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = _wilder(dx, period)
    return _output(
        "ADX",
        [
            _line("adx", f"ADX({period})", adx),
            _line("plus_di", "+DI", plus_di, color="#26a69a"),
            _line("minus_di", "-DI", minus_di, color="#ef5350"),
        ],
    )


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] ADX\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Average Directional Index with positive and negative directional indicators.\n"
    "# Values render in a separate pane and are informational only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] ADX"\n'
    'my_indicator_description = "Average Directional Index with +DI and -DI trend-strength lines."\n'
    "\n"
    "# @param length int 14 Wilder smoothing period range=3:50:1\n"
    "\n"
    'length = max(2, int(params.get("length", 14)))\n'
    "\n"
    "df = df.copy()\n"
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "previous_high = high.shift(1)\n"
    "previous_low = low.shift(1)\n"
    "previous_close = close.shift(1)\n"
    "up_move = high - previous_high\n"
    "down_move = previous_low - low\n"
    "plus_dm = up_move.where((up_move > down_move) & (up_move > 0.0), 0.0)\n"
    "minus_dm = down_move.where((down_move > up_move) & (down_move > 0.0), 0.0)\n"
    "true_range = pd.concat([\n"
    "    high - low,\n"
    "    (high - previous_close).abs(),\n"
    "    (low - previous_close).abs(),\n"
    "], axis=1).max(axis=1)\n"
    "smoothed_tr = true_range.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()\n"
    "plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean() / smoothed_tr.replace(0.0, np.nan)\n"
    "minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean() / smoothed_tr.replace(0.0, np.nan)\n"
    "directional_sum = (plus_di + minus_di).replace(0.0, np.nan)\n"
    "dx = 100.0 * (plus_di - minus_di).abs() / directional_sum\n"
    "adx = dx.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(v) else float(v) for v in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "ADX", "data": plot_list(adx), "color": "#FFA726", "overlay": False},\n'
    '        {"name": "+DI", "data": plot_list(plus_di), "color": "#26A69A", "overlay": False},\n'
    '        {"name": "-DI", "data": plot_list(minus_di), "color": "#EF5350", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)

compute = _adx
