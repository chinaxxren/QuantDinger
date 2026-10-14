# ============================================================
# [Default] TRIX
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Triple-smoothed EMA rate of change. The percentage change compares with the
# previous bar only and the signal is a trailing EMA, so the series is causal.
# ============================================================

my_indicator_name = "[Default] TRIX"
my_indicator_description = "Triple-smoothed EMA momentum with a signal line."

# @param period int 15 Triple EMA period range=2:200:1
# @param signal_period int 9 Signal EMA period range=2:100:1

period = max(2, int(params.get("period", 15)))
signal_period = max(2, int(params.get("signal_period", 9)))

df = df.copy()
close = df["close"].astype(float)
ema1 = close.ewm(span=period, adjust=False, min_periods=period).mean()
ema2 = ema1.ewm(span=period, adjust=False, min_periods=period).mean()
ema3 = ema2.ewm(span=period, adjust=False, min_periods=period).mean()
trix = 100.0 * ema3.pct_change(fill_method=None)
trix = trix.replace([np.inf, -np.inf], np.nan)
signal = trix.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "TRIX", "data": plot_list(trix), "color": "#2962FF", "overlay": False},
        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
