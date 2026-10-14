# ============================================================
# [Default] Volume Weighted MACD
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# MACD calculated from a volume-weighted price source. This is a chart-only
# oscillator and never submits or manages orders.
# ============================================================

my_indicator_name = "[Default] Volume Weighted MACD"
my_indicator_description = "MACD oscillator using a causal volume-weighted price with crossover markers."

# @param fast_length int 12 Fast EMA period range=2:100:1
# @param slow_length int 26 Slow EMA period range=3:200:1
# @param signal_length int 9 Signal EMA period range=2:100:1
# @param histogram bool True Show MACD histogram range=0:1:1

def _int_param(name, default, minimum, maximum):
    try:
        value = int(params.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))

def _as_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in ("false", "0", "no", "off", "")

fast_length = _int_param("fast_length", 12, 2, 100)
slow_length = _int_param("slow_length", 26, 3, 200)
if slow_length <= fast_length:
    slow_length = min(200, fast_length + 1)
signal_length = _int_param("signal_length", 9, 2, 100)
show_histogram = _as_bool(params.get("histogram", True), True)

frame = df.copy()
close = frame["close"].astype(float)
volume = frame.get("volume", pd.Series(0.0, index=frame.index)).astype(float)
volume = volume.clip(lower=0.0)
volume_sum = volume.rolling(slow_length, min_periods=1).sum()
weighted_sum = (close * volume).rolling(slow_length, min_periods=1).sum()
weighted_price = (weighted_sum / volume_sum.replace(0.0, np.nan)).where(volume_sum > 0.0, close)

fast = weighted_price.ewm(span=fast_length, adjust=False, min_periods=fast_length).mean()
slow = weighted_price.ewm(span=slow_length, adjust=False, min_periods=slow_length).mean()
macd = fast - slow
signal = macd.ewm(span=signal_length, adjust=False, min_periods=signal_length).mean()
hist = macd - signal

macd_values = macd.to_numpy(dtype=float)
signal_values = signal.to_numpy(dtype=float)
hist_values = hist.to_numpy(dtype=float)
previous_macd = np.concatenate(([np.nan], macd_values[:-1]))
previous_signal = np.concatenate(([np.nan], signal_values[:-1]))
finite = (
    np.isfinite(macd_values)
    & np.isfinite(signal_values)
    & np.isfinite(previous_macd)
    & np.isfinite(previous_signal)
)
buy = finite & (previous_macd <= previous_signal) & (macd_values > signal_values)
sell = finite & (previous_macd >= previous_signal) & (macd_values < signal_values)

if not show_histogram:
    hist_values = np.full(len(frame), np.nan, dtype=float)

def _plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "VW MACD", "data": _plot_list(macd_values), "color": "#26A69A", "overlay": False},
        {"name": "Signal", "data": _plot_list(signal_values), "color": "#FFB300", "overlay": False},
        {"name": "Histogram", "data": _plot_list(hist_values), "color": "#90CAF9", "overlay": False},
    ],
    "signals": [
        {"type": "buy", "text": "VW MACD+", "data": [float(value) if flag and np.isfinite(value) else None for value, flag in zip(macd_values, buy)], "color": "#00C853"},
        {"type": "sell", "text": "VW MACD-", "data": [float(value) if flag and np.isfinite(value) else None for value, flag in zip(macd_values, sell)], "color": "#FF1744"},
    ],
    "layers": [],
    "metadata": {
        "causal": True,
        "fast_length": fast_length,
        "slow_length": slow_length,
        "signal_length": signal_length,
        "histogram": show_histogram,
    },
}
