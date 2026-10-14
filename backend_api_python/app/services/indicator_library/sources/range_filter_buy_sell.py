# ============================================================
# [Default] Range Filter Buy and Sell
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Guikroth's Range Filter Buy and Sell variant. This indicator produces
# causal overlay lines and chart markers only; it does not execute trades.
# ============================================================

my_indicator_name = "[Default] Range Filter Buy and Sell"
my_indicator_description = (
    "Configurable-source range filter with directional bands and chart-only Buy/Sell signals."
)

# @param per int 100 Sampling period for the smoothed range range=2:200:1
# @param mult float 3.0 Range multiplier range=0.1:10.0:0.1
# @param source string close Source price: close, open, high, low, hl2, or hlc3

per = max(2, int(params.get("per", 100)))
mult = max(0.1, float(params.get("mult", 3.0)))
source_name = str(params.get("source", "close")).strip().lower()

_df = df.copy()
if source_name == "open":
    source_series = _df["open"].astype(float)
elif source_name == "high":
    source_series = _df["high"].astype(float)
elif source_name == "low":
    source_series = _df["low"].astype(float)
elif source_name == "hl2":
    source_series = ((_df["high"].astype(float) + _df["low"].astype(float)) / 2.0)
elif source_name == "hlc3":
    source_series = (
        _df["high"].astype(float)
        + _df["low"].astype(float)
        + _df["close"].astype(float)
    ) / 3.0
else:
    source_name = "close"
    source_series = _df["close"].astype(float)

high = _df["high"].astype(float).to_numpy()
low = _df["low"].astype(float).to_numpy()
source = source_series.to_numpy()
n = len(_df)

# The source indicator smooths absolute price changes twice before applying
# the range multiplier. adjust=False preserves the recursive EMA behavior.
source_delta = source_series.diff().abs().fillna(0.0)
avrng = source_delta.ewm(span=per, adjust=False).mean()
wper = max(1, per * 2 - 1)
smrng = avrng.ewm(span=wper, adjust=False).mean() * mult
range_values = smrng.to_numpy()

filt = np.full(n, np.nan, dtype=float)
upward = np.zeros(n, dtype=float)
downward = np.zeros(n, dtype=float)
if n > 0 and np.isfinite(source[0]):
    filt[0] = source[0]

# Range Filter ratchets only when price crosses the current channel edge.
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

# CondIni suppresses repeated markers while a condition remains active.
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

hband = filt + range_values
lband = filt - range_values

# Direction-colored filter segments use the source colors from the indicator.
# Include the transition point in both segments so lines remain connected.
filt_up = np.where(upward > 0, filt, np.nan)
filt_down = np.where(downward > 0, filt, np.nan)
for i in range(1, n):
    if upward[i] > 0 and downward[i - 1] > 0:
        filt_up[i - 1] = filt[i - 1]
        filt_up[i] = filt[i]
    elif downward[i] > 0 and upward[i - 1] > 0:
        filt_down[i - 1] = filt[i - 1]
        filt_down[i] = filt[i]


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

long_marks = [
    float(low[i]) if long_signal[i] and np.isfinite(low[i]) else None
    for i in range(n)
]
short_marks = [
    float(high[i]) if short_signal[i] and np.isfinite(high[i]) else None
    for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Filter", "data": plot_list(filt), "color": "#AAAAAA", "overlay": True},
        {"name": "Filter Up", "data": plot_list(filt_up), "color": "#CF1E1E", "overlay": True},
        {"name": "Filter Down", "data": plot_list(filt_down), "color": "#0000FF", "overlay": True},
        {"name": "Upper Band", "data": plot_list(hband), "color": "#4DDF48", "overlay": True},
        {"name": "Lower Band", "data": plot_list(lband), "color": "#0000FF", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "Buy", "data": long_marks, "color": "#AAAAAA"},
        {"type": "sell", "text": "Sell", "data": short_marks, "color": "#0000FF"},
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
