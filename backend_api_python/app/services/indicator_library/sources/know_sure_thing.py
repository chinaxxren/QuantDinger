# ============================================================
# [Default] Know Sure Thing
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Weighted sum of four smoothed rate-of-change series. Each ROC, average,
# and signal uses trailing data only, keeping all historical values causal.
# ============================================================

my_indicator_name = "[Default] Know Sure Thing"
my_indicator_description = "Multi-horizon momentum oscillator with a signal line."

# @param roc1_period int 10 First ROC period range=2:100:1
# @param roc2_period int 15 Second ROC period range=2:150:1
# @param roc3_period int 20 Third ROC period range=2:200:1
# @param roc4_period int 30 Fourth ROC period range=2:250:1
# @param signal_period int 9 Signal SMA period range=2:100:1

roc_periods = [
    max(2, int(params.get("roc1_period", 10))),
    max(2, int(params.get("roc2_period", 15))),
    max(2, int(params.get("roc3_period", 20))),
    max(2, int(params.get("roc4_period", 30))),
]
signal_period = max(2, int(params.get("signal_period", 9)))

df = df.copy()
close = df["close"].astype(float)
smoothed_rocs = []
for roc_period in roc_periods:
    base = close.shift(roc_period).replace(0.0, np.nan)
    roc = 100.0 * (close / base - 1.0)
    smoothed_rocs.append(roc.rolling(roc_period, min_periods=roc_period).mean())
kst = (
    smoothed_rocs[0]
    + 2.0 * smoothed_rocs[1]
    + 3.0 * smoothed_rocs[2]
    + 4.0 * smoothed_rocs[3]
)
signal = kst.rolling(signal_period, min_periods=signal_period).mean()

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "KST", "data": plot_list(kst), "color": "#2962FF", "overlay": False},
        {"name": "Signal", "data": plot_list(signal), "color": "#FF6D00", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
