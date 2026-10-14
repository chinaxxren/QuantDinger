# ============================================================
# [Default] ATR Rope
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal ATR-step trend filter. The rope only moves after price crosses an
# ATR-scaled threshold; markers show state transitions for charting only.
# ============================================================

my_indicator_name = "[Default] ATR Rope"
my_indicator_description = "ATR-step trend filter with a trailing rope and chart-only direction-change markers."

# @param atr_period int 14 ATR period range=2:100:1
# @param multiplier float 1.5 ATR threshold multiplier range=0.25:8.0:0.25

atr_period = max(2, int(params.get("atr_period", 14)))
multiplier = max(0.05, float(params.get("multiplier", 1.5)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
prev_close = close.shift(1)
tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
atr = tr.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean().to_numpy()
cl = close.to_numpy()
rope = np.full(len(df), np.nan)
direction = np.zeros(len(df), dtype=int)
for i in range(len(df)):
    if not np.isfinite(atr[i]):
        continue
    threshold = max(float(atr[i]) * multiplier, 0.0)
    if i == 0 or not np.isfinite(rope[i - 1]):
        rope[i] = cl[i]
        direction[i] = 0
        continue
    previous = rope[i - 1]
    if cl[i] > previous + threshold:
        rope[i] = cl[i] - threshold
        direction[i] = 1
    elif cl[i] < previous - threshold:
        rope[i] = cl[i] + threshold
        direction[i] = -1
    else:
        rope[i] = previous
        direction[i] = direction[i - 1]

long_marks = [float(low.iloc[i]) * 0.995 if direction[i] == 1 and direction[i - 1] != 1 else None for i in range(len(df))]
short_marks = [float(high.iloc[i]) * 1.005 if direction[i] == -1 and direction[i - 1] != -1 else None for i in range(len(df))]
rope_values = [None if not np.isfinite(v) else float(v) for v in rope]
output = {
    "name": my_indicator_name,
    "plots": [{"name": "ATR Rope", "data": rope_values, "color": "#26A69A", "overlay": True}],
    "signals": [
        {"type": "buy", "text": "Rope↥", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "Rope↧", "data": short_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
