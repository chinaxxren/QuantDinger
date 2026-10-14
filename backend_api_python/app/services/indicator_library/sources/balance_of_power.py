# ============================================================
# [Default] Balance of Power
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Measures close location within each bar's open-to-close range relative to
# the full high-low range. Zero-range bars are reported as neutral.
# ============================================================

my_indicator_name = "[Default] Balance of Power"
my_indicator_description = "Per-bar buying and selling pressure from open, high, low, and close."

# @param smooth_period int 1 Smoothing period range=1:100:1

smooth_period = max(1, int(params.get("smooth_period", 1)))

df = df.copy()
open_price = df["open"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
bar_range = high - low
bop = ((close - open_price) / bar_range.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan)
bop = bop.where(bar_range != 0.0, 0.0).clip(-1.0, 1.0)
if smooth_period > 1:
    bop = bop.rolling(smooth_period, min_periods=smooth_period).mean()

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "BOP", "data": plot_list(bop), "color": "#26A69A", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
