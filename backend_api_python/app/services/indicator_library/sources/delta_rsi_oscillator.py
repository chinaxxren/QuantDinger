# ============================================================
# [Default] Delta RSI Oscillator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Difference between fast and slow Wilder RSI readings. The spread highlights
# momentum acceleration/deceleration; the signal and histogram are chart-only.
# ============================================================

my_indicator_name = "[Default] Delta RSI Oscillator"
my_indicator_description = "Fast-minus-slow RSI momentum spread with signal and histogram."

# @param fast_period int 7 Fast RSI period range=2:100:1
# @param slow_period int 21 Slow RSI period range=3:200:1
# @param signal_period int 5 Signal EMA period range=2:100:1

fast_period = max(2, int(params.get("fast_period", 7)))
slow_period = max(fast_period + 1, int(params.get("slow_period", 21)))
signal_period = max(2, int(params.get("signal_period", 5)))

df = df.copy()
close = df["close"].astype(float)
change = close.diff()
gain = change.clip(lower=0.0)
loss = -change.clip(upper=0.0)

def calculate_rsi(period):
    average_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    average_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    relative_strength = average_gain / average_loss.replace(0.0, np.nan)
    values = 100.0 - 100.0 / (1.0 + relative_strength)
    values = values.where(average_loss != 0.0, 100.0)
    values = values.where(average_gain != 0.0, 0.0)
    return values.fillna(50.0)

fast_rsi = calculate_rsi(fast_period)
slow_rsi = calculate_rsi(slow_period)
delta_rsi = fast_rsi - slow_rsi
signal = delta_rsi.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
histogram = delta_rsi - signal

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Delta RSI", "data": plot_list(delta_rsi), "color": "#2962FF", "overlay": False},
        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},
        {"name": "Histogram", "data": plot_list(histogram), "color": "#26A69A", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
