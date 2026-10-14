# ============================================================
# [Default] Gaussian Filter Trend
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# A cascade of causal EMAs approximates Gaussian smoothing. ATR bands provide
# an adaptive trend state without centered windows or future-bar dependence.
# ============================================================

my_indicator_name = "[Default] Gaussian Filter Trend"
my_indicator_description = "Cascaded Gaussian-style smoother with ATR trend bands and visual reversal markers."

# @param period int 20 Base smoothing period range=2:200:1
# @param poles int 3 Number of smoothing stages range=1:6:1
# @param atr_period int 14 ATR period range=2:100:1
# @param multiplier float 1.5 ATR band multiplier range=0.25:8.0:0.25

period = max(2, int(params.get("period", 20)))
poles = min(6, max(1, int(params.get("poles", 3))))
atr_period = max(2, int(params.get("atr_period", 14)))
multiplier = max(0.05, float(params.get("multiplier", 1.5)))

df = df.copy()
close = df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
smooth = close.copy()
for _ in range(poles):
    smooth = smooth.ewm(span=period, adjust=False, min_periods=period).mean()
previous_close = close.shift(1)
true_range = pd.concat([
    high - low,
    (high - previous_close).abs(),
    (low - previous_close).abs(),
], axis=1).max(axis=1)
atr = true_range.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()
center = smooth.to_numpy()
atr_values = atr.to_numpy()
cl = close.to_numpy()
trend_line = np.full(len(df), np.nan)
trend = np.zeros(len(df), dtype=int)
for i in range(len(df)):
    if not np.isfinite(center[i]) or not np.isfinite(atr_values[i]):
        continue
    upper = center[i] + multiplier * atr_values[i]
    lower = center[i] - multiplier * atr_values[i]
    if i == 0 or trend[i - 1] == 0:
        trend[i] = 1 if cl[i] >= center[i] else -1
    elif trend[i - 1] > 0:
        trend[i] = -1 if cl[i] < lower else 1
    else:
        trend[i] = 1 if cl[i] > upper else -1
    trend_line[i] = lower if trend[i] > 0 else upper
previous_trend = np.concatenate([[0], trend[:-1]])
buy = (trend == 1) & (previous_trend == -1)
sell = (trend == -1) & (previous_trend == 1)

def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

lo = low.to_numpy()
hi = high.to_numpy()
buy_marks = [float(lo[i]) * 0.995 if buy[i] else None for i in range(len(df))]
sell_marks = [float(hi[i]) * 1.005 if sell[i] else None for i in range(len(df))]
output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Gaussian Filter", "data": plot_list(center), "color": "#2962FF", "overlay": True},
        {"name": "Gaussian Trend", "data": plot_list(trend_line), "color": "#FFB300", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "GF+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "GF-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
