# ============================================================
# [Default] PowerTrend Volume Range Filter
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# A native QuantDinger interpretation of a volume-confirmed range filter.
# Signals are chart markers only.
# ============================================================

my_indicator_name = "[Default] PowerTrend Volume Range Filter"
my_indicator_description = "Range Filter trend state confirmed by EMA power and relative volume expansion."

# @param range_period int 34 Range smoothing period range=10:120:2
# @param range_multiplier float 2.5 Range multiplier range=1.0:6.0:0.25
# @param fast_period int 21 Fast EMA period range=5:60:1
# @param slow_period int 55 Slow EMA period range=20:160:5
# @param volume_period int 34 Volume baseline period range=10:120:2
# @param min_relative_volume float 1.05 Minimum relative volume range=0.5:3.0:0.05

range_period = int(params.get("range_period", 34))
range_multiplier = float(params.get("range_multiplier", 2.5))
fast_period = int(params.get("fast_period", 21))
slow_period = int(params.get("slow_period", 55))
volume_period = int(params.get("volume_period", 34))
min_relative_volume = float(params.get("min_relative_volume", 1.05))

df = df.copy()
close = df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
volume = df.get("volume", pd.Series([0.0] * len(df), index=df.index)).astype(float)
n = len(df)

price_delta = close.diff().abs().fillna(0.0)
smooth_range = price_delta.ewm(span=range_period, adjust=False).mean()
smooth_range = smooth_range.ewm(span=max(1, range_period * 2 - 1), adjust=False).mean() * range_multiplier

cl = close.to_numpy()
rng = smooth_range.to_numpy()
filt = np.full(n, np.nan)
if n > 0:
    filt[0] = cl[0]
for i in range(1, n):
    previous = filt[i - 1]
    current_range = 0.0 if np.isnan(rng[i]) else rng[i]
    filt[i] = max(previous, cl[i] - current_range) if cl[i] > previous else min(previous, cl[i] + current_range)

ema_fast = close.ewm(span=fast_period, adjust=False).mean()
ema_slow = close.ewm(span=slow_period, adjust=False).mean()
power_line = ema_fast - ema_slow
volume_base = volume.ewm(span=volume_period, adjust=False).mean().replace(0, np.nan)
relative_volume = (volume / volume_base).replace([np.inf, -np.inf], np.nan).fillna(0.0)

range_trend_up = close.to_numpy() > filt
range_trend_down = close.to_numpy() < filt
power_up = power_line.to_numpy() > 0
power_down = power_line.to_numpy() < 0
volume_ok = relative_volume.to_numpy() >= min_relative_volume

long_condition = range_trend_up & power_up & volume_ok
short_condition = range_trend_down & power_down & volume_ok
long_edge = long_condition & np.concatenate([[False], ~long_condition[:-1]])
short_edge = short_condition & np.concatenate([[False], ~short_condition[:-1]])

def plot_list(values):
    return [None if pd.isna(v) else float(v) for v in values]

long_marks = [float(low.iloc[i]) * 0.995 if bool(long_edge[i]) else None for i in range(n)]
short_marks = [float(high.iloc[i]) * 1.005 if bool(short_edge[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Power Range Filter", "data": plot_list(filt), "color": "#00BCD4", "overlay": True},
        {"name": "Fast EMA", "data": plot_list(ema_fast), "color": "#FFB300", "overlay": True},
        {"name": "Slow EMA", "data": plot_list(ema_slow), "color": "#5C6BC0", "overlay": True},
        {"name": "Relative Volume", "data": plot_list(relative_volume), "color": "#26A69A", "overlay": False},
    ],
    "signals": [
        {"type": "buy", "text": "PT+", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "PT-", "data": short_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
