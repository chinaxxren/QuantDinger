# ============================================================
# [Sample] SuperTrend Trend-Following -- classic ATR channel flip
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# This is a chart-only indicator. It never opens, closes, sizes, or manages
# trades. Convert it to a Strategy API source before backtesting or live trading.
# ============================================================

my_indicator_name = "[Sample] SuperTrend Trend-Following"
my_indicator_description = (
    "Classic SuperTrend: ATR-channel direction flip with chart-only bullish "
    "and bearish markers."
)

# @param atr_period int 10 ATR Wilder smoothing period range=7:21:1
# @param multiplier float 3.0 ATR band multiplier range=1.5:5.0:0.5

atr_period = int(params.get("atr_period", 10))
multiplier = float(params.get("multiplier", 3.0))

df = df.copy()
high = df["high"]
low = df["low"]
close = df["close"]
prev_close = close.shift(1)

tr = pd.concat([
    high - low,
    (high - prev_close).abs(),
    (low - prev_close).abs(),
], axis=1).max(axis=1)
atr = tr.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()

hl2 = (high + low) / 2.0
upper_basic = hl2 + multiplier * atr
lower_basic = hl2 - multiplier * atr

n = len(df)
ub = upper_basic.to_numpy()
lb = lower_basic.to_numpy()
cl = close.to_numpy()

final_upper = np.full(n, np.nan)
final_lower = np.full(n, np.nan)
direction = np.zeros(n, dtype=np.int8)
supertrend = np.full(n, np.nan)
start_idx = int(atr_period)

for i in range(n):
    if i < start_idx or np.isnan(ub[i]) or np.isnan(lb[i]):
        continue

    if i == start_idx or direction[i - 1] == 0:
        final_upper[i] = ub[i]
        final_lower[i] = lb[i]
        direction[i] = 1 if cl[i] >= (ub[i] + lb[i]) / 2.0 else -1
        supertrend[i] = final_lower[i] if direction[i] == 1 else final_upper[i]
        continue

    final_upper[i] = ub[i] if (ub[i] < final_upper[i - 1]) or (cl[i - 1] > final_upper[i - 1]) else final_upper[i - 1]
    final_lower[i] = lb[i] if (lb[i] > final_lower[i - 1]) or (cl[i - 1] < final_lower[i - 1]) else final_lower[i - 1]

    if cl[i] > final_upper[i - 1]:
        direction[i] = 1
    elif cl[i] < final_lower[i - 1]:
        direction[i] = -1
    else:
        direction[i] = direction[i - 1]

    supertrend[i] = final_lower[i] if direction[i] == 1 else final_upper[i]

prev_direction = np.concatenate([[0], direction[:-1]])
flip_long = (direction == 1) & (prev_direction == -1)
flip_short = (direction == -1) & (prev_direction == 1)

supertrend_up = [float(v) if (d == 1 and not np.isnan(v)) else None for v, d in zip(supertrend, direction)]
supertrend_dn = [float(v) if (d == -1 and not np.isnan(v)) else None for v, d in zip(supertrend, direction)]

long_marks = [float(low.iloc[i]) * 0.995 if bool(flip_long[i]) else None for i in range(n)]
short_marks = [float(high.iloc[i]) * 1.005 if bool(flip_short[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "SuperTrend Up", "data": supertrend_up, "color": "#00E676", "overlay": True},
        {"name": "SuperTrend Down", "data": supertrend_dn, "color": "#FF5252", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "L", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "S", "data": short_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
