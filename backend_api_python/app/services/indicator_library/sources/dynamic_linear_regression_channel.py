# ============================================================
# [Default] Dynamic Linear Regression Channel
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Rolling least-squares regression using only current and prior bars. The
# channel width is based on residual standard deviation within each window.
# ============================================================

my_indicator_name = "[Default] Dynamic Linear Regression Channel"
my_indicator_description = "Causal rolling linear-regression centerline with residual-deviation bands."

# @param period int 50 Regression window range=5:200:1
# @param deviation float 2.0 Channel width in residual standard deviations range=0.5:4.0:0.25

period = max(3, int(params.get("period", 50)))
deviation = max(0.0, float(params.get("deviation", 2.0)))

df = df.copy()
close = df["close"].astype(float).to_numpy()
center = np.full(len(close), np.nan)
upper = np.full(len(close), np.nan)
lower = np.full(len(close), np.nan)
x = np.arange(period, dtype=float)
x_mean = float(period - 1) / 2.0
x_centered = x - x_mean
x_denom = sum(float(value) * float(value) for value in x_centered)
for i in range(period - 1, len(close)):
    window = close[i - period + 1:i + 1]
    if not np.isfinite(window).all():
        continue
    y_mean = sum(float(value) for value in window) / period
    covariance = sum(float(x_centered[j]) * (float(window[j]) - y_mean) for j in range(period))
    slope = float(covariance / x_denom)
    fitted = y_mean + slope * x_centered
    squared_error = sum((float(window[j]) - float(fitted[j])) ** 2 for j in range(period))
    residual_std = float(np.sqrt(squared_error / period))
    center[i] = float(fitted[-1])
    upper[i] = center[i] + deviation * residual_std
    lower[i] = center[i] - deviation * residual_std

def plot_list(values):
    return [None if not np.isfinite(v) else float(v) for v in values]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Regression", "data": plot_list(center), "color": "#FFB300", "overlay": True},
        {"name": "Regression Upper", "data": plot_list(upper), "color": "#26A69A", "overlay": True},
        {"name": "Regression Lower", "data": plot_list(lower), "color": "#EF5350", "overlay": True},
    ],
    "signals": [],
    "layers": [],
}
