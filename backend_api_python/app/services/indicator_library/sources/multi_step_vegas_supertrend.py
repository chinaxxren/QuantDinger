# ============================================================
# [Default] Multi-Step Vegas SuperTrend
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# A Vegas EMA channel adjusts the ATR multiplier before a causal supertrend.
# The original strategy's entries and exits are intentionally represented as
# chart markers only; this source never places or manages trades.
# ============================================================

my_indicator_name = "[Default] Multi-Step Vegas SuperTrend"
my_indicator_description = "Vegas volatility channel with an adaptive ATR supertrend and visual reversals."

# @param atr_period int 10 ATR period range=2:100:1
# @param vegas_period int 100 Vegas EMA and standard-deviation window range=5:300:1
# @param supertrend_multiplier float 5.0 Base ATR multiplier range=0.5:12.0:0.5
# @param volatility_adjustment float 5.0 Channel-width adjustment range=0.0:20.0:0.5

atr_period = max(2, int(params.get("atr_period", 10)))
vegas_period = max(5, int(params.get("vegas_period", 100)))
supertrend_multiplier = max(0.05, float(params.get("supertrend_multiplier", 5.0)))
volatility_adjustment = max(0.0, float(params.get("volatility_adjustment", 5.0)))

df = df.copy()
close = df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
vegas_average = close.ewm(span=vegas_period, adjust=False, min_periods=vegas_period).mean()
vegas_deviation = close.rolling(vegas_period, min_periods=vegas_period).std()
channel_width = 2.0 * vegas_deviation
adjusted_multiplier = supertrend_multiplier + volatility_adjustment * (channel_width / vegas_average.replace(0.0, np.nan))
previous_close = close.shift(1)
true_range = pd.concat([
    high - low,
    (high - previous_close).abs(),
    (low - previous_close).abs(),
], axis=1).max(axis=1)
atr = true_range.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()
price_center = (high + low + close) / 3.0
upper_basic = price_center - adjusted_multiplier * atr
lower_basic = price_center + adjusted_multiplier * atr
upper = upper_basic.to_numpy(copy=True)
lower = lower_basic.to_numpy(copy=True)
trend_line = np.full(len(df), np.nan)
direction = np.zeros(len(df), dtype=int)
for i in range(len(df)):
    if not np.isfinite(upper[i]) or not np.isfinite(lower[i]):
        continue
    if i == 0 or direction[i - 1] == 0:
        direction[i] = 1
    else:
        previous_upper = upper[i - 1]
        previous_lower = lower[i - 1]
        if direction[i - 1] > 0:
            upper[i] = max(upper[i], previous_upper)
            direction[i] = -1 if close.iloc[i] < previous_upper else 1
        else:
            lower[i] = min(lower[i], previous_lower)
            direction[i] = 1 if close.iloc[i] > previous_lower else -1
    trend_line[i] = upper[i] if direction[i] > 0 else lower[i]
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
        {"name": "Vegas EMA", "data": plot_list(vegas_average), "color": "#42A5F5", "overlay": True},
        {"name": "Vegas Upper", "data": plot_list(vegas_average + vegas_deviation), "color": "#90CAF9", "overlay": True},
        {"name": "Vegas Lower", "data": plot_list(vegas_average - vegas_deviation), "color": "#90CAF9", "overlay": True},
        {"name": "Vegas SuperTrend", "data": plot_list(trend_line), "color": "#FFB300", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "VS+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "VS-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
