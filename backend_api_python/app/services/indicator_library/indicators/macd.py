"""Reviewed backend calculation for the macd indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _bar, _close, _ema, _integer, _line, _output, pd


def _macd(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast", 12)
    slow = _integer(params, "slow", 26, minimum=2)
    signal = _integer(params, "signal", 9)
    if fast >= slow:
        raise ValueError("invalid parameter: fast")
    close = _close(df)
    line = _ema(close, fast) - _ema(close, slow)
    signal_line = _ema(line, signal)
    histogram = line - signal_line
    return _output(
        "MACD",
        [
            _line("macd", f"MACD({fast},{slow})", line),
            _line("signal", f"SIGNAL({signal})", signal_line, color="#fa8c16"),
            _bar("histogram", "HIST", histogram),
        ],
    )


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] MACD\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Moving Average Convergence Divergence oscillator. Values render in a\n"
    "# separate pane; this indicator does not submit or manage orders.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] MACD"\n'
    'my_indicator_description = "MACD, signal line, and histogram shown in a separate chart pane."\n'
    "\n"
    "# @param fast int 12 Fast EMA period range=2:50:1\n"
    "# @param slow int 26 Slow EMA period range=3:100:1\n"
    "# @param signal int 9 Signal EMA period range=2:50:1\n"
    "\n"
    'fast = max(2, int(params.get("fast", 12)))\n'
    'slow = max(fast + 1, int(params.get("slow", 26)))\n'
    'signal_period = max(2, int(params.get("signal", 9)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float)\n'
    "macd_line = close.ewm(span=fast, adjust=False, min_periods=fast).mean() - close.ewm(\n"
    "    span=slow, adjust=False, min_periods=slow\n"
    ").mean()\n"
    "signal_line = macd_line.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()\n"
    "histogram = macd_line - signal_line\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(v) else float(v) for v in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "MACD", "data": plot_list(macd_line), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "Signal", "data": plot_list(signal_line), "color": "#FF6D00", "overlay": False},\n'
    '        {"name": "Histogram", "data": plot_list(histogram), "color": "#26A69A", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)

compute = _macd
