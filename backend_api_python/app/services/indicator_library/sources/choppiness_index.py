# ============================================================
# [Default] Choppiness Index
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Compares the rolling sum of true range with the high-low span over the same
# trailing window. Values are clamped to the conventional 0-100 range.
# ============================================================

my_indicator_name = "[Default] Choppiness Index"
my_indicator_description = "Range-versus-true-range measure of market choppiness."

# @param period int 14 Rolling period range=2:200:1

period = max(2, int(params.get("period", 14)))

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
range_sum = true_range.rolling(period, min_periods=period).sum()
rolling_high = high.rolling(period, min_periods=period).max()
rolling_low = low.rolling(period, min_periods=period).min()
price_span = (rolling_high - rolling_low).replace(0.0, np.nan)
ratio = (range_sum / price_span).replace([np.inf, -np.inf], np.nan)
choppiness = 100.0 * np.log10(ratio) / np.log10(float(period))
choppiness = choppiness.replace([np.inf, -np.inf], np.nan).clip(0.0, 100.0)

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Choppiness", "data": plot_list(choppiness), "color": "#AB47BC", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
