# ============================================================
# [Default] Follow Line Indicator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Bollinger breakout direction with a one-sided ATR trailing line.
# This implementation emits chart lines and visual reversal markers only.
# ============================================================

my_indicator_name = "[Default] Follow Line Indicator"
my_indicator_description = (
    "Bollinger breakout and ATR trailing line with chart-only trend reversal signals."
)

# @param bb_period int 21 Bollinger period range=2:200:1
# @param bb_deviations float 1.0 Bollinger standard-deviation multiplier range=0.1:5.0:0.1
# @param use_atr_filter bool True Use ATR in the trailing line
# @param atr_period int 5 ATR period range=2:100:1
# @param hide_labels bool False Hide reversal signal markers

bb_period = max(2, int(params.get("bb_period", 21)))
bb_deviations = max(0.05, float(params.get("bb_deviations", 1.0)))
use_atr_filter = bool(params.get("use_atr_filter", True))
atr_period = max(2, int(params.get("atr_period", 5)))
hide_labels = bool(params.get("hide_labels", False))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)

basis = close.rolling(bb_period, min_periods=bb_period).mean()
stdev = close.rolling(bb_period, min_periods=bb_period).std(ddof=0)
bb_upper = (basis + bb_deviations * stdev).to_numpy()
bb_lower = (basis - bb_deviations * stdev).to_numpy()

previous_close = close.shift(1)
true_range = pd.concat([
    high - low,
    (high - previous_close).abs(),
    (low - previous_close).abs(),
], axis=1).max(axis=1)
atr = true_range.ewm(
    alpha=1.0 / atr_period,
    adjust=False,
    min_periods=atr_period,
).mean().to_numpy()

n = len(df)
trend = np.zeros(n, dtype=np.int8)
trend_line = np.full(n, np.nan, dtype=float)
low_values = low.to_numpy()
high_values = high.to_numpy()

# Trend direction changes only on a confirmed Bollinger breakout. The
# trailing line then moves in one direction until the next breakout.
for i in range(n):
    if not np.isfinite(close.iloc[i]) or not np.isfinite(bb_upper[i]) or not np.isfinite(bb_lower[i]):
        if i > 0:
            trend[i] = trend[i - 1]
            trend_line[i] = trend_line[i - 1]
        continue

    previous_trend = trend[i - 1] if i > 0 else 0
    if close.iloc[i] > bb_upper[i]:
        trend[i] = 1
    elif close.iloc[i] < bb_lower[i]:
        trend[i] = -1
    else:
        trend[i] = previous_trend

    previous_line = trend_line[i - 1] if i > 0 else np.nan
    if trend[i] == 1:
        candidate = low_values[i]
        if use_atr_filter and np.isfinite(atr[i]):
            candidate -= atr[i]
        trend_line[i] = candidate if not np.isfinite(previous_line) else max(candidate, previous_line)
    elif trend[i] == -1:
        candidate = high_values[i]
        if use_atr_filter and np.isfinite(atr[i]):
            candidate += atr[i]
        trend_line[i] = candidate if not np.isfinite(previous_line) else min(candidate, previous_line)
    else:
        trend_line[i] = previous_line

previous_trend = np.concatenate([[0], trend[:-1]])
buy = (trend == 1) & (previous_trend == -1)
sell = (trend == -1) & (previous_trend == 1)

# Bridge color segments on a reversal bar so the renderer draws a continuous
# line without introducing a new pane or changing the chart layout.
tl_up = np.where(trend == 1, trend_line, np.nan)
tl_down = np.where(trend == -1, trend_line, np.nan)
for i in range(1, n):
    if trend[i] == 1 and trend[i - 1] == -1:
        tl_up[i - 1] = trend_line[i - 1]
        tl_up[i] = trend_line[i]
    elif trend[i] == -1 and trend[i - 1] == 1:
        tl_down[i - 1] = trend_line[i - 1]
        tl_down[i] = trend_line[i]


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

long_marks = [
    float(low_values[i]) if buy[i] and np.isfinite(low_values[i]) and not hide_labels else None
    for i in range(n)
]
short_marks = [
    float(high_values[i]) if sell[i] and np.isfinite(high_values[i]) and not hide_labels else None
    for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Follow Line Up", "data": plot_list(tl_up), "color": "#0000FF", "overlay": True},
        {"name": "Follow Line Down", "data": plot_list(tl_down), "color": "#FF0000", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "Buy", "data": long_marks, "color": "#0000FF"},
        {"type": "sell", "text": "Sell", "data": short_marks, "color": "#FF0000"},
    ],
    "metadata": {
        "trend_line": plot_list(trend_line),
        "trend": [int(value) if value else None for value in trend],
        "causal": True,
    },
    "layers": [],
}
