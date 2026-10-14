# ============================================================
# [Default] Range Filter
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Volatility-adaptive filter line. Signals are chart markers only.
# ============================================================

my_indicator_name = "[Default] Range Filter"
my_indicator_description = "Adaptive price range filter with upper/lower bands and trend flip markers."

# @param sampling_period int 50 Range smoothing period range=10:150:5
# @param range_multiplier float 3.0 Smoothed range multiplier range=1.0:6.0:0.25

sampling_period = int(params.get("sampling_period", 50))
range_multiplier = float(params.get("range_multiplier", 3.0))

df = df.copy()
close = df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
n = len(df)

price_delta = close.diff().abs().fillna(0.0)
smooth_range = price_delta.ewm(span=sampling_period, adjust=False).mean()
smooth_range = smooth_range.ewm(span=max(1, sampling_period * 2 - 1), adjust=False).mean() * range_multiplier

cl = close.to_numpy()
rng = smooth_range.to_numpy()
filt = np.full(n, np.nan)
up_count = np.zeros(n, dtype=float)
down_count = np.zeros(n, dtype=float)

if n > 0:
    filt[0] = cl[0]

for i in range(1, n):
    previous = filt[i - 1]
    current_range = 0.0 if np.isnan(rng[i]) else rng[i]
    if cl[i] > previous:
        filt[i] = max(previous, cl[i] - current_range)
    else:
        filt[i] = min(previous, cl[i] + current_range)

    if filt[i] > filt[i - 1]:
        up_count[i] = up_count[i - 1] + 1
        down_count[i] = 0
    elif filt[i] < filt[i - 1]:
        down_count[i] = down_count[i - 1] + 1
        up_count[i] = 0
    else:
        up_count[i] = up_count[i - 1]
        down_count[i] = down_count[i - 1]

upper_band = filt + rng
lower_band = filt - rng
long_condition = (close.to_numpy() > filt) & (up_count > 0)
short_condition = (close.to_numpy() < filt) & (down_count > 0)
long_edge = long_condition & np.concatenate([[False], ~long_condition[:-1]])
short_edge = short_condition & np.concatenate([[False], ~short_condition[:-1]])

def plot_list(values):
    return [None if pd.isna(v) else float(v) for v in values]

long_marks = [float(low.iloc[i]) * 0.995 if bool(long_edge[i]) else None for i in range(n)]
short_marks = [float(high.iloc[i]) * 1.005 if bool(short_edge[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Range Filter", "data": plot_list(filt), "color": "#00BCD4", "overlay": True},
        {"name": "Upper Range", "data": plot_list(upper_band), "color": "#90CAF9", "overlay": True},
        {"name": "Lower Range", "data": plot_list(lower_band), "color": "#90CAF9", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "RF+", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "RF-", "data": short_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
