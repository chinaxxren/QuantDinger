# ============================================================
# [Default] Relative Volatility Index
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Assigns rolling price standard deviation to up/down movement and compares
# their Wilder-smoothed totals. The calculation uses only trailing data.
# ============================================================

my_indicator_name = "[Default] Relative Volatility Index"
my_indicator_description = "Directional volatility oscillator normalized to a 0-100 scale."

# @param period int 14 Volatility and smoothing period range=2:200:1

period = max(2, int(params.get("period", 14)))

df = df.copy()
close = df["close"].astype(float)
change = close.diff()
volatility = close.rolling(period, min_periods=period).std(ddof=0)
up_volatility = volatility.where(change > 0.0, 0.0)
down_volatility = volatility.where(change < 0.0, 0.0)
up_average = up_volatility.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
down_average = down_volatility.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
volatility_sum = up_average + down_average
rvi = 100.0 * up_average / volatility_sum.replace(0.0, np.nan)
rvi = rvi.where(volatility_sum != 0.0, 50.0).clip(0.0, 100.0)

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "RVI", "data": plot_list(rvi), "color": "#7E57C2", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
