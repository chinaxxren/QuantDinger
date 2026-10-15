"""Reviewed backend calculation for the volume_oscillator indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _volume_oscillator(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast_period", 5, minimum=2, maximum=100)
    slow = _integer(params, "slow_period", 20, minimum=3, maximum=200)
    signal_period = _integer(params, "signal_period", 5, minimum=1, maximum=100)
    if fast >= slow:
        raise ValueError("invalid parameter: fast_period")
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    fast_average = volume.ewm(span=fast, adjust=False, min_periods=fast).mean()
    slow_average = volume.ewm(span=slow, adjust=False, min_periods=slow).mean()
    oscillator = 100 * (fast_average - slow_average) / slow_average.replace(0, np.nan)
    signal = oscillator.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    return _output(
        "Volume Oscillator",
        [
            _line("volume_oscillator", "Volume Oscillator", oscillator, color="#26a69a"),
            _line("volume_oscillator_signal", "Signal", signal, color="#ff6d00"),
        ],
    )


SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Volume Oscillator\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Shows the percentage difference between fast and slow volume EMAs. The\n"
    "# current bar is included in both trailing exponential averages.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Volume Oscillator"\n'
    'my_indicator_description = "Percentage difference between fast and slow volume averages."\n'
    "\n"
    "# @param fast_period int 5 Fast volume EMA period range=2:100:1\n"
    "# @param slow_period int 20 Slow volume EMA period range=3:200:1\n"
    "# @param signal_period int 5 Signal EMA period range=1:100:1\n"
    "\n"
    'fast_period = max(2, int(params.get("fast_period", 5)))\n'
    'slow_period = max(fast_period + 1, int(params.get("slow_period", 20)))\n'
    'signal_period = max(1, int(params.get("signal_period", 5)))\n'
    "\n"
    "df = df.copy()\n"
    'volume = df["volume"].astype(float).clip(lower=0.0)\n'
    "fast_volume = volume.ewm(span=fast_period, adjust=False, min_periods=fast_period).mean()\n"
    "slow_volume = volume.ewm(span=slow_period, adjust=False, min_periods=slow_period).mean()\n"
    "volume_oscillator = 100.0 * (fast_volume - slow_volume) / slow_volume.replace(0.0, np.nan)\n"
    "volume_oscillator = volume_oscillator.replace([np.inf, -np.inf], np.nan)\n"
    "signal = volume_oscillator.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if pd.isna(value) else float(value) for value in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Volume Oscillator", "data": plot_list(volume_oscillator), "color": "#26A69A", "overlay": False},\n'
    '        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)

compute = _volume_oscillator
