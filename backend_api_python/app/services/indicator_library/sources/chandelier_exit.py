# ============================================================
# [Default] Chandelier Exit
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# ATR-based trailing levels from rolling extremes. The displayed stop follows
# the active direction and only emits chart markers on confirmed flips.
# ============================================================

my_indicator_name = "[Default] Chandelier Exit"
my_indicator_description = "ATR trailing stop levels based on rolling highs and lows."

# @param length int 22 Extreme and ATR lookback period range=5:100:1
# @param atr_multiplier float 3.0 ATR stop multiplier range=1.0:6.0:0.25

length = max(2, int(params.get("length", 22)))
atr_multiplier = max(0.1, float(params.get("atr_multiplier", 3.0)))

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
atr = true_range.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
long_candidate = high.rolling(length, min_periods=length).max() - atr_multiplier * atr
short_candidate = low.rolling(length, min_periods=length).min() + atr_multiplier * atr
n = len(df)
cl = close.to_numpy()
long_values = long_candidate.to_numpy()
short_values = short_candidate.to_numpy()
trend = np.zeros(n, dtype=int)
stop = np.full(n, np.nan)
for i in range(n):
    if pd.isna(long_values[i]) or pd.isna(short_values[i]):
        continue
    prior_trend = trend[i - 1] if i > 0 else 0
    prior_stop = stop[i - 1] if i > 0 else np.nan
    if prior_trend == 0:
        trend[i] = 1 if cl[i] >= (long_values[i] + short_values[i]) / 2.0 else -1
        stop[i] = long_values[i] if trend[i] > 0 else short_values[i]
    elif prior_trend > 0:
        if cl[i] < prior_stop:
            trend[i] = -1
            stop[i] = short_values[i]
        else:
            trend[i] = 1
            stop[i] = max(prior_stop, long_values[i])
    else:
        if cl[i] > prior_stop:
            trend[i] = 1
            stop[i] = long_values[i]
        else:
            trend[i] = -1
            stop[i] = min(prior_stop, short_values[i])
long_flip = (trend == 1) & np.concatenate([[False], trend[:-1] != 1])
short_flip = (trend == -1) & np.concatenate([[False], trend[:-1] != -1])
long_marks = [float(low.iloc[i]) * 0.995 if bool(long_flip[i]) else None for i in range(n)]
short_marks = [float(high.iloc[i]) * 1.005 if bool(short_flip[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Chandelier Stop", "data": [None if pd.isna(v) else float(v) for v in stop], "color": "#FFB300", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "CE+", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "CE-", "data": short_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
