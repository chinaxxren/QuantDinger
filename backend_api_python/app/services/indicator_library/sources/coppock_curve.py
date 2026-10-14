# ============================================================
# [Default] Coppock Curve
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Weighted moving average of two rate-of-change series. All comparisons are
# against prior closes and the weighted average is trailing (not centered).
# ============================================================

my_indicator_name = "[Default] Coppock Curve"
my_indicator_description = "Long-term momentum curve from weighted dual rate-of-change readings."

# @param long_roc int 14 Long ROC period range=2:200:1
# @param short_roc int 11 Short ROC period range=2:200:1
# @param wma_period int 10 Weighted moving average period range=2:100:1

long_roc = max(2, int(params.get("long_roc", 14)))
short_roc = max(2, int(params.get("short_roc", 11)))
wma_period = max(2, int(params.get("wma_period", 10)))

df = df.copy()
close = df["close"].astype(float)
long_base = close.shift(long_roc).replace(0.0, np.nan)
short_base = close.shift(short_roc).replace(0.0, np.nan)
roc_sum = 100.0 * ((close / long_base - 1.0) + (close / short_base - 1.0))
weights = np.arange(1.0, wma_period + 1.0)
weight_total = float(weights.sum())
def weighted_average(values):
    return float(np.dot(values, weights) / weight_total)

coppock = roc_sum.rolling(wma_period, min_periods=wma_period).apply(weighted_average, raw=True)

def plot_list(values):
    return [None if pd.isna(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Coppock Curve", "data": plot_list(coppock), "color": "#2962FF", "overlay": False},
    ],
    "signals": [],
    "layers": [],
}
