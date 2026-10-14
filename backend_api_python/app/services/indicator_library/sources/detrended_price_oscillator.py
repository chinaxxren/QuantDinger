# ============================================================
# [Default] Detrended Price Oscillator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Compares price with a lagged trailing moving average to emphasize cyclical
# deviation. The average is shifted backward in time, never forward-looking.
# ============================================================

my_indicator_name = "[Default] Detrended Price Oscillator"
my_indicator_description = "Price deviation from a lagged trailing simple moving average."

# @param period int 20 Moving average and cycle period range=2:200:1

period = max(2, int(params.get("period", 20)))

df = df.copy()
close = df["close"].astype(float)
cycle_offset = period // 2 + 1
lagged_average = close.rolling(period, min_periods=period).mean().shift(cycle_offset)
dpo = close - lagged_average

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "DPO", "data": plot_list(dpo), "color": "#2962FF", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
