# ============================================================
# [Default] Twin Range Filter
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Colinmck's Twin Range Filter. Two independently smoothed ranges are
# averaged into one causal filter, with chart-only Long/Short markers.
# ============================================================

my_indicator_name = "[Default] Twin Range Filter"
my_indicator_description = (
    "Twin smoothed range filter with configurable source and chart-only Long/Short signals."
)

# @param source string close Source price: close, open, high, low, hl2, hlc3, or ohlc4
# @param per1 int 27 Fast filter period range=2:200:1
# @param mult1 float 1.6 Fast filter multiplier range=0.1:10.0:0.1
# @param per2 int 55 Slow filter period range=2:300:1
# @param mult2 float 2.0 Slow filter multiplier range=0.1:10.0:0.1

source_name = str(params.get("source", "close")).strip().lower()
per1 = max(2, int(params.get("per1", params.get("fast_period", 27))))
mult1 = max(0.1, float(params.get("mult1", params.get("fast_multiplier", 1.6))))
per2 = max(2, int(params.get("per2", params.get("slow_period", 55))))
mult2 = max(0.1, float(params.get("mult2", params.get("slow_multiplier", 2.0))))

df = df.copy()
open_values = df["open"].astype(float)
high_series = df["high"].astype(float)
low_series = df["low"].astype(float)
close_series = df["close"].astype(float)

if source_name == "open":
    source_series = open_values
elif source_name == "high":
    source_series = high_series
elif source_name == "low":
    source_series = low_series
elif source_name == "hl2":
    source_series = (high_series + low_series) / 2.0
elif source_name == "hlc3":
    source_series = (high_series + low_series + close_series) / 3.0
elif source_name == "ohlc4":
    source_series = (open_values + high_series + low_series + close_series) / 4.0
else:
    source_name = "close"
    source_series = close_series

source = source_series.to_numpy()
n = len(df)
price_delta = source_series.diff().abs().fillna(0.0)

def smooth_range(period, multiplier):
    average_range = price_delta.ewm(span=period, adjust=False).mean()
    return (
        average_range.ewm(span=max(1, period * 2 - 1), adjust=False).mean()
        * multiplier
    ).to_numpy()

range_values = (smooth_range(per1, mult1) + smooth_range(per2, mult2)) / 2.0
filt = np.full(n, np.nan, dtype=float)
upward = np.zeros(n, dtype=float)
downward = np.zeros(n, dtype=float)
if n > 0 and np.isfinite(source[0]):
    filt[0] = source[0]

# Apply the Pine rngfilt ratchet: price must cross the current range edge
# before the filter moves; otherwise the previous filter value is retained.
for i in range(1, n):
    value = source[i]
    previous = filt[i - 1]
    width = range_values[i]
    if not np.isfinite(value) or not np.isfinite(previous) or not np.isfinite(width):
        continue

    if value > previous:
        filt[i] = previous if value - width < previous else value - width
    else:
        filt[i] = previous if value + width > previous else value + width

    if filt[i] > previous:
        upward[i] = upward[i - 1] + 1.0
        downward[i] = 0.0
    elif filt[i] < previous:
        downward[i] = downward[i - 1] + 1.0
        upward[i] = 0.0
    else:
        upward[i] = upward[i - 1]
        downward[i] = downward[i - 1]

previous_source = np.concatenate([[np.nan], source[:-1]])
source_moved = np.isfinite(source) & np.isfinite(previous_source) & (source != previous_source)
long_condition = (
    np.isfinite(source)
    & np.isfinite(filt)
    & (source > filt)
    & (upward > 0)
    & source_moved
)
short_condition = (
    np.isfinite(source)
    & np.isfinite(filt)
    & (source < filt)
    & (downward > 0)
    & source_moved
)

condition_state = np.zeros(n, dtype=np.int8)
long_signal = np.zeros(n, dtype=bool)
short_signal = np.zeros(n, dtype=bool)
state = 0
for i in range(n):
    if long_condition[i]:
        long_signal[i] = state == -1
        state = 1
    elif short_condition[i]:
        short_signal[i] = state == 1
        state = -1
    condition_state[i] = state


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

low = low_series.to_numpy()
high = high_series.to_numpy()
long_marks = [
    float(low[i]) * 0.995 if long_signal[i] and np.isfinite(low[i]) else None
    for i in range(n)
]
short_marks = [
    float(high[i]) * 1.005 if short_signal[i] and np.isfinite(high[i]) else None
    for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Twin Range Filter", "data": plot_list(filt), "color": "#2962FF", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "Long", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "Short", "data": short_marks, "color": "#FF5252"},
    ],
    "metadata": {
        "source": source_name,
        "upward": [float(value) if value else None for value in upward],
        "downward": [float(value) if value else None for value in downward],
        "condition_state": [int(value) if value else None for value in condition_state],
        "causal": True,
    },
    "layers": [],
}
