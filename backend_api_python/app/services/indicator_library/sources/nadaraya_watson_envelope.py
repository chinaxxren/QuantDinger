# ============================================================
# [Default] Nadaraya-Watson Envelope
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal Gaussian-kernel smoother with ATR envelope bands. No future bars are
# used, so the line is stable once a candle closes. Signals are visual only.
# ============================================================

my_indicator_name = "[Default] Nadaraya-Watson Envelope"
my_indicator_description = "Causal Gaussian-kernel smoother with ATR envelope bands for mean reversion zones."

# @param lookback int 64 Kernel lookback window range=20:160:4
# @param bandwidth float 8.0 Gaussian bandwidth range=2.0:30.0:0.5
# @param atr_period int 21 ATR period range=5:80:1
# @param envelope_multiplier float 2.0 ATR envelope multiplier range=0.5:5.0:0.25

lookback = int(params.get("lookback", 64))
bandwidth = float(params.get("bandwidth", 8.0))
atr_period = int(params.get("atr_period", 21))
envelope_multiplier = float(params.get("envelope_multiplier", 2.0))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
n = len(df)
cl = close.to_numpy()

smooth = np.full(n, np.nan)
for i in range(n):
    start = max(0, i - lookback + 1)
    window = cl[start:i + 1]
    distance = np.arange(len(window) - 1, -1, -1, dtype=float)
    weights = np.exp(-(distance * distance) / (2.0 * bandwidth * bandwidth))
    weight_sum = weights.sum()
    smooth[i] = float((window * weights).sum() / weight_sum) if weight_sum > 0 else cl[i]

prev_close = close.shift(1)
tr = pd.concat([
    high - low,
    (high - prev_close).abs(),
    (low - prev_close).abs(),
], axis=1).max(axis=1)
atr = tr.ewm(alpha=1.0 / atr_period, adjust=False, min_periods=atr_period).mean()
upper = smooth + envelope_multiplier * atr.to_numpy()
lower = smooth - envelope_multiplier * atr.to_numpy()

below_lower = close.to_numpy() < lower
above_upper = close.to_numpy() > upper
reclaim_lower = (close.to_numpy() > lower) & np.concatenate([[False], below_lower[:-1]])
reject_upper = (close.to_numpy() < upper) & np.concatenate([[False], above_upper[:-1]])

def plot_list(values):
    return [None if pd.isna(v) else float(v) for v in values]

long_marks = [float(low.iloc[i]) * 0.995 if bool(reclaim_lower[i]) else None for i in range(n)]
short_marks = [float(high.iloc[i]) * 1.005 if bool(reject_upper[i]) else None for i in range(n)]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "NW Smooth", "data": plot_list(smooth), "color": "#FFB300", "overlay": True},
        {"name": "NW Upper", "data": plot_list(upper), "color": "#AB47BC", "overlay": True},
        {"name": "NW Lower", "data": plot_list(lower), "color": "#AB47BC", "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "NW↥", "data": long_marks, "color": "#00E676"},
        {"type": "sell", "text": "NW↧", "data": short_marks, "color": "#FF5252"},
    ],
    "layers": [],
}
