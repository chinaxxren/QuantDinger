# ============================================================
# [Default] Stochastic RSI
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Applies a stochastic normalization to RSI. The result is bounded between
# zero and one and uses only trailing observations.
# ============================================================

my_indicator_name = "[Default] Stochastic RSI"
my_indicator_description = "Stochastic normalization of RSI with smoothed %K and %D lines."

# @param rsi_period int 14 RSI lookback period range=2:100:1
# @param stochastic_period int 14 Stochastic normalization period range=2:100:1
# @param k_period int 3 %K smoothing period range=1:50:1
# @param d_period int 3 %D smoothing period range=1:50:1

rsi_period = max(2, int(params.get("rsi_period", 14)))
stochastic_period = max(2, int(params.get("stochastic_period", 14)))
k_period = max(1, int(params.get("k_period", 3)))
d_period = max(1, int(params.get("d_period", 3)))

df = df.copy()
close = df["close"].astype(float)
delta = close.diff()
gains = delta.clip(lower=0.0)
losses = (-delta.clip(upper=0.0))
avg_gain = gains.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()
avg_loss = losses.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()
relative_strength = avg_gain / avg_loss.replace(0.0, np.nan)
rsi = (100.0 - 100.0 / (1.0 + relative_strength)).where(avg_loss != 0.0, 100.0)
rsi_low = rsi.rolling(stochastic_period, min_periods=stochastic_period).min()
rsi_high = rsi.rolling(stochastic_period, min_periods=stochastic_period).max()
stoch_range = (rsi_high - rsi_low).replace(0.0, np.nan)
stoch_rsi = ((rsi - rsi_low) / stoch_range).where(stoch_range != 0.0, 0.5)
k = stoch_rsi.rolling(k_period, min_periods=k_period).mean()
d = k.rolling(d_period, min_periods=d_period).mean()

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "%K", "data": plot_list(k), "color": "#2962FF", "overlay": False},
        {"name": "%D", "data": plot_list(d), "color": "#FF6D00", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
