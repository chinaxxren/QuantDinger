# ============================================================
# [Default] Range Filter B&S Signals
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal Range Filter B&S Signals implementation based on the
# VuManChu Swing Free / DonovanWall Range Filter formula.
# This source produces chart lines and visual markers only.
# ============================================================

my_indicator_name = "[Default] Range Filter B&S Signals"
my_indicator_description = (
    "Double-EMA range filter with directional bands and chart-only BUY/SELL signals."
)

# @param rng_per int 20 Swing period for the range EMA range=2:150:1
# @param rng_qty float 3.5 Swing multiplier for the filter width range=0.1:10.0:0.1

rng_per = max(2, int(params.get("rng_per", 20)))
rng_qty = max(0.1, float(params.get("rng_qty", 3.5)))

df = df.copy()
close = df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
source = close.to_numpy()
n = len(df)

# The original formula uses two exponential smoothers.  pandas EWM with
# adjust=False matches the recursive EMA form and does not use future bars.
price_delta = close.diff().abs().fillna(0.0)
avrng = price_delta.ewm(span=rng_per, adjust=False).mean()
wper = max(1, rng_per * 2 - 1)
rng = avrng.ewm(span=wper, adjust=False).mean() * rng_qty
range_values = rng.to_numpy()

filt = np.full(n, np.nan, dtype=float)
fdir = np.zeros(n, dtype=np.int8)
if n > 0 and np.isfinite(source[0]):
    filt[0] = source[0]

# Recursive Range Filter with the original ratchet behavior.
for i in range(1, n):
    value = source[i]
    previous = filt[i - 1]
    width = range_values[i]
    if not np.isfinite(value) or not np.isfinite(previous) or not np.isfinite(width):
        continue

    if value - width > previous:
        filt[i] = value - width
    elif value + width < previous:
        filt[i] = value + width
    else:
        filt[i] = previous

    if filt[i] > previous:
        fdir[i] = 1
    elif filt[i] < previous:
        fdir[i] = -1
    else:
        fdir[i] = fdir[i - 1]

# Carry the last known direction through bars where the filter is flat.
for i in range(1, n):
    if fdir[i] == 0:
        fdir[i] = fdir[i - 1]

long_condition = np.isfinite(source) & np.isfinite(filt) & (source > filt) & (fdir == 1)
short_condition = np.isfinite(source) & np.isfinite(filt) & (source < filt) & (fdir == -1)

# CondIni stores the most recent confirmed condition.  A marker is emitted
# only when the active condition changes, not on every bar in a trend.
cond_ini = np.zeros(n, dtype=np.int8)
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
    cond_ini[i] = state

upper_band = filt + range_values
lower_band = filt - range_values

# Keep the neutral filter and direction-colored segments separate.  The
# transition bar is included in both adjacent colored segments so the chart
# renderer can draw a continuous line without changing the existing layout.
filt_bull = np.where(fdir == 1, filt, np.nan)
filt_bear = np.where(fdir == -1, filt, np.nan)
for i in range(1, n):
    if fdir[i] == 1 and fdir[i - 1] == -1:
        filt_bull[i - 1] = filt[i - 1]
        filt_bull[i] = filt[i]
    elif fdir[i] == -1 and fdir[i - 1] == 1:
        filt_bear[i - 1] = filt[i - 1]
        filt_bear[i] = filt[i]


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

low_values = low.to_numpy()
high_values = high.to_numpy()
long_marks = [
    float(low_values[i]) * 0.995 if long_signal[i] and np.isfinite(low_values[i]) else None
    for i in range(n)
]
short_marks = [
    float(high_values[i]) * 1.005 if short_signal[i] and np.isfinite(high_values[i]) else None
    for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Filter", "data": plot_list(filt), "color": "#CCCCCC", "overlay": True},
        {"name": "Filter Bull", "data": plot_list(filt_bull), "color": "#05FF9B", "overlay": True},
        {"name": "Filter Bear", "data": plot_list(filt_bear), "color": "#FF0583", "overlay": True},
        {"name": "Upper Band", "data": plot_list(upper_band), "color": "#90CAF9", "overlay": True},
        {"name": "Lower Band", "data": plot_list(lower_band), "color": "#EF9A9A", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "BUY", "data": long_marks, "color": "#05FF9B"},
        {"type": "sell", "text": "SELL", "data": short_marks, "color": "#FF0583"},
    ],
    "metadata": {
        "direction": [int(value) if value else None for value in fdir],
        "condition_state": [int(value) if value else None for value in cond_ini],
        "causal": True,
        "source": "VuManChu Swing Free / DonovanWall Range Filter",
    },
    "layers": [],
}
