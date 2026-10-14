# ============================================================
# [Default] Mass Index
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Sums the ratio of a range EMA to its second EMA over a trailing window.
# This volatility-expansion measure is causal and does not imply trade signals.
# ============================================================

my_indicator_name = "[Default] Mass Index"
my_indicator_description = "Range-expansion index from double-smoothed high-low movement."

# @param ema_period int 9 Range EMA period range=2:100:1
# @param sum_period int 25 Rolling sum period range=2:200:1

aema_period = max(2, int(params.get("ema_period", 9)))
sum_period = max(2, int(params.get("sum_period", 25)))

df = df.copy()
bar_range = (df["high"].astype(float) - df["low"].astype(float)).clip(lower=0.0)
first_ema = bar_range.ewm(span=aema_period, adjust=False, min_periods=aema_period).mean()
second_ema = first_ema.ewm(span=aema_period, adjust=False, min_periods=aema_period).mean()
ema_ratio = first_ema / second_ema.replace(0.0, np.nan)
mass_index = ema_ratio.rolling(sum_period, min_periods=sum_period).sum()

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Mass Index", "data": plot_list(mass_index), "color": "#AB47BC", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
