# ============================================================
# [Default] Ulcer Index
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Computes the root-mean-square percentage drawdown from the trailing rolling
# high. It measures downside depth and duration without using future prices.
# ============================================================

my_indicator_name = "[Default] Ulcer Index"
my_indicator_description = "Rolling root-mean-square drawdown from recent highs."

# @param period int 14 Drawdown and RMS lookback period range=2:200:1

period = max(2, int(params.get("period", 14)))

df = df.copy()
close = df["close"].astype(float)
rolling_high = close.rolling(period, min_periods=period).max()
drawdown = 100.0 * (close / rolling_high.replace(0.0, np.nan) - 1.0)
squared_drawdown = drawdown.pow(2)
ulcer_index = squared_drawdown.rolling(period, min_periods=period).mean().pow(0.5)

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Ulcer Index", "data": plot_list(ulcer_index), "color": "#EF5350", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
