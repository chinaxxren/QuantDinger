# ============================================================
# [Default] John Ehlers The Price Radio
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Chart-only AM/FM demodulation of the candle-body price signal. The AM
# envelope uses a four-bar rectifier peak followed by an SMA; the FM line
# clamps the signal and applies Ehlers' causal Super Smoother recurrence.
# ============================================================

my_indicator_name = "[Default] John Ehlers The Price Radio"
my_indicator_description = "AM volatility envelope and FM Super Smoother of candle-body price movement."

# @param am_period int 8 AM envelope smoothing period range=2:100:1
# @param fm_period int 30 FM Super Smoother period range=3:100:1
# @param fm_gain float 10.0 FM demodulator input gain range=0.1:100.0:0.1

am_period = max(2, int(params.get("am_period", 8)))
fm_period = max(3, int(params.get("fm_period", 30)))
fm_gain = max(0.1, float(params.get("fm_gain", 10.0)))

df = df.copy()
open_price = df["open"].astype(float).to_numpy()
close = df["close"].astype(float).to_numpy()
n = len(df)

# The source signal is the candle body's signed price movement.
signal = close - open_price
rectified_peak = pd.Series(np.abs(signal)).rolling(4, min_periods=4).max()
am = rectified_peak.rolling(am_period, min_periods=am_period).mean().to_numpy()

# Clamp amplitude before low-pass integration, as in the FM demodulator.
fm_input = np.clip(fm_gain * signal, -1.0, 1.0)
a1 = float(np.exp(-1.4142135623730951 * np.pi / fm_period))
b1 = 2.0 * a1 * float(np.cos(1.4142135623730951 * np.pi / fm_period))
c2 = b1
c3 = -(a1 * a1)
c1 = 1.0 - c2 - c3
fm = np.full(n, np.nan, dtype=float)
if n:
    # Seed with the first available input. Subsequent values use only current
    # and prior inputs/outputs, so appending candles leaves the prefix intact.
    fm[0] = c1 * fm_input[0]
    if n > 1:
        fm[1] = c1 * (fm_input[1] + fm_input[0]) / 2.0 + c2 * fm[0]
    for i in range(2, n):
        fm[i] = (
            c1 * (fm_input[i] + fm_input[i - 1]) / 2.0
            + c2 * fm[i - 1]
            + c3 * fm[i - 2]
        )


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "AM", "data": plot_list(am), "color": "#EF5350", "overlay": False},
        {"name": "FM", "data": plot_list(fm), "color": "#42A5F5", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
