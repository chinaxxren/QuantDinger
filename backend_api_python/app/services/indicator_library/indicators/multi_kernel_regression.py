"""Chart-only source for the multi_kernel_regression indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Multi Kernel Regression [ChartPrime]\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal Nadaraya-Watson kernel regression. The source indicator has a\n"
    "# repainting mode, but this library implementation intentionally uses only the\n"
    "# trailing window at each bar so historical values never change.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Multi Kernel Regression [ChartPrime]"\n'
    "my_indicator_description = (\n"
    '    "Causal multi-kernel regression with optional deviation bands and confirmed "\n'
    '    "chart-only direction signals."\n'
    ")\n"
    "\n"
    "# @param repaint bool True Compatibility switch; the chart implementation remains non-repainting\n"
    "# @param kernel string Laplace Kernel type: Triangular, Gaussian, Epanechnikov, Logistic, Log Logistic, Cosine, Sinc, Laplace, Quartic, Parabolic, Exponential, Silverman, Cauchy, Tent, Wave, Power, or Morters\n"
    "# @param bandwidth int 14 Kernel lookback range=2:200:1\n"
    "# @param source string close Price source: close, hl2, hlc3, or ohlc4\n"
    "# @param deviations float 2.0 Deviation-band multiplier range=0.0:10.0:0.25\n"
    "# @param enable bool False Show deviation bands\n"
    "# @param bullish_color string #54C294 Rising regression color\n"
    "# @param bearish_color string #EB3939 Falling regression color\n"
    "# @param confirm_bars int 10 Consecutive direction bars required for a reversal range=1:100:1\n"
    "\n"
    "\n"
    "def as_bool(value, default):\n"
    "    if value is None:\n"
    "        return default\n"
    "    text = str(value).strip().lower()\n"
    '    if text in ("false", "0", "no", "off"):\n'
    "        return False\n"
    '    if text in ("true", "1", "yes", "on"):\n'
    "        return True\n"
    "    return bool(value)\n"
    "\n"
    "\n"
    "def clamp_int(value, default, minimum, maximum):\n"
    "    try:\n"
    "        parsed = int(value)\n"
    "    except (TypeError, ValueError):\n"
    "        parsed = default\n"
    "    return min(maximum, max(minimum, parsed))\n"
    "\n"
    "\n"
    "def clamp_float(value, default, minimum, maximum):\n"
    "    try:\n"
    "        parsed = float(value)\n"
    "    except (TypeError, ValueError):\n"
    "        parsed = default\n"
    "    if not np.isfinite(parsed):\n"
    "        parsed = default\n"
    "    return min(maximum, max(minimum, parsed))\n"
    "\n"
    "\n"
    "def kernel_weight(squared_distance, kind):\n"
    '    """Return a normalized non-negative kernel weight for a unit bandwidth."""\n'
    "    radius = float(np.sqrt(max(0.0, squared_distance)))\n"
    '    name = str(kind).strip().lower().replace("-", " ").replace("_", " ")\n'
    '    name = " ".join(name.split())\n'
    "    bounded = radius <= 1.0\n"
    "\n"
    '    if name == "triangular":\n'
    "        value = 1.0 - radius if bounded else 0.0\n"
    '    elif name == "gaussian":\n'
    "        value = float(np.exp(-0.5 * radius * radius))\n"
    '    elif name == "epanechnikov":\n'
    "        value = 0.75 * (1.0 - radius * radius) if bounded else 0.0\n"
    '    elif name == "logistic":\n'
    "        # Symmetric logistic density. The constant is immaterial after\n"
    "        # normalization, but retaining it keeps the kernel well scaled.\n"
    "        value = 1.0 / (2.0 + float(np.exp(radius)) + float(np.exp(-radius)))\n"
    '    elif name == "log logistic":\n'
    "        value = 1.0 / (1.0 + float(np.exp(radius)))\n"
    '    elif name == "cosine":\n'
    "        value = (np.pi / 4.0) * float(np.cos(np.pi * radius / 2.0)) if bounded else 0.0\n"
    '    elif name == "sinc":\n'
    "        value = 1.0 if radius == 0.0 else float(np.sin(np.pi * radius) / (np.pi * radius))\n"
    '    elif name == "laplace":\n'
    "        value = 0.5 * float(np.exp(-radius))\n"
    '    elif name == "quartic":\n'
    "        value = (15.0 / 16.0) * (1.0 - radius * radius) ** 2 if bounded else 0.0\n"
    '    elif name == "parabolic":\n'
    "        value = 0.75 * (1.0 - radius * radius) if bounded else 0.0\n"
    '    elif name == "exponential":\n'
    "        value = 0.5 * float(np.exp(-radius))\n"
    '    elif name == "silverman":\n'
    "        value = (\n"
    "            1.0 / (2.0 * float(np.sqrt(2.0)))\n"
    "        ) * float(np.exp(-radius / float(np.sqrt(2.0)))) * float(\n"
    "            np.sin(radius / float(np.sqrt(2.0)) + np.pi / 4.0)\n"
    "        )\n"
    '    elif name == "cauchy":\n'
    "        value = 1.0 / (np.pi * (1.0 + radius * radius))\n"
    '    elif name == "tent":\n'
    "        value = 1.0 - radius if bounded else 0.0\n"
    '    elif name == "wave":\n'
    "        value = (1.0 - radius) * float(np.cos(np.pi * radius)) if bounded else 0.0\n"
    '    elif name == "power":\n'
    "        value = (1.0 - radius ** 3) if bounded else 0.0\n"
    '    elif name == "morters":\n'
    "        value = (1.0 - radius * radius) ** 2 if bounded else 0.0\n"
    "    else:\n"
    "        value = 0.5 * float(np.exp(-radius))\n"
    "\n"
    "    if not np.isfinite(value):\n"
    "        return 0.0\n"
    "    # Oscillatory kernels can become negative near their boundary. Clipping\n"
    "    # protects the regression denominator while preserving their shape.\n"
    "    return max(0.0, float(value))\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    'repaint_requested = as_bool(params.get("repaint", True), True)\n'
    'kernel = str(params.get("kernel", "Laplace")).strip()\n'
    'bandwidth = clamp_int(params.get("bandwidth", 14), 14, 2, 200)\n'
    'source_name = str(params.get("source", "close")).strip().lower()\n'
    'deviations = clamp_float(params.get("deviations", 2.0), 2.0, 0.0, 10.0)\n'
    'enable = as_bool(params.get("enable", False), False)\n'
    'bullish_color = str(params.get("bullish_color", "#54C294"))\n'
    'bearish_color = str(params.get("bearish_color", "#EB3939"))\n'
    'confirm_bars = clamp_int(params.get("confirm_bars", 10), 10, 1, 100)\n'
    "\n"
    "\n"
    "df = df.copy()\n"
    'close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)\n'
    'high = pd.to_numeric(df["high"], errors="coerce").to_numpy(dtype=float)\n'
    'low = pd.to_numeric(df["low"], errors="coerce").to_numpy(dtype=float)\n'
    "open_values = (\n"
    '    pd.to_numeric(df["open"], errors="coerce").to_numpy(dtype=float)\n'
    '    if "open" in df\n'
    "    else close.copy()\n"
    ")\n"
    "\n"
    'if source_name == "hl2":\n'
    "    source = (high + low) / 2.0\n"
    'elif source_name == "hlc3":\n'
    "    source = (high + low + close) / 3.0\n"
    'elif source_name == "ohlc4":\n'
    "    source = (open_values + high + low + close) / 4.0\n"
    "else:\n"
    '    source_name = "close"\n'
    "    source = close.copy()\n"
    "\n"
    "n = len(source)\n"
    "nrp = np.full(n, np.nan, dtype=float)\n"
    "nrp_std = np.full(n, np.nan, dtype=float)\n"
    "weights = np.asarray(\n"
    "    [kernel_weight((age * age) / float(bandwidth * bandwidth), kernel) for age in range(bandwidth)],\n"
    "    dtype=float,\n"
    ")\n"
    "\n"
    "# The current candle is age zero and the oldest candle is age bandwidth - 1.\n"
    "# This is the non-repainting branch: every endpoint is calculated once from a\n"
    "# fixed trailing window and is independent of candles that arrive later.\n"
    "for index in range(bandwidth - 1, n):\n"
    "    window = source[index - bandwidth + 1:index + 1]\n"
    "    if not np.isfinite(window).all():\n"
    "        continue\n"
    "    weight_sum = float(np.sum(weights))\n"
    "    if weight_sum <= 0.0:\n"
    "        continue\n"
    "    nrp[index] = float(np.dot(window[::-1], weights) / weight_sum)\n"
    "    errors = window - nrp[index]\n"
    "    nrp_std[index] = float(np.sqrt(np.sum(errors * errors) / max(1, bandwidth - 1)))\n"
    "\n"
    "nrp_up = np.full(n, np.nan, dtype=float)\n"
    "nrp_dn = np.full(n, np.nan, dtype=float)\n"
    "upper = np.full(n, np.nan, dtype=float)\n"
    "lower = np.full(n, np.nan, dtype=float)\n"
    "long_signal = np.full(n, np.nan, dtype=float)\n"
    "short_signal = np.full(n, np.nan, dtype=float)\n"
    "\n"
    "# Split the regression into two same-valued lines so the renderer can preserve\n"
    "# the source indicator's bullish/bearish line colors without changing layout.\n"
    "for index in range(n):\n"
    "    if not np.isfinite(nrp[index]):\n"
    "        continue\n"
    "    if enable and np.isfinite(nrp_std[index]):\n"
    "        upper[index] = nrp[index] + deviations * nrp_std[index]\n"
    "        lower[index] = nrp[index] - deviations * nrp_std[index]\n"
    "    if index == 0 or not np.isfinite(nrp[index - 1]):\n"
    "        nrp_up[index] = nrp[index]\n"
    "    elif nrp[index] >= nrp[index - 1]:\n"
    "        nrp_up[index] = nrp[index]\n"
    "    else:\n"
    "        nrp_dn[index] = nrp[index]\n"
    "\n"
    "# Confirm a direction only after it has held for confirm_bars consecutive\n"
    "# valid slopes. A signal is a chart marker, not an instruction to trade.\n"
    "candidate_direction = 0\n"
    "candidate_count = 0\n"
    "confirmed_direction = 0\n"
    "for index in range(1, n):\n"
    "    if not np.isfinite(nrp[index]) or not np.isfinite(nrp[index - 1]):\n"
    "        candidate_direction = 0\n"
    "        candidate_count = 0\n"
    "        continue\n"
    "    slope = nrp[index] - nrp[index - 1]\n"
    "    direction = 1 if slope >= 0.0 else -1\n"
    "    if direction == candidate_direction:\n"
    "        candidate_count += 1\n"
    "    else:\n"
    "        candidate_direction = direction\n"
    "        candidate_count = 1\n"
    "    if candidate_count >= confirm_bars and direction != confirmed_direction:\n"
    "        if direction > 0:\n"
    "            long_signal[index] = low[index] if np.isfinite(low[index]) else nrp[index]\n"
    "        else:\n"
    "            short_signal[index] = high[index] if np.isfinite(high[index]) else nrp[index]\n"
    "        confirmed_direction = direction\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Kernel Regression Up", "data": plot_list(nrp_up), "color": bullish_color, "overlay": True, "linewidth": 3},\n'
    '        {"name": "Kernel Regression Down", "data": plot_list(nrp_dn), "color": bearish_color, "overlay": True, "linewidth": 3},\n'
    '        {"name": "Kernel Regression Upper", "data": plot_list(upper), "color": "#808080", "overlay": True, "linestyle": "dashed"},\n'
    '        {"name": "Kernel Regression Lower", "data": plot_list(lower), "color": "#808080", "overlay": True, "linestyle": "dashed"},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "MKR↥", "data": plot_list(long_signal), "color": bullish_color, "shape": "triangle", "position": "belowBar"},\n'
    '        {"type": "sell", "text": "MKR↧", "data": plot_list(short_signal), "color": bearish_color, "shape": "inverted_triangle", "position": "aboveBar"},\n'
    "    ],\n"
    '    "layers": [],\n'
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "repaint": False,\n'
    '        "repaint_requested": repaint_requested,\n'
    '        "kernel": kernel,\n'
    '        "bandwidth": bandwidth,\n'
    '        "source": source_name,\n'
    '        "deviations": deviations,\n'
    '        "enable": enable,\n'
    '        "confirm_bars": confirm_bars,\n'
    '        "nrp": plot_list(nrp),\n'
    '        "nrp_up": plot_list(nrp_up),\n'
    '        "nrp_dn": plot_list(nrp_dn),\n'
    '        "nrp_std": plot_list(nrp_std),\n'
    '        "upper": plot_list(upper),\n'
    '        "lower": plot_list(lower),\n'
    '        "est": plot_list(nrp),\n'
    '        "long_signal": plot_list(long_signal),\n'
    '        "short_signal": plot_list(short_signal),\n'
    "    },\n"
    "}\n"
)
