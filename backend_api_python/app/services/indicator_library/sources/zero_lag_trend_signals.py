# ============================================================
# [Default] Zero Lag Trend Signals
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Zero-lag EMA baseline with ATR-extreme volatility bands. It preserves the
# original indicator's trend-flip and pullback signals while keeping all
# calculations causal and chart-only.
# ============================================================

my_indicator_name = "[Default] Zero Lag Trend Signals"
my_indicator_description = (
    "Zero-lag EMA trend baseline with ATR volatility bands and chart-only "
    "trend-flip and pullback signals."
)

# @param length int 70 Zero-lag EMA and ATR lookback range=2:300:1
# @param mult float 1.2 Volatility band multiplier range=0.1:10.0:0.1

length = max(2, int(params.get("length", 70)))
mult = max(0.05, float(params.get("mult", 1.2)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
cl = close.to_numpy()

lag = max(1, int((length - 1) // 2))
source = close + (close - close.shift(lag))
zlema = source.ewm(span=length, adjust=False, min_periods=length).mean().to_numpy()

previous_close = close.shift(1)
true_range = pd.concat([
    high - low,
    (high - previous_close).abs(),
    (low - previous_close).abs(),
], axis=1).max(axis=1)
atr = true_range.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
volatility = (atr.rolling(length * 3, min_periods=length * 3).max() * mult).to_numpy()
upper = zlema + volatility
lower = zlema - volatility

n = len(df)
trend = np.zeros(n, dtype=np.int8)
for i in range(n):
    if not np.isfinite(zlema[i]) or not np.isfinite(upper[i]) or not np.isfinite(lower[i]) or not np.isfinite(cl[i]):
        continue

    if i == 0 or trend[i - 1] == 0:
        trend[i] = 1 if cl[i] >= zlema[i] else -1
        continue

    previous_zlema = zlema[i - 1]
    previous_upper = upper[i - 1]
    previous_lower = lower[i - 1]
    previous_value = cl[i - 1]
    if np.isfinite(previous_upper) and previous_value <= previous_upper and cl[i] > previous_upper:
        trend[i] = 1
    elif np.isfinite(previous_lower) and previous_value >= previous_lower and cl[i] < previous_lower:
        trend[i] = -1
    else:
        trend[i] = trend[i - 1]

previous_trend = np.concatenate([[0], trend[:-1]])
trend_bull = (trend == 1) & (previous_trend == -1)
trend_bear = (trend == -1) & (previous_trend == 1)

# Pullback entries require the trend to be established on both bars and a
# close crossing of the zero-lag baseline on the current bar.
long_entry = np.zeros(n, dtype=bool)
short_entry = np.zeros(n, dtype=bool)
for i in range(1, n):
    if trend[i] == 1 and trend[i - 1] == 1 and np.isfinite(zlema[i]) and np.isfinite(zlema[i - 1]):
        long_entry[i] = np.isfinite(cl[i - 1]) and cl[i - 1] <= zlema[i - 1] and cl[i] > zlema[i]
    elif trend[i] == -1 and trend[i - 1] == -1 and np.isfinite(zlema[i]) and np.isfinite(zlema[i - 1]):
        short_entry[i] = np.isfinite(cl[i - 1]) and cl[i - 1] >= zlema[i - 1] and cl[i] < zlema[i]


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

# Keep the two trend-colored baseline plots separated for the existing chart
# renderer. The active band is shown only in its corresponding trend state.
zlema_bull = [float(zlema[i]) if trend[i] == 1 and np.isfinite(zlema[i]) else None for i in range(n)]
zlema_bear = [float(zlema[i]) if trend[i] == -1 and np.isfinite(zlema[i]) else None for i in range(n)]
upper_plot = [float(upper[i]) if trend[i] == -1 and np.isfinite(upper[i]) else None for i in range(n)]
lower_plot = [float(lower[i]) if trend[i] == 1 and np.isfinite(lower[i]) else None for i in range(n)]

low_values = low.to_numpy()
high_values = high.to_numpy()
long_marks = [float(low_values[i]) * 0.995 if long_entry[i] and np.isfinite(low_values[i]) else None for i in range(n)]
short_marks = [float(high_values[i]) * 1.005 if short_entry[i] and np.isfinite(high_values[i]) else None for i in range(n)]
bear_marks = [float(high_values[i]) * 1.015 if trend_bear[i] and np.isfinite(high_values[i]) else None for i in range(n)]
bull_marks = [float(low_values[i]) * 0.985 if trend_bull[i] and np.isfinite(low_values[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Zero Lag Bull", "data": zlema_bull, "color": "#00FFBB", "overlay": True},
        {"name": "Zero Lag Bear", "data": zlema_bear, "color": "#FF1100", "overlay": True},
        {"name": "Upper Band", "data": upper_plot, "color": "#FF5252", "overlay": True},
        {"name": "Lower Band", "data": lower_plot, "color": "#00E676", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "Long", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "Short", "data": short_marks, "color": "#FF5252"},
        {"type": "sell", "text": "Bear", "data": bear_marks, "color": "#FF1744"},
        {"type": "buy", "text": "Bull", "data": bull_marks, "color": "#00C853"},
    ],
    "metadata": {
        "trend": [int(value) if value else None for value in trend],
        "causal": True,
        "source": "Zero Lag EMA + ATR extreme volatility bands",
    },
    "layers": [],
}
