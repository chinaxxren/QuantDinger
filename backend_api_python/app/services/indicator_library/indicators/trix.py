"""Reviewed backend calculation for the trix indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _ema, _integer, _line, _output, pd


def _trix(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 12)
    smoothing = _integer(params, "smoothing", 1)
    close = _close(df)
    first = _ema(close, period)
    second = _ema(first, period)
    third = _ema(second, period)
    values = third.pct_change() * 100
    if smoothing > 1:
        values = values.rolling(smoothing, min_periods=smoothing).mean()
    return _output("Triple Exponential Average", [_line("trix", f"TRIX({period})", values)])


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] TRIX\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Triple-smoothed EMA rate of change. The percentage change compares with the\n"
    "# previous bar only and the signal is a trailing EMA, so the series is causal.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] TRIX"\n'
    'my_indicator_description = "Triple-smoothed EMA momentum with a signal line."\n'
    "\n"
    "# @param period int 15 Triple EMA period range=2:200:1\n"
    "# @param signal_period int 9 Signal EMA period range=2:100:1\n"
    "\n"
    'period = max(2, int(params.get("period", 15)))\n'
    'signal_period = max(2, int(params.get("signal_period", 9)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "ema1 = close.ewm(span=period, adjust=False, min_periods=period).mean()\n"
    "ema2 = ema1.ewm(span=period, adjust=False, min_periods=period).mean()\n"
    "ema3 = ema2.ewm(span=period, adjust=False, min_periods=period).mean()\n"
    "trix = 100.0 * ema3.pct_change(fill_method=None)\n"
    "trix = trix.replace([np.inf, -np.inf], np.nan)\n"
    "signal = trix.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "TRIX", "data": plot_list(trix), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)

compute = _trix
