# ============================================================
# [Default] Keltner Channel
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# EMA centerline with Wilder ATR envelopes. Every input uses current or prior
# bars only, so historical channel values remain stable as new bars arrive.
# ============================================================

my_indicator_name = "[Default] Keltner Channel"
my_indicator_description = "EMA centerline with ATR-based volatility envelopes."

# @param period int 20 EMA centerline period range=2:200:1
# @param atr_period int 10 ATR period range=2:100:1
# @param multiplier float 2.0 ATR band multiplier range=0.25:8.0:0.25

period = max(2, int(params.get("period", 20)))
atr_period = max(2, int(params.get("atr_period", 10)))
multiplier = max(0.05, float(params.get("multiplier", 2.0)))

df = df.copy()
close = df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
center = close.ewm(span=period, adjust=False, min_periods=period).mean()
previous_close = close.shift(1)
true_range = pd.concat([
    high - low,
    (high - previous_close).abs(),
    (low - previous_close).abs(),
], axis=1).max(axis=1)
atr = true_range.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()
upper = center + multiplier * atr
lower = center - multiplier * atr

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Upper", "data": plot_list(upper), "color": "#26A69A", "overlay": True},
        {"name": "EMA", "data": plot_list(center), "color": "#2962FF", "overlay": True},
        {"name": "Lower", "data": plot_list(lower), "color": "#EF5350", "overlay": True},
    ],
    "signals": [],
    "layers": [],
}
