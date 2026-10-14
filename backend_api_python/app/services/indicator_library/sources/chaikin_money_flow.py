# ============================================================
# [Default] Chaikin Money Flow
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Rolling volume-weighted close-location value. Zero-range bars contribute no
# money flow, and the ratio is undefined when the window has no traded volume.
# ============================================================

my_indicator_name = "[Default] Chaikin Money Flow"
my_indicator_description = "Rolling volume-weighted buying and selling pressure oscillator."

# @param period int 20 Rolling period range=2:200:1

period = max(2, int(params.get("period", 20)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
volume = df["volume"].astype(float).clip(lower=0.0)
price_range = high - low
money_flow_multiplier = ((close - low) - (high - close)) / price_range.replace(0.0, np.nan)
money_flow_multiplier = money_flow_multiplier.replace([np.inf, -np.inf], np.nan).fillna(0.0)
raw_money_flow = money_flow_multiplier * volume
volume_sum = volume.rolling(period, min_periods=period).sum()
flow_sum = raw_money_flow.rolling(period, min_periods=period).sum()
cmf = (flow_sum / volume_sum.replace(0.0, np.nan)).clip(-1.0, 1.0)

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "CMF", "data": plot_list(cmf), "color": "#26A69A", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
