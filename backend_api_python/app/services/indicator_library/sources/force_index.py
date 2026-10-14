# ============================================================
# [Default] Force Index
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Force Index multiplies close-to-close change by traded volume and smooths
# the result. The first bar is undefined because it has no prior close.
# ============================================================

my_indicator_name = "[Default] Force Index"
my_indicator_description = "Volume-weighted price-change momentum with configurable EMA smoothing."

# @param period int 13 EMA smoothing period range=1:200:1

period = max(1, int(params.get("period", 13)))

df = df.copy()
close = df["close"].astype(float)
volume = df["volume"].astype(float).clip(lower=0.0)
raw_force = close.diff() * volume
force_index = raw_force.ewm(span=period, adjust=False, min_periods=period).mean()

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Force Index", "data": plot_list(force_index), "color": "#2962FF", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
