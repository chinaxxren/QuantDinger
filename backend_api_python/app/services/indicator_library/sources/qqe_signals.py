# ============================================================
# [Default] QQE Signals
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# RSI-based adaptive trailing levels. All smoothing and state transitions use
# current and prior bars; markers are visual only.
# ============================================================

my_indicator_name = "[Default] QQE Signals"
my_indicator_description = "Smoothed RSI with volatility-adaptive QQE trailing levels and chart-only signals."

# @param rsi_period int 14 RSI period range=2:100:1
# @param rsi_smoothing int 5 RSI smoothing period range=1:50:1
# @param qqe_factor float 4.236 Trailing-level multiplier range=0.5:10.0:0.1

rsi_period = max(2, int(params.get("rsi_period", 14)))
rsi_smoothing = max(1, int(params.get("rsi_smoothing", 5)))
qqe_factor = max(0.1, float(params.get("qqe_factor", 4.236)))

df = df.copy()
close = df["close"].astype(float)
delta = close.diff()
gain = delta.clip(lower=0.0)
loss = -delta.clip(upper=0.0)
average_gain = gain.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()
average_loss = loss.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()
rsi = 100.0 - 100.0 / (1.0 + average_gain / average_loss.replace(0.0, np.nan))
rsi = rsi.where(average_loss != 0.0, 100.0)
rsi = rsi.where(average_gain != 0.0, 0.0)
rsi = rsi.fillna(50.0)
smoothed_rsi = rsi.ewm(span=rsi_smoothing, adjust=False, min_periods=rsi_smoothing).mean().to_numpy()
rsi_delta = pd.Series(smoothed_rsi).diff().abs()
range_first = rsi_delta.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()
range_second = range_first.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()
trailing_range = (range_second * qqe_factor).to_numpy()
long_band = np.full(len(df), np.nan)
short_band = np.full(len(df), np.nan)
trend = np.zeros(len(df), dtype=int)
for i in range(len(df)):
    value = smoothed_rsi[i]
    distance = trailing_range[i]
    if not np.isfinite(value) or not np.isfinite(distance):
        continue
    candidate_long = value - distance
    candidate_short = value + distance
    if i == 0 or not np.isfinite(long_band[i - 1]):
        long_band[i] = candidate_long
        short_band[i] = candidate_short
        trend[i] = 1
        continue
    previous_long = long_band[i - 1]
    previous_short = short_band[i - 1]
    previous_value = smoothed_rsi[i - 1]
    long_band[i] = max(previous_long, candidate_long) if previous_value > previous_long and value > previous_long else candidate_long
    short_band[i] = min(previous_short, candidate_short) if previous_value < previous_short and value < previous_short else candidate_short
    if value > previous_short:
        trend[i] = 1
    elif value < previous_long:
        trend[i] = -1
    else:
        trend[i] = trend[i - 1]
active_band = np.where(trend == 1, long_band, short_band)
previous_trend = np.concatenate([[0], trend[:-1]])
buy = (trend == 1) & (previous_trend == -1)
sell = (trend == -1) & (previous_trend == 1)

def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

low = df["low"].astype(float).to_numpy()
high = df["high"].astype(float).to_numpy()
buy_marks = [float(low[i]) * 0.995 if buy[i] else None for i in range(len(df))]
sell_marks = [float(high[i]) * 1.005 if sell[i] else None for i in range(len(df))]
output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "QQE RSI", "data": plot_list(smoothed_rsi), "color": "#2962FF", "overlay": False},
        {"name": "QQE Trail", "data": plot_list(active_band), "color": "#FF6D00", "overlay": False},
    ],
    "signals": [
        {"type": "buy", "text": "QQE+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "QQE-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
