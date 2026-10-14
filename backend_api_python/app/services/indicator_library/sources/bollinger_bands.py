# ============================================================
# [Default] Bollinger Bands
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Simple moving average with population-standard-deviation bands. Chart only.
# ============================================================

my_indicator_name = "[Default] Bollinger Bands"
my_indicator_description = "Moving-average volatility bands with configurable period and deviation."

# @param length int 20 Moving average period range=5:100:1
# @param deviation float 2.0 Standard deviation multiplier range=0.5:4.0:0.1

length = max(2, int(params.get("length", 20)))
deviation = max(0.1, float(params.get("deviation", 2.0)))

df = df.copy()
close = df["close"].astype(float)
middle = close.rolling(length, min_periods=length).mean()
std = close.rolling(length, min_periods=length).std(ddof=0)
upper = middle + deviation * std
lower = middle - deviation * std

def plot_list(values):
    return [None if pd.isna(v) else float(v) for v in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "BB Upper", "data": plot_list(upper), "color": "#42A5F5", "overlay": True},
        {"name": "BB Middle", "data": plot_list(middle), "color": "#FFA726", "overlay": True},
        {"name": "BB Lower", "data": plot_list(lower), "color": "#42A5F5", "overlay": True},
    ],
    "signals": [],
    "layers": [],
}
