# ============================================================
# [Default] Ichimoku Cloud
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# This chart-safe representation exposes the current Tenkan-sen, Kijun-sen,
# and cloud boundaries without forward-shifting values. That keeps each
# returned point aligned with its source candle and prevents look-ahead bias.
# ============================================================

my_indicator_name = "[Default] Ichimoku Cloud"
my_indicator_description = "Causal Ichimoku conversion, base, and cloud boundary lines."

# @param conversion_period int 9 Conversion line lookback range=2:100:1
# @param base_period int 26 Base line lookback range=2:200:1
# @param span_b_period int 52 Cloud boundary lookback range=2:300:1

conversion_period = max(2, int(params.get("conversion_period", 9)))
base_period = max(2, int(params.get("base_period", 26)))
span_b_period = max(2, int(params.get("span_b_period", 52)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
conversion = (high.rolling(conversion_period, min_periods=conversion_period).max() + low.rolling(conversion_period, min_periods=conversion_period).min()) / 2.0
base = (high.rolling(base_period, min_periods=base_period).max() + low.rolling(base_period, min_periods=base_period).min()) / 2.0
span_a = (conversion + base) / 2.0
span_b = (high.rolling(span_b_period, min_periods=span_b_period).max() + low.rolling(span_b_period, min_periods=span_b_period).min()) / 2.0

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Tenkan-sen", "data": plot_list(conversion), "color": "#26A69A", "overlay": True},
        {"name": "Kijun-sen", "data": plot_list(base), "color": "#EF5350", "overlay": True},
        {"name": "Senkou Span A", "data": plot_list(span_a), "color": "#66BB6A", "overlay": True},
        {"name": "Senkou Span B", "data": plot_list(span_b), "color": "#AB47BC", "overlay": True},
    ],
    "signals": [],
    "layers": [],
}
