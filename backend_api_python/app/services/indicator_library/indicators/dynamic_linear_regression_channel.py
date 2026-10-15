"""Chart-only source for the dynamic_linear_regression_channel indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Dynamic Linear Regression Channel\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Rolling least-squares regression using only current and prior bars. The\n"
    "# channel width is based on residual standard deviation within each window.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Dynamic Linear Regression Channel"\n'
    'my_indicator_description = "Causal rolling linear-regression centerline with residual-deviation bands."\n'
    "\n"
    "# @param period int 50 Regression window range=5:200:1\n"
    "# @param deviation float 2.0 Channel width in residual standard deviations range=0.5:4.0:0.25\n"
    "\n"
    'period = max(3, int(params.get("period", 50)))\n'
    'deviation = max(0.0, float(params.get("deviation", 2.0)))\n'
    "\n"
    "df = df.copy()\n"
    'close = df["close"].astype(float).to_numpy()\n'
    "center = np.full(len(close), np.nan)\n"
    "upper = np.full(len(close), np.nan)\n"
    "lower = np.full(len(close), np.nan)\n"
    "x = np.arange(period, dtype=float)\n"
    "x_mean = float(period - 1) / 2.0\n"
    "x_centered = x - x_mean\n"
    "x_denom = sum(float(value) * float(value) for value in x_centered)\n"
    "for i in range(period - 1, len(close)):\n"
    "    window = close[i - period + 1:i + 1]\n"
    "    if not np.isfinite(window).all():\n"
    "        continue\n"
    "    y_mean = sum(float(value) for value in window) / period\n"
    "    covariance = sum(float(x_centered[j]) * (float(window[j]) - y_mean) for j in range(period))\n"
    "    slope = float(covariance / x_denom)\n"
    "    fitted = y_mean + slope * x_centered\n"
    "    squared_error = sum((float(window[j]) - float(fitted[j])) ** 2 for j in range(period))\n"
    "    residual_std = float(np.sqrt(squared_error / period))\n"
    "    center[i] = float(fitted[-1])\n"
    "    upper[i] = center[i] + deviation * residual_std\n"
    "    lower[i] = center[i] - deviation * residual_std\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(v) else float(v) for v in values]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Regression", "data": plot_list(center), "color": "#FFB300", "overlay": True},\n'
    '        {"name": "Regression Upper", "data": plot_list(upper), "color": "#26A69A", "overlay": True},\n'
    '        {"name": "Regression Lower", "data": plot_list(lower), "color": "#EF5350", "overlay": True},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "layers": [],\n'
    "}\n"
)
