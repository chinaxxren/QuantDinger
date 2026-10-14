# ============================================================
# [Default] Elder Ray Index
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Bull and bear power measure the distance from an EMA to each bar's high and
# low. The EMA and current OHLC values are causal and use no future bars.
# ============================================================

my_indicator_name = "[Default] Elder Ray Index"
my_indicator_description = "Bull Power and Bear Power measured against an exponential moving average."

# @param period int 13 EMA baseline period range=2:200:1

period = max(2, int(params.get("period", 13)))

df = df.copy()
close = df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
baseline = close.ewm(span=period, adjust=False, min_periods=period).mean()
bull_power = high - baseline
bear_power = low - baseline

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Bull Power", "data": plot_list(bull_power), "color": "#26A69A", "overlay": False},
        {"name": "Bear Power", "data": plot_list(bear_power), "color": "#EF5350", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
