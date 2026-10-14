# ============================================================
# [Default] VWAP Price Channel
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Rolling volume-weighted typical-price mean and standard-deviation bands.
# A rolling window is used so the calculation works consistently on any
# chart history without exchange-session assumptions.
# ============================================================

my_indicator_name = "[Default] VWAP Price Channel"
my_indicator_description = "Rolling volume-weighted price channel with deviation bands."

# @param period int 30 Rolling VWAP window range=5:200:1
# @param deviation float 1.5 Band deviation multiplier range=0.25:5.0:0.25

period = max(2, int(params.get("period", 30)))
deviation = max(0.0, float(params.get("deviation", 1.5)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
volume = df["volume"].astype(float).clip(lower=0.0)
typical = (high + low + close) / 3.0
weighted_price = typical * volume
rolling_volume = volume.rolling(period, min_periods=period).sum()
vwap = weighted_price.rolling(period, min_periods=period).sum() / rolling_volume.replace(0.0, np.nan)
weighted_sq = (typical * typical * volume).rolling(period, min_periods=period).sum() / rolling_volume.replace(0.0, np.nan)
variance = (weighted_sq - vwap * vwap).clip(lower=0.0)
std = np.sqrt(variance)
upper = vwap + deviation * std
lower = vwap - deviation * std

def plot_list(values):
    return [None if pd.isna(v) else float(v) for v in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "VWAP", "data": plot_list(vwap), "color": "#2962FF", "overlay": True},
        {"name": "VWAP Upper", "data": plot_list(upper), "color": "#AB47BC", "overlay": True},
        {"name": "VWAP Lower", "data": plot_list(lower), "color": "#AB47BC", "overlay": True},
    ],
    "signals": [],
    "layers": [],
}
