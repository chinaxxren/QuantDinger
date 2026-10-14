# ============================================================
# [Default] Double Exponential Moving Average
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# DEMA reduces EMA lag by combining a single EMA with the EMA of that EMA.
# Every output at index i depends only on data through index i.
# ============================================================

my_indicator_name = "[Default] Double Exponential Moving Average"
my_indicator_description = "A reduced-lag moving average formed from two exponential averages."

# @param period int 20 EMA lookback period range=2:200:1

period = max(2, int(params.get("period", 20)))

df = df.copy()
close = df["close"].astype(float)
ema_once = close.ewm(span=period, adjust=False, min_periods=period).mean()
ema_twice = ema_once.ewm(span=period, adjust=False, min_periods=period).mean()
dema = 2.0 * ema_once - ema_twice

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "DEMA", "data": plot_list(dema), "color": "#26A69A", "overlay": True},
    ],
    "signals": [],
    "layers": [],
}
