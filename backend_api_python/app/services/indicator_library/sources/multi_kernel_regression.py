# ============================================================
# [Default] Multi Kernel Regression [ChartPrime]
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal Nadaraya-Watson kernel regression. The source indicator has a
# repainting mode, but this library implementation intentionally uses only the
# trailing window at each bar so historical values never change.
# ============================================================

my_indicator_name = "[Default] Multi Kernel Regression [ChartPrime]"
my_indicator_description = (
    "Causal multi-kernel regression with optional deviation bands and confirmed "
    "chart-only direction signals."
)

# @param repaint bool True Compatibility switch; the chart implementation remains non-repainting
# @param kernel string Laplace Kernel type: Triangular, Gaussian, Epanechnikov, Logistic, Log Logistic, Cosine, Sinc, Laplace, Quartic, Parabolic, Exponential, Silverman, Cauchy, Tent, Wave, Power, or Morters
# @param bandwidth int 14 Kernel lookback range=2:200:1
# @param source string close Price source: close, hl2, hlc3, or ohlc4
# @param deviations float 2.0 Deviation-band multiplier range=0.0:10.0:0.25
# @param enable bool False Show deviation bands
# @param bullish_color string #54C294 Rising regression color
# @param bearish_color string #EB3939 Falling regression color
# @param confirm_bars int 10 Consecutive direction bars required for a reversal range=1:100:1


def as_bool(value, default):
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in ("false", "0", "no", "off"):
        return False
    if text in ("true", "1", "yes", "on"):
        return True
    return bool(value)


def clamp_int(value, default, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(maximum, max(minimum, parsed))


def clamp_float(value, default, minimum, maximum):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    if not np.isfinite(parsed):
        parsed = default
    return min(maximum, max(minimum, parsed))


def kernel_weight(squared_distance, kind):
    """Return a normalized non-negative kernel weight for a unit bandwidth."""
    radius = float(np.sqrt(max(0.0, squared_distance)))
    name = str(kind).strip().lower().replace("-", " ").replace("_", " ")
    name = " ".join(name.split())
    bounded = radius <= 1.0

    if name == "triangular":
        value = 1.0 - radius if bounded else 0.0
    elif name == "gaussian":
        value = float(np.exp(-0.5 * radius * radius))
    elif name == "epanechnikov":
        value = 0.75 * (1.0 - radius * radius) if bounded else 0.0
    elif name == "logistic":
        # Symmetric logistic density. The constant is immaterial after
        # normalization, but retaining it keeps the kernel well scaled.
        value = 1.0 / (2.0 + float(np.exp(radius)) + float(np.exp(-radius)))
    elif name == "log logistic":
        value = 1.0 / (1.0 + float(np.exp(radius)))
    elif name == "cosine":
        value = (np.pi / 4.0) * float(np.cos(np.pi * radius / 2.0)) if bounded else 0.0
    elif name == "sinc":
        value = 1.0 if radius == 0.0 else float(np.sin(np.pi * radius) / (np.pi * radius))
    elif name == "laplace":
        value = 0.5 * float(np.exp(-radius))
    elif name == "quartic":
        value = (15.0 / 16.0) * (1.0 - radius * radius) ** 2 if bounded else 0.0
    elif name == "parabolic":
        value = 0.75 * (1.0 - radius * radius) if bounded else 0.0
    elif name == "exponential":
        value = 0.5 * float(np.exp(-radius))
    elif name == "silverman":
        value = (
            1.0 / (2.0 * float(np.sqrt(2.0)))
        ) * float(np.exp(-radius / float(np.sqrt(2.0)))) * float(
            np.sin(radius / float(np.sqrt(2.0)) + np.pi / 4.0)
        )
    elif name == "cauchy":
        value = 1.0 / (np.pi * (1.0 + radius * radius))
    elif name == "tent":
        value = 1.0 - radius if bounded else 0.0
    elif name == "wave":
        value = (1.0 - radius) * float(np.cos(np.pi * radius)) if bounded else 0.0
    elif name == "power":
        value = (1.0 - radius ** 3) if bounded else 0.0
    elif name == "morters":
        value = (1.0 - radius * radius) ** 2 if bounded else 0.0
    else:
        value = 0.5 * float(np.exp(-radius))

    if not np.isfinite(value):
        return 0.0
    # Oscillatory kernels can become negative near their boundary. Clipping
    # protects the regression denominator while preserving their shape.
    return max(0.0, float(value))


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


repaint_requested = as_bool(params.get("repaint", True), True)
kernel = str(params.get("kernel", "Laplace")).strip()
bandwidth = clamp_int(params.get("bandwidth", 14), 14, 2, 200)
source_name = str(params.get("source", "close")).strip().lower()
deviations = clamp_float(params.get("deviations", 2.0), 2.0, 0.0, 10.0)
enable = as_bool(params.get("enable", False), False)
bullish_color = str(params.get("bullish_color", "#54C294"))
bearish_color = str(params.get("bearish_color", "#EB3939"))
confirm_bars = clamp_int(params.get("confirm_bars", 10), 10, 1, 100)


df = df.copy()
close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)
high = pd.to_numeric(df["high"], errors="coerce").to_numpy(dtype=float)
low = pd.to_numeric(df["low"], errors="coerce").to_numpy(dtype=float)
open_values = (
    pd.to_numeric(df["open"], errors="coerce").to_numpy(dtype=float)
    if "open" in df
    else close.copy()
)

if source_name == "hl2":
    source = (high + low) / 2.0
elif source_name == "hlc3":
    source = (high + low + close) / 3.0
elif source_name == "ohlc4":
    source = (open_values + high + low + close) / 4.0
else:
    source_name = "close"
    source = close.copy()

n = len(source)
nrp = np.full(n, np.nan, dtype=float)
nrp_std = np.full(n, np.nan, dtype=float)
weights = np.asarray(
    [kernel_weight((age * age) / float(bandwidth * bandwidth), kernel) for age in range(bandwidth)],
    dtype=float,
)

# The current candle is age zero and the oldest candle is age bandwidth - 1.
# This is the non-repainting branch: every endpoint is calculated once from a
# fixed trailing window and is independent of candles that arrive later.
for index in range(bandwidth - 1, n):
    window = source[index - bandwidth + 1:index + 1]
    if not np.isfinite(window).all():
        continue
    weight_sum = float(np.sum(weights))
    if weight_sum <= 0.0:
        continue
    nrp[index] = float(np.dot(window[::-1], weights) / weight_sum)
    errors = window - nrp[index]
    nrp_std[index] = float(np.sqrt(np.sum(errors * errors) / max(1, bandwidth - 1)))

nrp_up = np.full(n, np.nan, dtype=float)
nrp_dn = np.full(n, np.nan, dtype=float)
upper = np.full(n, np.nan, dtype=float)
lower = np.full(n, np.nan, dtype=float)
long_signal = np.full(n, np.nan, dtype=float)
short_signal = np.full(n, np.nan, dtype=float)

# Split the regression into two same-valued lines so the renderer can preserve
# the source indicator's bullish/bearish line colors without changing layout.
for index in range(n):
    if not np.isfinite(nrp[index]):
        continue
    if enable and np.isfinite(nrp_std[index]):
        upper[index] = nrp[index] + deviations * nrp_std[index]
        lower[index] = nrp[index] - deviations * nrp_std[index]
    if index == 0 or not np.isfinite(nrp[index - 1]):
        nrp_up[index] = nrp[index]
    elif nrp[index] >= nrp[index - 1]:
        nrp_up[index] = nrp[index]
    else:
        nrp_dn[index] = nrp[index]

# Confirm a direction only after it has held for confirm_bars consecutive
# valid slopes. A signal is a chart marker, not an instruction to trade.
candidate_direction = 0
candidate_count = 0
confirmed_direction = 0
for index in range(1, n):
    if not np.isfinite(nrp[index]) or not np.isfinite(nrp[index - 1]):
        candidate_direction = 0
        candidate_count = 0
        continue
    slope = nrp[index] - nrp[index - 1]
    direction = 1 if slope >= 0.0 else -1
    if direction == candidate_direction:
        candidate_count += 1
    else:
        candidate_direction = direction
        candidate_count = 1
    if candidate_count >= confirm_bars and direction != confirmed_direction:
        if direction > 0:
            long_signal[index] = low[index] if np.isfinite(low[index]) else nrp[index]
        else:
            short_signal[index] = high[index] if np.isfinite(high[index]) else nrp[index]
        confirmed_direction = direction

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Kernel Regression Up", "data": plot_list(nrp_up), "color": bullish_color, "overlay": True, "linewidth": 3},
        {"name": "Kernel Regression Down", "data": plot_list(nrp_dn), "color": bearish_color, "overlay": True, "linewidth": 3},
        {"name": "Kernel Regression Upper", "data": plot_list(upper), "color": "#808080", "overlay": True, "linestyle": "dashed"},
        {"name": "Kernel Regression Lower", "data": plot_list(lower), "color": "#808080", "overlay": True, "linestyle": "dashed"},
    ],
    "signals": [
        {"type": "buy", "text": "MKR↥", "data": plot_list(long_signal), "color": bullish_color, "shape": "triangle", "position": "belowBar"},
        {"type": "sell", "text": "MKR↧", "data": plot_list(short_signal), "color": bearish_color, "shape": "inverted_triangle", "position": "aboveBar"},
    ],
    "layers": [],
    "metadata": {
        "causal": True,
        "repaint": False,
        "repaint_requested": repaint_requested,
        "kernel": kernel,
        "bandwidth": bandwidth,
        "source": source_name,
        "deviations": deviations,
        "enable": enable,
        "confirm_bars": confirm_bars,
        "nrp": plot_list(nrp),
        "nrp_up": plot_list(nrp_up),
        "nrp_dn": plot_list(nrp_dn),
        "nrp_std": plot_list(nrp_std),
        "upper": plot_list(upper),
        "lower": plot_list(lower),
        "est": plot_list(nrp),
        "long_signal": plot_list(long_signal),
        "short_signal": plot_list(short_signal),
    },
}
