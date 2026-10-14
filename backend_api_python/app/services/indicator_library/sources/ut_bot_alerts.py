# ============================================================
# [Default] UT Bot Alerts
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# ATR-based causal trailing stop. Crosses are chart annotations only and do
# not place, modify, or close trades.
# ============================================================

my_indicator_name = "[Default] UT Bot Alerts"
my_indicator_description = "ATR trailing stop with chart-only price-cross markers."

# @param atr_period int 10 ATR period range=2:100:1
# @param key_value float 1.0 ATR sensitivity multiplier range=0.25:10.0:0.25

atr_period = max(2, int(params.get("atr_period", 10)))
key_value = max(0.05, float(params.get("key_value", 1.0)))

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
cl = close.to_numpy()
lo = low.to_numpy()
hi = high.to_numpy()
stop = np.full(len(df), np.nan)
trend = np.zeros(len(df), dtype=int)
for i in range(len(df)):
    if not np.isfinite(atr[i]):
        continue
    loss = float(atr[i]) * key_value
    if i == 0 or not np.isfinite(stop[i - 1]):
        stop[i] = cl[i] - loss
        trend[i] = 1
        continue
    previous_stop = stop[i - 1]
    previous_price = cl[i - 1]
    if previous_price > previous_stop and cl[i] > previous_stop:
        stop[i] = max(previous_stop, cl[i] - loss)
    elif previous_price < previous_stop and cl[i] < previous_stop:
        stop[i] = min(previous_stop, cl[i] + loss)
    elif cl[i] > previous_stop:
        stop[i] = cl[i] - loss
    else:
        stop[i] = cl[i] + loss
    trend[i] = 1 if cl[i] > stop[i] else -1

previous_trend = np.concatenate([[0], trend[:-1]])
buy = (trend == 1) & (previous_trend == -1)
sell = (trend == -1) & (previous_trend == 1)
stop_values = [None if not np.isfinite(value) else float(value) for value in stop]
buy_marks = [float(lo[i]) * 0.995 if buy[i] else None for i in range(len(df))]
sell_marks = [float(hi[i]) * 1.005 if sell[i] else None for i in range(len(df))]
output = {
    "name": my_indicator_name,
    "plots": [{"name": "UT Bot Stop", "data": stop_values, "color": "#FFB300", "overlay": True}],
    "signals": [
        {"type": "buy", "text": "UT Buy", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "UT Sell", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
