# ============================================================
# [Default] Volume Oscillator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Shows the percentage difference between fast and slow volume EMAs. The
# current bar is included in both trailing exponential averages.
# ============================================================

my_indicator_name = "[Default] Volume Oscillator"
my_indicator_description = "Percentage difference between fast and slow volume averages."

# @param fast_period int 5 Fast volume EMA period range=2:100:1
# @param slow_period int 20 Slow volume EMA period range=3:200:1
# @param signal_period int 5 Signal EMA period range=1:100:1

fast_period = max(2, int(params.get("fast_period", 5)))
slow_period = max(fast_period + 1, int(params.get("slow_period", 20)))
signal_period = max(1, int(params.get("signal_period", 5)))

df = df.copy()
volume = df["volume"].astype(float).clip(lower=0.0)
fast_volume = volume.ewm(span=fast_period, adjust=False, min_periods=fast_period).mean()
slow_volume = volume.ewm(span=slow_period, adjust=False, min_periods=slow_period).mean()
volume_oscillator = 100.0 * (fast_volume - slow_volume) / slow_volume.replace(0.0, np.nan)
volume_oscillator = volume_oscillator.replace([np.inf, -np.inf], np.nan)
signal = volume_oscillator.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Volume Oscillator", "data": plot_list(volume_oscillator), "color": "#26A69A", "overlay": False},
        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
