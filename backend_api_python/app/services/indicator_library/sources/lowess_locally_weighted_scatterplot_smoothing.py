# ============================================================
# [Default] LOWESS Locally Weighted Scatterplot Smoothing
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal two-stage smoother inspired by the MiniBT/ChartPrime LOWESS
# conversion: volatility-scaled Gaussian weighting followed by a local
# cubic-weight smoother. Each output uses only the current and prior bars.
# ============================================================

my_indicator_name = "[Default] LOWESS Locally Weighted Scatterplot Smoothing"
my_indicator_description = "Volatility-weighted Gaussian price smoother with a causal LOWESS stage."

# @param length int 100 Gaussian and volatility lookback range=10:200:1
# @param malen int 100 LOWESS smoothing lookback range=5:200:1

length = max(10, int(params.get("length", 100)))
malen = max(5, int(params.get("malen", 100)))

df = df.copy()
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
n = len(df)

previous_close = close.shift(1)
true_range = pd.concat(
    [high - low, (high - previous_close).abs(), (low - previous_close).abs()],
    axis=1,
).max(axis=1)
atr = true_range.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
stdev = close.rolling(length, min_periods=length).std(ddof=0)
sigma = ((atr + stdev) / 2.0).to_numpy()
prices = close.to_numpy()
gaussian_ma = np.full(n, np.nan, dtype=float)

for end in range(length - 1, n):
    current_sigma = sigma[end]
    if not (np.isfinite(current_sigma) and current_sigma > 0.0):
        continue

    # Reverse the trailing window so index zero is the current candle, as in
    # the reference implementation. Prefix extrema are causal rolling extrema.
    window = prices[end - length + 1:end + 1][::-1]
    if not np.isfinite(window).all():
        continue
    prefix_high = np.maximum.accumulate(window)
    prefix_low = np.minimum.accumulate(window)
    offsets = np.arange(length, dtype=float)
    weights = np.exp(-np.square((offsets - (length - 1.0)) / (2.0 * current_sigma)) / 2.0)
    values = (prefix_high + prefix_low) / 2.0
    weight_sum = float(weights.sum())
    if weight_sum > 0.0:
        gaussian_ma[end] = float(np.dot(values, weights) / weight_sum)

# LOWESS stage mirrors the reference cubic weighting over a reversed rolling
# window. Its oldest/current alignment is fixed per endpoint and never uses
# future candles.
smoothed = np.full(n, np.nan, dtype=float)
lowess_offsets = np.arange(malen, dtype=float)
lowess_weights = np.power(1.0 - np.power(lowess_offsets / malen, 3.0), 3.0)
lowess_weight_sum = float(lowess_weights.sum())
for end in range(malen - 1, n):
    window = gaussian_ma[end - malen + 1:end + 1][::-1]
    if not np.isfinite(window).all() or lowess_weight_sum <= 0.0:
        continue
    intercept = float(np.dot(lowess_weights, window) / lowess_weight_sum)
    slope_proxy = float(np.dot(lowess_weights, lowess_offsets) / lowess_weight_sum)
    smoothed[end] = intercept + slope_proxy / (malen - 1.0) / 2000.0


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Gaussian MA", "data": plot_list(gaussian_ma), "color": "#42A5F5", "overlay": True},
        {"name": "LOWESS", "data": plot_list(smoothed), "color": "#FF9800", "overlay": True},
    ],
    "signals": [],
    "layers": [],
}
