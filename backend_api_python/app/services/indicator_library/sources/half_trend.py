# ============================================================
# [Default] HalfTrend
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal swing-channel trend line. A direction change can only use extrema
# confirmed by the prior bars, avoiding centered-window lookahead.
# ============================================================

my_indicator_name = "[Default] HalfTrend"
my_indicator_description = "Swing-channel trend line with ATR bands and chart-only reversal markers."

# @param amplitude int 2 Swing lookback range=1:30:1
# @param atr_period int 100 ATR period range=2:200:1
# @param channel_deviation float 2.0 ATR band multiplier range=0.25:6.0:0.25

amplitude = max(1, int(params.get("amplitude", 2)))
atr_period = max(2, int(params.get("atr_period", 100)))
channel_deviation = max(0.05, float(params.get("channel_deviation", 2.0)))

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
prior_high = high.rolling(amplitude, min_periods=amplitude).max().shift(1).to_numpy()
prior_low = low.rolling(amplitude, min_periods=amplitude).min().shift(1).to_numpy()
cl = close.to_numpy()
lo = low.to_numpy()
hi = high.to_numpy()
trend = np.zeros(len(df), dtype=int)
line = np.full(len(df), np.nan)
upper = np.full(len(df), np.nan)
lower = np.full(len(df), np.nan)
for i in range(len(df)):
    if i == 0:
        trend[i] = 1
    else:
        trend[i] = trend[i - 1]
        if np.isfinite(prior_high[i]) and cl[i] > prior_high[i]:
            trend[i] = 1
        elif np.isfinite(prior_low[i]) and cl[i] < prior_low[i]:
            trend[i] = -1
    if not np.isfinite(atr[i]):
        continue
    half_width = float(atr[i]) * channel_deviation
    center = prior_low[i] if trend[i] >= 0 else prior_high[i]
    if not np.isfinite(center):
        center = cl[i]
    raw_line = float(center)
    if i > 0 and np.isfinite(line[i - 1]):
        if trend[i] == trend[i - 1] == 1:
            raw_line = max(raw_line, line[i - 1])
        elif trend[i] == trend[i - 1] == -1:
            raw_line = min(raw_line, line[i - 1])
    line[i] = raw_line
    upper[i] = raw_line + half_width
    lower[i] = raw_line - half_width

previous_trend = np.concatenate([[0], trend[:-1]])
buy = (trend == 1) & (previous_trend == -1)
sell = (trend == -1) & (previous_trend == 1)

def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

buy_marks = [float(lo[i]) * 0.995 if buy[i] else None for i in range(len(df))]
sell_marks = [float(hi[i]) * 1.005 if sell[i] else None for i in range(len(df))]
output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "HalfTrend", "data": plot_list(line), "color": "#2962FF", "overlay": True},
        {"name": "HalfTrend Upper", "data": plot_list(upper), "color": "#26A69A", "overlay": True},
        {"name": "HalfTrend Lower", "data": plot_list(lower), "color": "#EF5350", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "HT+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "HT-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
