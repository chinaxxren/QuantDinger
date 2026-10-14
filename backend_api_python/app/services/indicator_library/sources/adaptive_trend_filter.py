# ============================================================
# [Default] Adaptive Trend Filter
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# A recursive variance-aware price estimator followed by an ATR supertrend.
# Both calculations are causal and intended for visual trend confirmation.
# ============================================================

my_indicator_name = "[Default] Adaptive Trend Filter"
my_indicator_description = "Variance-adaptive price filter with ATR supertrend bands."

# @param alpha_filter float 0.01 Filter responsiveness coefficient range=0.001:1.0:0.001
# @param beta_filter float 0.1 Process-noise coefficient range=0.001:2.0:0.001
# @param filter_period int 21 Filter scaling period range=2:100:1
# @param supertrend_factor float 1.0 ATR band multiplier range=0.25:8.0:0.25
# @param atr_period int 7 ATR period range=2:100:1

alpha_filter = max(0.0001, float(params.get("alpha_filter", 0.01)))
beta_filter = max(0.0001, float(params.get("beta_filter", 0.1)))
filter_period = max(2, int(params.get("filter_period", 21)))
supertrend_factor = max(0.05, float(params.get("supertrend_factor", 1.0)))
atr_period = max(2, int(params.get("atr_period", 7)))

df = df.copy()
close = df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
cl = close.to_numpy()
estimated = np.full(len(df), np.nan)
variance = 1.0
coefficient = alpha_filter * filter_period
for i in range(len(df)):
    if not np.isfinite(cl[i]):
        continue
    if i == 0 or not np.isfinite(estimated[i - 1]):
        estimated[i] = cl[i]
        continue
    gain = variance / (variance + coefficient)
    estimated[i] = estimated[i - 1] + gain * (cl[i] - estimated[i - 1])
    variance = (1.0 - gain) * variance + beta_filter / filter_period
filtered = pd.Series(estimated, index=df.index)
previous_close = close.shift(1)
true_range = pd.concat([
    high - low,
    (high - previous_close).abs(),
    (low - previous_close).abs(),
], axis=1).max(axis=1)
atr = true_range.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()
upper_basic = filtered + supertrend_factor * atr
lower_basic = filtered - supertrend_factor * atr
upper = upper_basic.to_numpy(copy=True)
lower = lower_basic.to_numpy(copy=True)
trend_line = np.full(len(df), np.nan)
direction = np.zeros(len(df), dtype=int)
for i in range(len(df)):
    if not np.isfinite(upper[i]) or not np.isfinite(lower[i]):
        continue
    if i == 0 or direction[i - 1] == 0:
        direction[i] = 1 if cl[i] >= filtered.iloc[i] else -1
    else:
        if direction[i - 1] > 0:
            upper[i] = min(upper[i], upper[i - 1])
            direction[i] = -1 if cl[i] < upper[i - 1] else 1
        else:
            lower[i] = max(lower[i], lower[i - 1])
            direction[i] = 1 if cl[i] > lower[i - 1] else -1
    trend_line[i] = lower[i] if direction[i] > 0 else upper[i]
previous_direction = np.concatenate([[0], direction[:-1]])
buy = (direction == 1) & (previous_direction == -1)
sell = (direction == -1) & (previous_direction == 1)

def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

low_values = low.to_numpy()
high_values = high.to_numpy()
buy_marks = [float(low_values[i]) * 0.995 if buy[i] else None for i in range(len(df))]
sell_marks = [float(high_values[i]) * 1.005 if sell[i] else None for i in range(len(df))]
output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Adaptive Filter", "data": plot_list(estimated), "color": "#2962FF", "overlay": True},
        {"name": "Adaptive SuperTrend", "data": plot_list(trend_line), "color": "#FFB300", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "ATF+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "ATF-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
