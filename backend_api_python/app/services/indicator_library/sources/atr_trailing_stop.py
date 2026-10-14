# ============================================================
# [Default] ATR Trailing Stop
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# A causal ATR trailing stop that follows the current close direction.
# It is a chart-only overlay and does not submit or manage orders.
# ============================================================

my_indicator_name = "[Default] ATR Trailing Stop"
my_indicator_description = "Causal ATR trailing stop with direction flips and chart-only markers."

# @param atr_length int 14 ATR lookback period range=2:100:1
# @param atr_multiplier float 3.0 ATR distance multiplier range=0.5:8.0:0.1
# @param source str close Price source choices=close,hl2

try:
    atr_length = max(2, min(100, int(params.get("atr_length", 14))))
except (TypeError, ValueError):
    atr_length = 14
try:
    atr_multiplier = float(params.get("atr_multiplier", 3.0))
except (TypeError, ValueError):
    atr_multiplier = 3.0
if not np.isfinite(atr_multiplier):
    atr_multiplier = 3.0
atr_multiplier = max(0.5, min(8.0, atr_multiplier))
source_name = str(params.get("source", "close")).strip().lower()

frame = df.copy()
high = frame["high"].astype(float)
low = frame["low"].astype(float)
close = frame["close"].astype(float)
source = close if source_name != "hl2" else (high + low) / 2.0
previous_close = close.shift(1)
true_range = pd.concat(
    [high - low, (high - previous_close).abs(), (low - previous_close).abs()],
    axis=1,
).max(axis=1)
atr = true_range.ewm(
    alpha=1.0 / atr_length,
    adjust=False,
    min_periods=atr_length,
).mean()

source_values = source.to_numpy(dtype=float)
atr_values = atr.to_numpy(dtype=float)
high_values = high.to_numpy(dtype=float)
low_values = low.to_numpy(dtype=float)
n = len(frame)
long_stop = np.full(n, np.nan, dtype=float)
short_stop = np.full(n, np.nan, dtype=float)
direction = np.zeros(n, dtype=int)

for i in range(n):
    if not np.isfinite(source_values[i]) or not np.isfinite(atr_values[i]):
        continue
    long_candidate = source_values[i] - atr_multiplier * atr_values[i]
    short_candidate = source_values[i] + atr_multiplier * atr_values[i]
    previous_direction = direction[i - 1] if i else 0
    previous_long = long_stop[i - 1] if i else np.nan
    previous_short = short_stop[i - 1] if i else np.nan

    if previous_direction >= 0:
        direction[i] = 1 if previous_direction == 0 or source_values[i] >= previous_long else -1
    else:
        direction[i] = -1 if source_values[i] <= previous_short else 1

    if direction[i] > 0:
        long_stop[i] = (
            max(previous_long, long_candidate)
            if np.isfinite(previous_long) and previous_direction > 0
            else long_candidate
        )
        short_stop[i] = short_candidate
    else:
        short_stop[i] = (
            min(previous_short, short_candidate)
            if np.isfinite(previous_short) and previous_direction < 0
            else short_candidate
        )
        long_stop[i] = long_candidate

active_stop = np.where(direction > 0, long_stop, short_stop)
previous_direction = np.concatenate(([0], direction[:-1]))
buy = (direction > 0) & (previous_direction <= 0)
sell = (direction < 0) & (previous_direction >= 0)

def _plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

buy_marks = [
    float(low_values[i]) * 0.995 if buy[i] and np.isfinite(low_values[i]) else None
    for i in range(n)
]
sell_marks = [
    float(high_values[i]) * 1.005 if sell[i] and np.isfinite(high_values[i]) else None
    for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "ATR Stop", "data": _plot_list(active_stop), "color": "#FFB300", "overlay": True},
        {"name": "Long Stop", "data": _plot_list(long_stop), "color": "#26A69A", "overlay": True},
        {"name": "Short Stop", "data": _plot_list(short_stop), "color": "#EF5350", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "ATR Buy", "data": buy_marks, "color": "#00C853"},
        {"type": "sell", "text": "ATR Sell", "data": sell_marks, "color": "#FF1744"},
    ],
    "layers": [],
    "metadata": {
        "causal": True,
        "atr_length": atr_length,
        "atr_multiplier": atr_multiplier,
        "source": "hl2" if source_name == "hl2" else "close",
        "direction": [int(value) for value in direction],
    },
}
