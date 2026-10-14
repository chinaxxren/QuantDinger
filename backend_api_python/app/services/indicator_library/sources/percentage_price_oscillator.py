# ============================================================
# [Default] Percentage Price Oscillator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Expresses the fast/slow EMA spread as a percentage of the slow EMA, with a
# trailing signal EMA and histogram. All smoothing is causal.
# ============================================================

my_indicator_name = "[Default] Percentage Price Oscillator"
my_indicator_description = "Percentage-scaled EMA spread with signal and histogram."

# @param fast_period int 12 Fast EMA period range=2:100:1
# @param slow_period int 26 Slow EMA period range=3:200:1
# @param signal_period int 9 Signal EMA period range=2:100:1

fast_period = max(2, int(params.get("fast_period", 12)))
slow_period = max(fast_period + 1, int(params.get("slow_period", 26)))
signal_period = max(2, int(params.get("signal_period", 9)))

df = df.copy()
close = df["close"].astype(float)
fast = close.ewm(span=fast_period, adjust=False, min_periods=fast_period).mean()
slow = close.ewm(span=slow_period, adjust=False, min_periods=slow_period).mean()
ppo = 100.0 * (fast - slow) / slow.replace(0.0, np.nan)
ppo = ppo.replace([np.inf, -np.inf], np.nan)
signal = ppo.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
histogram = ppo - signal

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "PPO", "data": plot_list(ppo), "color": "#2962FF", "overlay": False},
        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},
        {"name": "Histogram", "data": plot_list(histogram), "color": "#26A69A", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
