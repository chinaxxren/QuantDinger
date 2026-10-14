# ============================================================
# [Default] ADX
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Average Directional Index with positive and negative directional indicators.
# Values render in a separate pane and are informational only.
# ============================================================

my_indicator_name = "[Default] ADX"
my_indicator_description = "Average Directional Index with +DI and -DI trend-strength lines."

# @param length int 14 Wilder smoothing period range=3:50:1

length = max(2, int(params.get("length", 14)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
previous_high = high.shift(1)
previous_low = low.shift(1)
previous_close = close.shift(1)
up_move = high - previous_high
down_move = previous_low - low
plus_dm = up_move.where((up_move > down_move) & (up_move > 0.0), 0.0)
minus_dm = down_move.where((down_move > up_move) & (down_move > 0.0), 0.0)
true_range = pd.concat([
    high - low,
    (high - previous_close).abs(),
    (low - previous_close).abs(),
], axis=1).max(axis=1)
smoothed_tr = true_range.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean() / smoothed_tr.replace(0.0, np.nan)
minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean() / smoothed_tr.replace(0.0, np.nan)
directional_sum = (plus_di + minus_di).replace(0.0, np.nan)
dx = 100.0 * (plus_di - minus_di).abs() / directional_sum
adx = dx.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()

def plot_list(values):
    return [None if pd.isna(v) else float(v) for v in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "ADX", "data": plot_list(adx), "color": "#FFA726", "overlay": False},
        {"name": "+DI", "data": plot_list(plus_di), "color": "#26A69A", "overlay": False},
        {"name": "-DI", "data": plot_list(minus_di), "color": "#EF5350", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
