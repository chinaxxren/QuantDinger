# ============================================================
# Percentage Volume Oscillator
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Percentage difference between short and long volume EMAs, with a signal line
# and histogram. EMA seeding follows the library convention: the first value is
# the simple average of the first complete period.
# ============================================================

my_indicator_name = "Percentage Volume Oscillator"
my_indicator_description = "Percentage difference between short and long volume EMAs."

# @param short_period int 12 Short volume EMA period range=2:100:1
# @param long_period int 26 Long volume EMA period range=3:200:1
# @param signal_period int 9 Signal EMA period range=1:100:1

short_period = int(params.get("short_period", 12))
long_period = int(params.get("long_period", 26))
signal_period = int(params.get("signal_period", 9))
volume = pd.to_numeric(df["volume"], errors="coerce").clip(lower=0.0)

def seeded_ema(values, period):
    numeric = pd.to_numeric(values, errors="coerce")
    data = numeric.to_numpy(dtype=float, copy=False)
    result = pd.Series(np.nan, index=numeric.index, dtype=float)
    valid_positions = np.flatnonzero(np.isfinite(data))
    if len(valid_positions) < period:
        return result
    seed_position = valid_positions[period - 1]
    result.iloc[seed_position] = float(np.mean(data[valid_positions[:period]]))
    alpha = 2.0 / (period + 1.0)
    for index in range(seed_position + 1, len(data)):
        current = data[index]
        previous = result.iloc[index - 1]
        result.iloc[index] = previous if not np.isfinite(current) else previous + alpha * (current - previous)
    return result

short_ema = seeded_ema(volume, short_period)
long_ema = seeded_ema(volume, long_period)
pvo = 100.0 * (short_ema - long_ema) / long_ema.replace(0.0, np.nan)
pvo = pvo.replace([np.inf, -np.inf], np.nan)
signal = seeded_ema(pvo, signal_period)
histogram = pvo - signal

output = {
    "name": my_indicator_name,
    "plots": [
        {"key": "pvo", "title": "PVO", "data": pvo.tolist(), "color": "#2962ff", "overlay": False},
        {"key": "signal", "title": "Signal", "data": signal.tolist(), "color": "#ff6d00", "overlay": False},
        {"key": "histogram", "title": "Histogram", "data": histogram.tolist(), "type": "histogram", "color": "#26a69a", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
