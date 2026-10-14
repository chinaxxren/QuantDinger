# ============================================================
# [Default] Pivot Point Supertrend
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Confirmed swing pivots define a causal centerline; ATR bands trail that
# centerline and switch direction on close crossings. No future bars used.
# ============================================================

my_indicator_name = "[Default] Pivot Point Supertrend"
my_indicator_description = "ATR trend bands centered on confirmed rolling swing pivots."

# @param pivot_period int 2 Pivot confirmation period range=1:20:1
# @param atr_period int 10 ATR period range=2:100:1
# @param multiplier float 3.0 ATR band multiplier range=0.25:10.0:0.25

pivot_period = max(1, int(params.get("pivot_period", 2)))
atr_period = max(2, int(params.get("atr_period", 10)))
multiplier = max(0.05, float(params.get("multiplier", 3.0)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
previous_close = close.shift(1)
true_range = pd.concat([
    high - low,
    (high - previous_close).abs(),
    (low - previous_close).abs(),
], axis=1).max(axis=1)
atr = true_range.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean().to_numpy()
# A pivot at bar t is only accepted at t + pivot_period, after all right-side
# confirmation bars are present. Rolling windows end on the confirmation bar.
window = 2 * pivot_period + 1
pivot_high_candidates = high.shift(pivot_period)
pivot_low_candidates = low.shift(pivot_period)
confirmed_high = pivot_high_candidates.where(pivot_high_candidates == high.rolling(window, min_periods=window).max())
confirmed_low = pivot_low_candidates.where(pivot_low_candidates == low.rolling(window, min_periods=window).min())
confirmed_high = confirmed_high.ffill().to_numpy()
confirmed_low = confirmed_low.ffill().to_numpy()
cl = close.to_numpy()
trend = np.zeros(len(df), dtype=int)
upper = np.full(len(df), np.nan)
lower = np.full(len(df), np.nan)
line = np.full(len(df), np.nan)
for i in range(len(df)):
    if not np.isfinite(atr[i]):
        continue
    if np.isfinite(confirmed_high[i]) and np.isfinite(confirmed_low[i]):
        pivot_center = (confirmed_high[i] + confirmed_low[i]) / 2.0
    elif np.isfinite(confirmed_high[i]):
        pivot_center = confirmed_high[i]
    elif np.isfinite(confirmed_low[i]):
        pivot_center = confirmed_low[i]
    else:
        pivot_center = cl[i]
    half_width = multiplier * float(atr[i])
    basic_upper = pivot_center + half_width
    basic_lower = pivot_center - half_width
    if i == 0 or not np.isfinite(line[i - 1]):
        trend[i] = 1 if cl[i] >= pivot_center else -1
        upper[i] = basic_upper
        lower[i] = basic_lower
    else:
        previous_trend = trend[i - 1]
        previous_upper = upper[i - 1]
        previous_lower = lower[i - 1]
        upper[i] = min(basic_upper, previous_upper) if previous_trend < 0 else basic_upper
        lower[i] = max(basic_lower, previous_lower) if previous_trend > 0 else basic_lower
        if previous_trend < 0 and cl[i] > previous_upper:
            trend[i] = 1
        elif previous_trend > 0 and cl[i] < previous_lower:
            trend[i] = -1
        else:
            trend[i] = previous_trend
    line[i] = lower[i] if trend[i] > 0 else upper[i]

previous_trend = np.concatenate([[0], trend[:-1]])
buy = (trend == 1) & (previous_trend == -1)
sell = (trend == -1) & (previous_trend == 1)

def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

low_values = low.to_numpy()
high_values = high.to_numpy()
buy_marks = [float(low_values[i]) * 0.995 if buy[i] else None for i in range(len(df))]
sell_marks = [float(high_values[i]) * 1.005 if sell[i] else None for i in range(len(df))]
output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Pivot Supertrend Up", "data": [float(line[i]) if trend[i] > 0 and np.isfinite(line[i]) else None for i in range(len(df))], "color": "#00E676", "overlay": True},
        {"name": "Pivot Supertrend Down", "data": [float(line[i]) if trend[i] < 0 and np.isfinite(line[i]) else None for i in range(len(df))], "color": "#FF5252", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "PPS+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "PPS-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
