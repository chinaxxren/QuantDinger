# ============================================================
# [Default] Market Structure Oscillator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal structure-position oscillator. No future pivots or orders are used.
# ============================================================

my_indicator_name = "[Default] Market Structure Oscillator"
my_indicator_description = "Causal market-structure position oscillator with trend confirmation and crossover markers."

# @param structure_length int 20 Structure lookback range=3:200:1
# @param signal_length int 5 Oscillator signal smoothing range=2:50:1
# @param volume_length int 20 Volume bias lookback range=2:200:1
# @param show_signal bool True Show signal line


def _clamp_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _as_bool(value, default):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in ("false", "0", "no", "off", "")


def _plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


structure_length = _clamp_int(params.get("structure_length", 20), 20, 3, 200)
signal_length = _clamp_int(params.get("signal_length", 5), 5, 2, 50)
volume_length = _clamp_int(params.get("volume_length", 20), 20, 2, 200)
show_signal = _as_bool(params.get("show_signal", True), True)

frame = df.copy()
high = frame["high"].astype(float)
low = frame["low"].astype(float)
close = frame["close"].astype(float)
volume = frame["volume"].astype(float)
n = len(frame)

# Use only completed bars before the current bar for structure boundaries.
prior_high = high.shift(1).rolling(structure_length, min_periods=structure_length).max().to_numpy(dtype=float)
prior_low = low.shift(1).rolling(structure_length, min_periods=structure_length).min().to_numpy(dtype=float)
close_values = close.to_numpy(dtype=float)
range_size = prior_high - prior_low
position = np.full(n, np.nan, dtype=float)
valid_range = np.isfinite(close_values) & np.isfinite(prior_high) & np.isfinite(prior_low) & (range_size > 0.0)
position[valid_range] = ((close_values[valid_range] - prior_low[valid_range]) / range_size[valid_range]) * 2.0 - 1.0

# A short EMA slope provides a causal trend component, while relative volume
# supplies a small confirmation term without changing the oscillator scale.
ema = close.ewm(span=signal_length, adjust=False, min_periods=signal_length).mean().to_numpy(dtype=float)
ema_previous = np.concatenate(([np.nan], ema[:-1]))
atr_like = (high - low).rolling(structure_length, min_periods=structure_length).mean().to_numpy(dtype=float)
trend_component = np.zeros(n, dtype=float)
valid_trend = np.isfinite(close_values) & np.isfinite(ema_previous) & np.isfinite(atr_like) & (atr_like > 0.0)
trend_component[valid_trend] = np.clip((close_values[valid_trend] - ema_previous[valid_trend]) / atr_like[valid_trend], -1.0, 1.0)

volume_average = volume.shift(1).rolling(volume_length, min_periods=volume_length).mean().to_numpy(dtype=float)
volume_bias = np.zeros(n, dtype=float)
volume_values = volume.to_numpy(dtype=float)
valid_volume = np.isfinite(volume_values) & np.isfinite(volume_average) & (volume_average > 0.0)
volume_bias[valid_volume] = np.clip((volume_values[valid_volume] / volume_average[valid_volume]) - 1.0, -1.0, 1.0)
candle_direction = np.sign(close_values - frame["open"].astype(float).to_numpy(dtype=float))
volume_component = np.nan_to_num(candle_direction * volume_bias, nan=0.0, posinf=0.0, neginf=0.0)

oscillator = 100.0 * (0.65 * position + 0.25 * trend_component + 0.10 * volume_component)
signal = pd.Series(oscillator, index=frame.index).ewm(span=signal_length, adjust=False, min_periods=signal_length).mean().to_numpy(dtype=float)
if not show_signal:
    signal = np.full(n, np.nan, dtype=float)

previous_oscillator = np.concatenate(([np.nan], oscillator[:-1]))
previous_signal = np.concatenate(([np.nan], signal[:-1]))
finite_cross = np.isfinite(oscillator) & np.isfinite(signal) & np.isfinite(previous_oscillator) & np.isfinite(previous_signal)
buy = finite_cross & (previous_oscillator <= previous_signal) & (oscillator > signal) & (oscillator < 0.0)
sell = finite_cross & (previous_oscillator >= previous_signal) & (oscillator < signal) & (oscillator > 0.0)

buy_marks = [float(oscillator[i]) if buy[i] else None for i in range(n)]
sell_marks = [float(oscillator[i]) if sell[i] else None for i in range(n)]
zero = [0.0] * n

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Structure Oscillator", "data": _plot_list(oscillator), "color": "#42A5F5", "overlay": False, "width": 2},
        {"name": "Signal", "data": _plot_list(signal), "color": "#FFB300", "overlay": False},
        {"name": "Zero", "data": zero, "color": "#777777", "overlay": False, "width": 1},
    ],
    "signals": [
        {"type": "buy", "text": "Bullish Structure", "data": buy_marks, "color": "#00C853"},
        {"type": "sell", "text": "Bearish Structure", "data": sell_marks, "color": "#FF1744"},
    ],
    "layers": [],
    "metadata": {
        "causal": True,
        "structure_length": structure_length,
        "signal_length": signal_length,
        "volume_length": volume_length,
        "show_signal": show_signal,
    },
}
