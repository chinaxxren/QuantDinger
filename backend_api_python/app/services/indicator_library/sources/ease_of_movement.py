# ============================================================
# [Default] Ease of Movement
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Relates midpoint price movement to the range and volume of each bar, then
# smooths it with a trailing simple average. Zero-volume bars remain undefined.
# ============================================================

my_indicator_name = "[Default] Ease of Movement"
my_indicator_description = "Volume-normalized price movement with a smoothed EOM line."

# @param period int 14 Smoothing period range=2:200:1
# @param volume_divisor float 10000.0 Volume scaling divisor range=1.0:1000000000.0:1.0

period = max(2, int(params.get("period", 14)))
volume_divisor = max(1.0, float(params.get("volume_divisor", 10000.0)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
volume = df["volume"].astype(float).clip(lower=0.0)
midpoint = (high + low) / 2.0
midpoint_move = midpoint.diff()
box_ratio = (volume / volume_divisor) / (high - low).replace(0.0, np.nan)
eom_raw = midpoint_move / box_ratio.replace(0.0, np.nan)
eom = eom_raw.rolling(period, min_periods=period).mean()

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "EOM", "data": plot_list(eom), "color": "#26A69A", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
