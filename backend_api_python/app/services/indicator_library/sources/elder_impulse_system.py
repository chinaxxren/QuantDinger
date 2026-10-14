# ============================================================
# [Default] Elder Impulse System
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Combines EMA slope and MACD histogram slope into causal impulse states.
# States are exposed as chart markers only; no orders are submitted.
# ============================================================

my_indicator_name = "[Default] Elder Impulse System"
my_indicator_description = "EMA and MACD momentum impulse states with chart-only color markers."

# @param ema_length int 13 Trend EMA period range=2:100:1
# @param macd_fast int 12 MACD fast period range=2:100:1
# @param macd_slow int 26 MACD slow period range=3:200:1
# @param macd_signal int 9 MACD signal period range=2:100:1

def _int_param(name, default, minimum, maximum):
    try:
        value = int(params.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))

ema_length = _int_param("ema_length", 13, 2, 100)
macd_fast = _int_param("macd_fast", 12, 2, 100)
macd_slow = _int_param("macd_slow", 26, 3, 200)
if macd_slow <= macd_fast:
    macd_slow = min(200, macd_fast + 1)
macd_signal = _int_param("macd_signal", 9, 2, 100)

frame = df.copy()
close = frame["close"].astype(float)
ema = close.ewm(span=ema_length, adjust=False, min_periods=ema_length).mean()
fast = close.ewm(span=macd_fast, adjust=False, min_periods=macd_fast).mean()
slow = close.ewm(span=macd_slow, adjust=False, min_periods=macd_slow).mean()
macd = fast - slow
signal = macd.ewm(span=macd_signal, adjust=False, min_periods=macd_signal).mean()
histogram = macd - signal

ema_values = ema.to_numpy(dtype=float)
hist_values = histogram.to_numpy(dtype=float)
previous_ema = np.concatenate(([np.nan], ema_values[:-1]))
previous_hist = np.concatenate(([np.nan], hist_values[:-1]))
valid = (
    np.isfinite(ema_values)
    & np.isfinite(hist_values)
    & np.isfinite(previous_ema)
    & np.isfinite(previous_hist)
)
ema_rising = valid & (ema_values > previous_ema)
ema_falling = valid & (ema_values < previous_ema)
hist_rising = valid & (hist_values > previous_hist)
hist_falling = valid & (hist_values < previous_hist)
impulse = np.where(ema_rising & hist_rising, 1, np.where(ema_falling & hist_falling, -1, 0))

previous_impulse = np.concatenate(([0], impulse[:-1]))
buy = (impulse == 1) & (previous_impulse != 1)
sell = (impulse == -1) & (previous_impulse != -1)
high_values = frame["high"].astype(float).to_numpy(dtype=float)
low_values = frame["low"].astype(float).to_numpy(dtype=float)

def _plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

buy_marks = [float(low_values[i]) * 0.995 if buy[i] and np.isfinite(low_values[i]) else None for i in range(len(frame))]
sell_marks = [float(high_values[i]) * 1.005 if sell[i] and np.isfinite(high_values[i]) else None for i in range(len(frame))]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Impulse EMA", "data": _plot_list(ema_values), "color": "#42A5F5", "overlay": True},
        {"name": "MACD Histogram", "data": _plot_list(hist_values), "color": "#90CAF9", "overlay": False},
    ],
    "signals": [
        {"type": "buy", "text": "Impulse Up", "data": buy_marks, "color": "#00C853"},
        {"type": "sell", "text": "Impulse Down", "data": sell_marks, "color": "#FF1744"},
    ],
    "layers": [],
    "metadata": {
        "causal": True,
        "ema_length": ema_length,
        "macd_fast": macd_fast,
        "macd_slow": macd_slow,
        "macd_signal": macd_signal,
        "impulse": [int(value) for value in impulse],
    },
}
