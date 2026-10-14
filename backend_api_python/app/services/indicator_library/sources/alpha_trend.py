# ============================================================
# [Default] AlphaTrend
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# ATR bands are ratcheted according to RSI momentum. The recursive state only
# uses current and prior bars; cross markers are visual, not order actions.
# ============================================================

my_indicator_name = "[Default] AlphaTrend"
my_indicator_description = "RSI-confirmed ATR trend line with chart-only crossover markers."

# @param atr_period int 14 ATR period range=2:100:1
# @param momentum_period int 14 RSI period range=2:100:1
# @param multiplier float 1.0 ATR channel multiplier range=0.25:8.0:0.25
# @param confirmation_lag int 2 Signal comparison lag range=1:10:1

atr_period = max(2, int(params.get("atr_period", 14)))
momentum_period = max(2, int(params.get("momentum_period", 14)))
multiplier = max(0.05, float(params.get("multiplier", 1.0)))
confirmation_lag = max(1, int(params.get("confirmation_lag", 2)))

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
delta = close.diff()
gain = delta.clip(lower=0.0)
loss = -delta.clip(upper=0.0)
average_gain = gain.ewm(alpha=1.0 / momentum_period, adjust=False, min_periods=momentum_period).mean()
average_loss = loss.ewm(alpha=1.0 / momentum_period, adjust=False, min_periods=momentum_period).mean()
relative_strength = average_gain / average_loss.replace(0.0, np.nan)
rsi = (100.0 - 100.0 / (1.0 + relative_strength)).fillna(50.0).to_numpy()
cl = close.to_numpy()
lo = low.to_numpy()
hi = high.to_numpy()
trend_line = np.full(len(df), np.nan)
trend = np.zeros(len(df), dtype=int)
for i in range(len(df)):
    if not np.isfinite(atr[i]):
        continue
    lower_band = cl[i] - multiplier * float(atr[i])
    upper_band = cl[i] + multiplier * float(atr[i])
    bullish = rsi[i] >= 50.0
    if i == 0 or not np.isfinite(trend_line[i - 1]):
        trend_line[i] = lower_band if bullish else upper_band
    elif bullish:
        trend_line[i] = max(lower_band, trend_line[i - 1])
    else:
        trend_line[i] = min(upper_band, trend_line[i - 1])
    trend[i] = 1 if bullish else -1

lagged = np.concatenate([np.full(min(confirmation_lag, len(df)), np.nan), trend_line[:-confirmation_lag]]) if len(df) > confirmation_lag else np.full(len(df), np.nan)
previous_gap = np.concatenate([[np.nan], (trend_line - lagged)[:-1]]) if len(df) else np.array([])
current_gap = trend_line - lagged
buy = (current_gap > 0.0) & (previous_gap <= 0.0) & np.isfinite(current_gap) & np.isfinite(previous_gap)
sell = (current_gap < 0.0) & (previous_gap >= 0.0) & np.isfinite(current_gap) & np.isfinite(previous_gap)
line_values = [None if not np.isfinite(value) else float(value) for value in trend_line]
buy_marks = [float(lo[i]) * 0.995 if buy[i] else None for i in range(len(df))]
sell_marks = [float(hi[i]) * 1.005 if sell[i] else None for i in range(len(df))]
output = {
    "name": my_indicator_name,
    "plots": [{"name": "AlphaTrend", "data": line_values, "color": "#26A69A", "overlay": True}],
    "signals": [
        {"type": "buy", "text": "AT+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "AT-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
