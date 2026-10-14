# ============================================================
# [Default] Variable Moving Average
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# VIDYA-style adaptive average. The Chande momentum ratio adjusts the EMA
# smoothing coefficient on each bar; all values are causal.
# ============================================================

my_indicator_name = "[Default] Variable Moving Average"
my_indicator_description = "VIDYA-style adaptive moving average driven by normalized price momentum."

# @param period int 20 Base smoothing period range=2:200:1
# @param momentum_period int 9 Momentum normalization period range=2:100:1
# @param signal_period int 9 Signal EMA period range=2:100:1

period = max(2, int(params.get("period", 20)))
momentum_period = max(2, int(params.get("momentum_period", 9)))
signal_period = max(2, int(params.get("signal_period", 9)))

df = df.copy()
close = df["close"].astype(float)
change = close.diff()
up = change.clip(lower=0.0).rolling(momentum_period, min_periods=momentum_period).sum()
down = (-change.clip(upper=0.0)).rolling(momentum_period, min_periods=momentum_period).sum()
absolute_momentum = ((up - down).abs() / (up + down).replace(0.0, np.nan)).fillna(0.0).to_numpy()
cl = close.to_numpy()
vidya = np.full(len(df), np.nan)
base_alpha = 2.0 / (period + 1.0)
for i in range(len(df)):
    if not np.isfinite(cl[i]):
        continue
    alpha = base_alpha * min(1.0, max(0.0, float(absolute_momentum[i])))
    if i == 0 or not np.isfinite(vidya[i - 1]):
        vidya[i] = cl[i]
    else:
        vidya[i] = alpha * cl[i] + (1.0 - alpha) * vidya[i - 1]
vidya_series = pd.Series(vidya, index=df.index)
signal = vidya_series.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean().to_numpy()

def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "VIDYA", "data": plot_list(vidya), "color": "#2962FF", "overlay": True},
        {"name": "VIDYA Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": True},
    ],
    "signals": [],
    "layers": [],
}
