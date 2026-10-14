# ============================================================
# [Default] Chaikin Oscillator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# The oscillator is the difference between fast and slow EMAs of the
# accumulation/distribution line, using only current and prior bars.
# ============================================================

my_indicator_name = "[Default] Chaikin Oscillator"
my_indicator_description = "Fast-minus-slow EMA of volume-weighted accumulation and distribution."

# @param fast_period int 3 Fast EMA period range=1:100:1
# @param slow_period int 10 Slow EMA period range=2:200:1

fast_period = max(1, int(params.get("fast_period", 3)))
slow_period = max(2, int(params.get("slow_period", 10)))
if fast_period >= slow_period:
    raise ValueError("fast_period must be less than slow_period")

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
volume = df["volume"].astype(float).clip(lower=0.0)
bar_range = high - low
money_flow_multiplier = ((2.0 * close - high - low) / bar_range.replace(0.0, np.nan)).fillna(0.0)
accumulation_distribution = (money_flow_multiplier * volume).cumsum()
fast = accumulation_distribution.ewm(span=fast_period, adjust=False, min_periods=fast_period).mean()
slow = accumulation_distribution.ewm(span=slow_period, adjust=False, min_periods=slow_period).mean()
chaikin = fast - slow

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Chaikin Oscillator", "data": plot_list(chaikin), "color": "#42A5F5", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
