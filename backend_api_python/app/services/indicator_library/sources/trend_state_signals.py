# ============================================================
# [Default] Trend State Signals
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal adaptive step filter based on the trailing RMA of absolute price
# changes. Trend reversals are emitted as visual chart markers only.
# ============================================================

my_indicator_name = "[Default] Trend State Signals"
my_indicator_description = "Adaptive step filter with trend state and chart-only reversal markers."

# @param length int 20 RMA volatility lookback range=2:200:1
# @param multiplier float 3.5 Adaptive range multiplier range=0.1:10.0:0.1
# @param src_type string close Price source: close, hl2, hlc3, or ohlc4

length = max(2, int(params.get("length", 20)))
multiplier = max(0.1, float(params.get("multiplier", 3.5)))
src_type = str(params.get("src_type", "close")).lower()

df = df.copy()
open_price = df["open"].astype(float).to_numpy()
high = df["high"].astype(float).to_numpy()
low = df["low"].astype(float).to_numpy()
close = df["close"].astype(float).to_numpy()
if src_type == "hl2":
    source = (high + low) / 2.0
elif src_type == "hlc3":
    source = (high + low + close) / 3.0
elif src_type == "ohlc4":
    source = (open_price + high + low + close) / 4.0
else:
    source = close

n = len(source)
movement = np.full(n, np.nan, dtype=float)
if n > 1:
    movement[1:] = np.abs(np.diff(source))
movement_rma = np.full(n, np.nan, dtype=float)
adaptive_range = np.full(n, np.nan, dtype=float)

# Wilder RMA seeded by an SMA of the first complete window, matching Pine's
# ta.rma warm-up rather than pandas' differently seeded ewm implementation.
first_rma_index = length
if n > first_rma_index:
    seed = movement[1:first_rma_index + 1]
    if len(seed) == length and np.isfinite(seed).all():
        movement_rma[first_rma_index] = float(np.mean(seed))
        adaptive_range[first_rma_index] = movement_rma[first_rma_index] * multiplier
        for i in range(first_rma_index + 1, n):
            if np.isfinite(movement[i]) and np.isfinite(movement_rma[i - 1]):
                movement_rma[i] = (
                    movement_rma[i - 1] * (length - 1) + movement[i]
                ) / length
                adaptive_range[i] = movement_rma[i] * multiplier

filter_line = np.full(n, np.nan, dtype=float)
trend = np.zeros(n, dtype=int)
for i in range(first_rma_index, n):
    if not np.isfinite(source[i]) or not np.isfinite(adaptive_range[i]):
        if i > first_rma_index:
            filter_line[i] = filter_line[i - 1]
            trend[i] = trend[i - 1]
        continue

    if i == first_rma_index or not np.isfinite(filter_line[i - 1]):
        filter_line[i] = source[i]
        continue

    previous_filter = filter_line[i - 1]
    distance = adaptive_range[i]
    if source[i] > previous_filter + distance:
        filter_line[i] = source[i] - distance
    elif source[i] < previous_filter - distance:
        filter_line[i] = source[i] + distance
    else:
        filter_line[i] = previous_filter

    if filter_line[i] > previous_filter:
        trend[i] = 1
    elif filter_line[i] < previous_filter:
        trend[i] = -1
    else:
        trend[i] = trend[i - 1]

previous_trend = np.concatenate(([0], trend[:-1]))
long_signal = (trend == 1) & (previous_trend != 1) & (previous_trend != 0)
short_signal = (trend == -1) & (previous_trend != -1) & (previous_trend != 0)
buy_marks = [float(low[i]) * 0.995 if long_signal[i] and np.isfinite(low[i]) else None for i in range(n)]
sell_marks = [float(high[i]) * 1.005 if short_signal[i] and np.isfinite(high[i]) else None for i in range(n)]


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Step Filter", "data": plot_list(filter_line), "color": "#26A69A", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "TSS+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "TSS-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
