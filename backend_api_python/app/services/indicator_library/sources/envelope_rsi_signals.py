# ============================================================
# [Default] Envelope RSI Signals
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# RSI envelope with causal threshold-crossing markers. Signals are visual only.
# ============================================================

my_indicator_name = "[Default] Envelope RSI Signals"
my_indicator_description = "RSI volatility envelope with causal oversold and overbought reversal signals."

# @param rsi_length int 14 RSI lookback range=2:50:1
# @param envelope_length int 20 Envelope smoothing lookback range=2:100:1
# @param envelope_multiplier float 1.5 Envelope deviation multiplier range=0.1:5.0:0.1
# @param show_envelope bool True Show RSI envelope bands


def _clamp_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _clamp_float(value, default, minimum, maximum):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    if not np.isfinite(parsed):
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


rsi_length = _clamp_int(params.get("rsi_length", 14), 14, 2, 50)
envelope_length = _clamp_int(params.get("envelope_length", 20), 20, 2, 100)
envelope_multiplier = _clamp_float(params.get("envelope_multiplier", 1.5), 1.5, 0.1, 5.0)
show_envelope = _as_bool(params.get("show_envelope", True), True)

frame = df.copy()
close = frame["close"].astype(float)
delta = close.diff()
gain = delta.clip(lower=0.0)
loss = (-delta).clip(lower=0.0)
avg_gain = gain.ewm(alpha=1.0 / rsi_length, adjust=False, min_periods=rsi_length).mean()
avg_loss = loss.ewm(alpha=1.0 / rsi_length, adjust=False, min_periods=rsi_length).mean()
up = avg_gain.to_numpy(dtype=float)
down = avg_loss.to_numpy(dtype=float)
rsi = np.full(len(frame), np.nan, dtype=float)
valid = np.isfinite(up) & np.isfinite(down)
rsi[valid & (down <= 0.0) & (up > 0.0)] = 100.0
rsi[valid & (up <= 0.0) & (down > 0.0)] = 0.0
rsi[valid & (up <= 0.0) & (down <= 0.0)] = 50.0
normal = valid & (up > 0.0) & (down > 0.0)
rsi[normal] = 100.0 - 100.0 / (1.0 + up[normal] / down[normal])

rsi_series = pd.Series(rsi, index=frame.index)
basis = rsi_series.ewm(span=envelope_length, adjust=False, min_periods=envelope_length).mean().to_numpy(dtype=float)
deviation = rsi_series.rolling(envelope_length, min_periods=envelope_length).std(ddof=0).to_numpy(dtype=float)
upper = np.clip(basis + envelope_multiplier * deviation, 0.0, 100.0)
lower = np.clip(basis - envelope_multiplier * deviation, 0.0, 100.0)

previous_rsi = np.concatenate(([np.nan], rsi[:-1]))
previous_upper = np.concatenate(([np.nan], upper[:-1]))
previous_lower = np.concatenate(([np.nan], lower[:-1]))
finite = np.isfinite(rsi) & np.isfinite(basis)
buy = finite & np.isfinite(previous_rsi) & np.isfinite(previous_lower) & (previous_rsi <= previous_lower) & (rsi > lower)
sell = finite & np.isfinite(previous_rsi) & np.isfinite(previous_upper) & (previous_rsi >= previous_upper) & (rsi < upper)

if not show_envelope:
    upper = np.full(len(frame), np.nan, dtype=float)
    lower = np.full(len(frame), np.nan, dtype=float)

close_values = frame["close"].astype(float).to_numpy(dtype=float)
low_values = frame["low"].astype(float).to_numpy(dtype=float)
high_values = frame["high"].astype(float).to_numpy(dtype=float)
buy_marks = [float(rsi[i]) if buy[i] and np.isfinite(rsi[i]) else None for i in range(len(frame))]
sell_marks = [float(rsi[i]) if sell[i] and np.isfinite(rsi[i]) else None for i in range(len(frame))]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "RSI", "data": _plot_list(rsi), "color": "#7E57C2", "overlay": False, "width": 2},
        {"name": "RSI Basis", "data": _plot_list(basis), "color": "#FFB300", "overlay": False},
        {"name": "Envelope Upper", "data": _plot_list(upper), "color": "#EF5350", "overlay": False},
        {"name": "Envelope Lower", "data": _plot_list(lower), "color": "#26A69A", "overlay": False},
    ],
    "signals": [
        {"type": "buy", "text": "RSI Buy", "data": buy_marks, "color": "#00C853"},
        {"type": "sell", "text": "RSI Sell", "data": sell_marks, "color": "#FF1744"},
    ],
    "layers": [],
    "metadata": {
        "causal": True,
        "rsi_length": rsi_length,
        "envelope_length": envelope_length,
        "envelope_multiplier": envelope_multiplier,
        "show_envelope": show_envelope,
        "overbought": 70.0,
        "oversold": 30.0,
    },
}
