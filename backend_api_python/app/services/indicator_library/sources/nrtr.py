# ============================================================
# [Default] NRTR
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Nick Rypock Trailing Reverse percentage stop with optional volatility
# adjustment. Trend flips are chart annotations only, never orders.
# ============================================================

my_indicator_name = "[Default] NRTR"
my_indicator_description = "Percentage-based trailing stop with optional volatility adjustment."

# @param percentage float 1.0 Fixed stop percentage range=0.25:5.0:0.25
# @param mult float 0.0 Volatility adjustment multiplier range=0.0:3.0:0.1
# @param length int 20 Volatility lookback period range=5:100:1

percentage = max(0.01, float(params.get("percentage", 1.0)))
mult = max(0.0, float(params.get("mult", 0.0)))
length = max(2, int(params.get("length", 20)))

df = df.copy()
close = df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
n = len(df)
cl = close.to_numpy()
mean = close.rolling(length, min_periods=length).mean().to_numpy()
std = close.rolling(length, min_periods=length).std(ddof=0).to_numpy()
long_stop = np.full(n, np.nan)
short_stop = np.full(n, np.nan)
trend = np.zeros(n, dtype=int)
peak = trough = active_stop = np.nan
for i in range(n):
    if i < length or not np.isfinite(cl[i]):
        continue
    k = percentage / 100.0
    if mult > 0.0 and np.isfinite(mean[i]) and mean[i] != 0.0 and np.isfinite(std[i]):
        k = max(0.0001, std[i] * mult / abs(mean[i]))
    if trend[i - 1] >= 0 if i > 0 else True:
        peak = cl[i] if not np.isfinite(peak) else max(peak, cl[i])
        active_stop = peak * (1.0 - k)
        if cl[i] <= active_stop:
            trend[i] = -1
            trough = cl[i]
            active_stop = trough * (1.0 + k)
            short_stop[i] = active_stop
        else:
            trend[i] = 1
            long_stop[i] = max(active_stop, long_stop[i - 1]) if i > 0 and np.isfinite(long_stop[i - 1]) else active_stop
    else:
        trough = cl[i] if not np.isfinite(trough) else min(trough, cl[i])
        active_stop = trough * (1.0 + k)
        if cl[i] >= active_stop:
            trend[i] = 1
            peak = cl[i]
            active_stop = peak * (1.0 - k)
            long_stop[i] = active_stop
        else:
            trend[i] = -1
            short_stop[i] = min(active_stop, short_stop[i - 1]) if i > 0 and np.isfinite(short_stop[i - 1]) else active_stop
    if i + 1 < n and trend[i + 1] == 0:
        trend[i + 1] = trend[i]

previous_trend = np.concatenate([[0], trend[:-1]])
buy_flip = (trend == 1) & (previous_trend == -1)
sell_flip = (trend == -1) & (previous_trend == 1)
buy_marks = [float(low.iloc[i]) * 0.995 if bool(buy_flip[i]) else None for i in range(n)]
sell_marks = [float(high.iloc[i]) * 1.005 if bool(sell_flip[i]) else None for i in range(n)]

def plot_list(values):
    return [None if not np.isfinite(v) else float(v) for v in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "NRTR Long Stop", "data": plot_list(long_stop), "color": "#00E676", "overlay": True},
        {"name": "NRTR Short Stop", "data": plot_list(short_stop), "color": "#FF5252", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "NRTR+", "data": buy_marks, "color": "#00E676"},
        {"type": "sell", "text": "NRTR-", "data": sell_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
