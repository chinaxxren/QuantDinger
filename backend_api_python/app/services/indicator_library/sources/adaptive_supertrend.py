# ============================================================
# [Default] Adaptive SuperTrend
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# A TQI-adaptive ATR SuperTrend. Trend quality widens the channel during
# choppy movement and tightens it during directional movement. All series are
# causal and this indicator only produces chart data and visual markers.
# ============================================================

my_indicator_name = "[Default] Adaptive SuperTrend"
my_indicator_description = (
    "TQI-adaptive ATR SuperTrend with causal trend bands and chart-only reversal markers."
)

# @param atr_period int 10 ATR Wilder smoothing period range=2:100:1
# @param factor float 3.0 Base ATR band multiplier range=0.25:10.0:0.25
# @param tqi_period int 14 Trend Quality Index lookback range=2:100:1
# @param smooth_period int 3 TQI smoothing period range=1:50:1

atr_period = max(2, int(params.get("atr_period", 10)))
base_factor = max(0.05, float(params.get("factor", 3.0)))
tqi_period = max(2, int(params.get("tqi_period", 14)))
smooth_period = max(1, int(params.get("smooth_period", 3)))

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
atr = true_range.ewm(
    alpha=1.0 / atr_period,
    adjust=False,
    min_periods=atr_period,
).mean().to_numpy()

# TQI compares net displacement with the absolute path travelled. It is
# intentionally based only on bars that have already closed.
net_change = close.diff(tqi_period).abs()
path_change = close.diff().abs().rolling(tqi_period, min_periods=tqi_period).sum()
tqi_raw = (net_change / path_change.replace(0.0, np.nan)).clip(lower=0.0, upper=1.0)
tqi = tqi_raw.ewm(
    span=smooth_period,
    adjust=False,
    min_periods=smooth_period,
).mean().clip(lower=0.0, upper=1.0)

# A low-quality, choppy path receives a wider band; a high-quality trend uses
# the base factor. Missing TQI values use the conservative widest multiplier.
tqi_values = tqi.to_numpy()
adaptive_factor = np.full(len(df), base_factor * 1.5, dtype=float)
finite_tqi = np.isfinite(tqi_values)
adaptive_factor[finite_tqi] = base_factor * (1.0 + 0.5 * (1.0 - tqi_values[finite_tqi]))

hl2 = (high + low) / 2.0
a = hl2.to_numpy()
upper_basic = a + adaptive_factor * atr
lower_basic = a - adaptive_factor * atr
cl = close.to_numpy()

n = len(df)
final_upper = np.full(n, np.nan)
final_lower = np.full(n, np.nan)
trend = np.zeros(n, dtype=np.int8)
trend_line = np.full(n, np.nan)

for i in range(n):
    if not np.isfinite(upper_basic[i]) or not np.isfinite(lower_basic[i]) or not np.isfinite(cl[i]):
        continue

    if i == 0 or trend[i - 1] == 0 or not np.isfinite(final_upper[i - 1]) or not np.isfinite(final_lower[i - 1]):
        final_upper[i] = upper_basic[i]
        final_lower[i] = lower_basic[i]
        trend[i] = 1 if cl[i] >= a[i] else -1
    else:
        previous_upper = final_upper[i - 1]
        previous_lower = final_lower[i - 1]
        previous_close_value = cl[i - 1]
        final_upper[i] = (
            upper_basic[i]
            if upper_basic[i] < previous_upper or previous_close_value > previous_upper
            else previous_upper
        )
        final_lower[i] = (
            lower_basic[i]
            if lower_basic[i] > previous_lower or previous_close_value < previous_lower
            else previous_lower
        )
        if cl[i] > previous_upper:
            trend[i] = 1
        elif cl[i] < previous_lower:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]

    trend_line[i] = final_lower[i] if trend[i] > 0 else final_upper[i]

previous_trend = np.concatenate([[0], trend[:-1]])
buy = (trend == 1) & (previous_trend == -1)
sell = (trend == -1) & (previous_trend == 1)


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

low_values = low.to_numpy()
high_values = high.to_numpy()
buy_marks = [
    float(low_values[i]) * 0.995 if buy[i] and np.isfinite(low_values[i]) else None
    for i in range(n)
]
sell_marks = [
    float(high_values[i]) * 1.005 if sell[i] and np.isfinite(high_values[i]) else None
    for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Adaptive SuperTrend Up", "data": [float(trend_line[i]) if trend[i] > 0 and np.isfinite(trend_line[i]) else None for i in range(n)], "color": "#00E676", "overlay": True},
        {"name": "Adaptive SuperTrend Down", "data": [float(trend_line[i]) if trend[i] < 0 and np.isfinite(trend_line[i]) else None for i in range(n)], "color": "#FF5252", "overlay": True},
        {"name": "TQI", "data": plot_list(tqi_values), "color": "#42A5F5", "overlay": False},
    ],
    "signals": [
        {"type": "buy", "text": "AST+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "AST-", "data": sell_marks, "color": "#FF5252"},
    ],
    "metadata": {
        "tqi": plot_list(tqi_values),
        "adaptive_factor": plot_list(adaptive_factor),
        "causal": True,
    },
    "layers": [],
}
