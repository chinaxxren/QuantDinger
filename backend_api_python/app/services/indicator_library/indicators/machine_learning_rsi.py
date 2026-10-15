"""Chart-only source for the machine_learning_rsi indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Machine Learning RSI\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# K-nearest-neighbour enhanced RSI inspired by the MiniBT /\n"
    "# BullVision Machine Learning RSI. This source is a chart-only\n"
    "# indicator: signals are visual markers and never place orders.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Machine Learning RSI"\n'
    "my_indicator_description = (\n"
    '    "KNN-enhanced RSI with causal technical features and optional smoothing."\n'
    ")\n"
    "\n"
    "# @param rsi_length int 14 RSI and price-channel period range=2:100:1\n"
    "# @param use_smoothing bool True Smooth the base RSI before KNN processing\n"
    "# @param smoothing_length int 3 Base RSI smoothing period range=1:50:1\n"
    "# @param ma_type string ALMA Base RSI moving-average type: SMA, EMA, DEMA, TEMA, WMA, VWMA, SMMA, HMA, LSMA, ALMA\n"
    "# @param alma_sigma float 4 ALMA sigma range=1:10:0.5\n"
    "# @param use_knn bool True Enable KNN enhancement\n"
    "# @param knn_neighbors int 5 Number of nearest historical samples range=1:32:1\n"
    "# @param knn_lookback int 100 Historical feature search window range=20:500:10\n"
    "# @param knn_weight float 0.4 Blend weight for KNN RSI range=0:1:0.05\n"
    "# @param feature_count int 3 Number of normalized features range=1:5:1\n"
    "# @param use_filter bool True Apply a final RSI filter\n"
    "# @param filter_method string Kalman Filter: Kalman, DoubleEMA, ALMA\n"
    "# @param filter_strength float 0.3 Filter strength range=0.05:1:0.05\n"
    "# @param src string close Price source: close, hl2, hlc3, or ohlc4\n"
    "# @param overbought int 70 Overbought threshold range=50:95:1\n"
    "# @param oversold int 30 Oversold threshold range=5:50:1\n"
    "# @param color_scheme string Classic Signal color scheme\n"
    "# @param neon_effect bool True Use brighter Classic colors\n"
    "# @param color_mode string Trend Following RSI coloring: None, Trend Following, Impulse\n"
    "# @param show_table bool True Retained for compatibility; status is returned in metadata\n"
    "# @param table_position string top-left Retained for compatibility\n"
    "\n"
    "\n"
    "def _as_bool(value, default=False):\n"
    "    if value is None:\n"
    "        return default\n"
    "    if isinstance(value, str):\n"
    "        normalized = value.strip().lower()\n"
    '        if normalized in ("false", "0", "no", "off", "none", ""):\n'
    "            return False\n"
    '        if normalized in ("true", "1", "yes", "on"):\n'
    "            return True\n"
    "    return bool(value)\n"
    "\n"
    "\n"
    "def _finite(value):\n"
    "    return value is not None and np.isfinite(float(value))\n"
    "\n"
    "\n"
    "def _source_series(frame, name):\n"
    '    close_values = frame["close"].astype(float)\n'
    '    high_values = frame["high"].astype(float)\n'
    '    low_values = frame["low"].astype(float)\n'
    '    open_values = frame["open"].astype(float) if "open" in frame else close_values\n'
    '    if name == "hl2":\n'
    "        return (high_values + low_values) / 2.0\n"
    '    if name == "hlc3":\n'
    "        return (high_values + low_values + close_values) / 3.0\n"
    '    if name == "ohlc4":\n'
    "        return (open_values + high_values + low_values + close_values) / 4.0\n"
    "    return close_values\n"
    "\n"
    "\n"
    "def _ema(values, period):\n"
    "    return values.ewm(span=period, adjust=False, min_periods=period).mean()\n"
    "\n"
    "\n"
    "def _wma(values, period):\n"
    "    weights = np.arange(1, period + 1, dtype=float)\n"
    "    total = float(np.sum(weights))\n"
    "    return values.rolling(period, min_periods=period).apply(\n"
    "        lambda window: float(np.dot(window, weights) / total), raw=True\n"
    "    )\n"
    "\n"
    "\n"
    "def _vwma(values, volume, period):\n"
    "    weighted = (values * volume).rolling(period, min_periods=period).sum()\n"
    "    denominator = volume.rolling(period, min_periods=period).sum()\n"
    "    return weighted / denominator.replace(0.0, np.nan)\n"
    "\n"
    "\n"
    "def _smma(values, period):\n"
    "    return values.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()\n"
    "\n"
    "\n"
    "def _linreg(values, period):\n"
    "    x = np.arange(period, dtype=float)\n"
    "    x_mean = float(np.mean(x))\n"
    "    denominator = float(np.sum((x - x_mean) ** 2))\n"
    "\n"
    "    def fit(window):\n"
    "        y_mean = float(np.mean(window))\n"
    "        slope = float(np.sum((x - x_mean) * (window - y_mean)) / denominator)\n"
    "        return y_mean + slope * (period - 1 - x_mean)\n"
    "\n"
    "    return values.rolling(period, min_periods=period).apply(fit, raw=True)\n"
    "\n"
    "\n"
    "def _alma(values, period, sigma):\n"
    "    if period <= 1:\n"
    "        return values.copy()\n"
    "    center = 0.85 * (period - 1)\n"
    "    width = (period / sigma) ** 2\n"
    "    weights = np.exp(-((np.arange(period, dtype=float) - center) ** 2) / (2.0 * width))\n"
    "    weights = weights / float(np.sum(weights))\n"
    "    return values.rolling(period, min_periods=period).apply(\n"
    "        lambda window: float(np.dot(window, weights)), raw=True\n"
    "    )\n"
    "\n"
    "\n"
    "def _moving_average(values, period, kind, sigma, volume):\n"
    '    normalized = str(kind or "ALMA").strip().upper()\n'
    "    if period <= 1:\n"
    "        return values.copy()\n"
    '    if normalized == "SMA":\n'
    "        return values.rolling(period, min_periods=period).mean()\n"
    '    if normalized == "EMA":\n'
    "        return _ema(values, period)\n"
    '    if normalized == "DEMA":\n'
    "        first = _ema(values, period)\n"
    "        return 2.0 * first - _ema(first, period)\n"
    '    if normalized == "TEMA":\n'
    "        first = _ema(values, period)\n"
    "        second = _ema(first, period)\n"
    "        third = _ema(second, period)\n"
    "        return 3.0 * first - 3.0 * second + third\n"
    '    if normalized == "WMA":\n'
    "        return _wma(values, period)\n"
    '    if normalized == "VWMA":\n'
    "        return _vwma(values, volume, period)\n"
    '    if normalized in ("SMMA", "RMA", "WWMA"):\n'
    "        return _smma(values, period)\n"
    '    if normalized == "HMA":\n'
    "        half = max(1, period // 2)\n"
    "        root = max(1, int(np.sqrt(period)))\n"
    "        return _wma(2.0 * _wma(values, half) - _wma(values, period), root)\n"
    '    if normalized in ("LSMA", "LINREG", "LINEAR REGRESSION"):\n'
    "        return _linreg(values, period)\n"
    "    return _alma(values, period, sigma)\n"
    "\n"
    "\n"
    "def _rsi(values, period):\n"
    "    change = values.diff()\n"
    "    gain = change.clip(lower=0.0)\n"
    "    loss = (-change).clip(lower=0.0)\n"
    "    average_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()\n"
    "    average_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()\n"
    "    total = average_gain + average_loss\n"
    "    result = 100.0 * average_gain / total.replace(0.0, np.nan)\n"
    "    result = result.where(average_loss > 0.0, 100.0)\n"
    "    result = result.where(~((average_gain == 0.0) & (average_loss == 0.0)), 50.0)\n"
    "    return result.clip(0.0, 100.0)\n"
    "\n"
    "\n"
    "def _rolling_slope(values, period):\n"
    "    x = np.arange(period, dtype=float)\n"
    "    x_mean = float(np.mean(x))\n"
    "    denominator = float(np.sum((x - x_mean) ** 2))\n"
    "\n"
    "    def slope(window):\n"
    "        y_mean = float(np.mean(window))\n"
    "        return float(np.sum((x - x_mean) * (window - y_mean)) / denominator)\n"
    "\n"
    "    return values.rolling(period, min_periods=period).apply(slope, raw=True)\n"
    "\n"
    "\n"
    "def _normalize(values, period):\n"
    "    lowest = values.rolling(period, min_periods=period).min()\n"
    "    highest = values.rolling(period, min_periods=period).max()\n"
    "    width = highest - lowest\n"
    "    normalized = (values - lowest) / width.replace(0.0, np.nan)\n"
    "    return normalized.where(width != 0.0, 0.5)\n"
    "\n"
    "\n"
    "def _plot_values(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    'rsi_length = min(100, max(2, int(params.get("rsi_length", 14))))\n'
    'use_smoothing = _as_bool(params.get("use_smoothing", True), True)\n'
    'smoothing_length = min(50, max(1, int(params.get("smoothing_length", 3))))\n'
    'ma_type = str(params.get("ma_type", "ALMA"))\n'
    'alma_sigma = min(10.0, max(1.0, float(params.get("alma_sigma", 4.0))))\n'
    'use_knn = _as_bool(params.get("use_knn", True), True)\n'
    'knn_neighbors = min(32, max(1, int(params.get("knn_neighbors", 5))))\n'
    'knn_lookback = min(500, max(20, int(params.get("knn_lookback", 100))))\n'
    'knn_weight = min(1.0, max(0.0, float(params.get("knn_weight", 0.4))))\n'
    'feature_count = min(5, max(1, int(params.get("feature_count", 3))))\n'
    'use_filter = _as_bool(params.get("use_filter", True), True)\n'
    'filter_method = str(params.get("filter_method", "Kalman")).strip().lower()\n'
    'filter_strength = min(1.0, max(0.05, float(params.get("filter_strength", 0.3))))\n'
    'src_name = str(params.get("src", "close")).strip().lower()\n'
    'overbought = min(100.0, max(50.0, float(params.get("overbought", 70))))\n'
    'oversold = min(50.0, max(0.0, float(params.get("oversold", 30))))\n'
    'color_scheme = str(params.get("color_scheme", "Classic")).strip().lower()\n'
    'neon_effect = _as_bool(params.get("neon_effect", True), True)\n'
    'color_mode = str(params.get("color_mode", "Trend Following")).strip().lower()\n'
    'show_table = _as_bool(params.get("show_table", True), True)\n'
    'table_position = str(params.get("table_position", "top-left"))\n'
    "\n"
    'if filter_method not in ("kalman", "doubleema", "double ema", "alma"):\n'
    '    filter_method = "kalman"\n'
    'if color_mode not in ("none", "trend following", "impulse"):\n'
    '    color_mode = "trend following"\n'
    "\n"
    "\n"
    "df = df.copy()\n"
    "source = _source_series(df, src_name)\n"
    'volume = df["volume"].astype(float) if "volume" in df else pd.Series(1.0, index=df.index)\n'
    "base_rsi = _rsi(source, rsi_length)\n"
    "standard_rsi = (\n"
    "    _moving_average(base_rsi, smoothing_length, ma_type, alma_sigma, volume)\n"
    "    if use_smoothing\n"
    "    else base_rsi\n"
    ")\n"
    "\n"
    "# Five causal features. Every normalization window contains only the current\n"
    "# and prior bars; KNN candidates are always strictly earlier than the target.\n"
    "features = [\n"
    "    _normalize(standard_rsi, knn_lookback),\n"
    "    _normalize(source.diff(3), knn_lookback),\n"
    "    _normalize(source.pct_change(fill_method=None).rolling(10, min_periods=10).std(), knn_lookback),\n"
    "    _normalize(_rolling_slope(source, 5), knn_lookback),\n"
    "    _normalize(source.diff(5), knn_lookback),\n"
    "]\n"
    "feature_values = [series.to_numpy(dtype=float) for series in features]\n"
    "standard_values = standard_rsi.to_numpy(dtype=float)\n"
    "n = len(df)\n"
    "ml_values = np.full(n, np.nan, dtype=float)\n"
    "knn_values = np.full(n, np.nan, dtype=float)\n"
    "\n"
    "for i in range(n):\n"
    "    standard_value = standard_values[i]\n"
    "    if not np.isfinite(standard_value):\n"
    "        continue\n"
    "    estimated = float(standard_value)\n"
    "    if use_knn:\n"
    "        current_features = [feature_values[j][i] for j in range(feature_count)]\n"
    "        if all(np.isfinite(value) for value in current_features):\n"
    "            start = max(0, i - knn_lookback)\n"
    "            candidates = []\n"
    "            for candidate in range(start, i):\n"
    "                candidate_features = [feature_values[j][candidate] for j in range(feature_count)]\n"
    "                candidate_rsi = standard_values[candidate]\n"
    "                if not np.isfinite(candidate_rsi) or not all(np.isfinite(value) for value in candidate_features):\n"
    "                    continue\n"
    "                distance = float(np.sqrt(np.sum((np.asarray(current_features) - np.asarray(candidate_features)) ** 2)))\n"
    "                weight = 1.0 if distance < 1e-4 else 1.0 / distance\n"
    "                candidates.append((distance, candidate, float(candidate_rsi), weight))\n"
    "            candidates.sort(key=lambda item: (item[0], item[1]))\n"
    "            selected = candidates[:knn_neighbors]\n"
    "            weight_sum = float(np.sum([item[3] for item in selected]))\n"
    "            if selected and weight_sum > 0.0:\n"
    "                knn_value = float(np.sum([item[2] * item[3] for item in selected]) / weight_sum)\n"
    "                knn_values[i] = knn_value\n"
    "                estimated = (1.0 - knn_weight) * standard_value + knn_weight * knn_value\n"
    "    ml_values[i] = min(100.0, max(0.0, estimated))\n"
    "\n"
    "# Optional causal endpoint filtering. The Kalman variant follows the source\n"
    "# description directly; DoubleEMA and ALMA use equivalent one-sided smoothers.\n"
    "final_values = ml_values.copy()\n"
    "if use_filter:\n"
    '    if filter_method == "kalman":\n'
    "        previous = np.nan\n"
    "        for i in range(n):\n"
    "            value = ml_values[i]\n"
    "            if not np.isfinite(value):\n"
    "                continue\n"
    "            if not np.isfinite(previous):\n"
    "                previous = value\n"
    "            else:\n"
    "                previous = previous + filter_strength * (value - previous)\n"
    "            final_values[i] = previous\n"
    '    elif filter_method in ("doubleema", "double ema"):\n'
    "        alpha = filter_strength\n"
    "        first = np.full(n, np.nan, dtype=float)\n"
    "        second = np.full(n, np.nan, dtype=float)\n"
    "        for i in range(n):\n"
    "            value = ml_values[i]\n"
    "            if not np.isfinite(value):\n"
    "                continue\n"
    "            first[i] = value if i == 0 or not np.isfinite(first[i - 1]) else alpha * value + (1.0 - alpha) * first[i - 1]\n"
    "            second[i] = first[i] if i == 0 or not np.isfinite(second[i - 1]) else alpha * first[i] + (1.0 - alpha) * second[i - 1]\n"
    "        final_values = second\n"
    "    else:\n"
    "        window = max(2, int(round(2.0 + (1.0 - filter_strength) * 8.0)))\n"
    "        filtered = pd.Series(ml_values, index=df.index)\n"
    "        final_values = _alma(filtered, window, alma_sigma).to_numpy(dtype=float)\n"
    "\n"
    "final_values = np.clip(final_values, 0.0, 100.0)\n"
    "\n"
    "# Build color-segmented RSI lines. Keeping each segment in its own plot lets\n"
    "# the existing frontend render the indicator without changing its layout.\n"
    "rsi_bull = np.full(n, np.nan, dtype=float)\n"
    "rsi_bear = np.full(n, np.nan, dtype=float)\n"
    "rsi_neutral = np.full(n, np.nan, dtype=float)\n"
    "rsi_gray = np.full(n, np.nan, dtype=float)\n"
    "for i, value in enumerate(final_values):\n"
    "    if not np.isfinite(value):\n"
    "        continue\n"
    '    if color_mode == "trend following":\n'
    "        if value > 50.0:\n"
    "            rsi_bull[i] = value\n"
    "        elif value < 50.0:\n"
    "            rsi_bear[i] = value\n"
    '    elif color_mode == "impulse":\n'
    "        if value >= overbought:\n"
    "            rsi_bull[i] = value\n"
    "        elif value <= oversold:\n"
    "            rsi_bear[i] = value\n"
    "        elif 45.0 <= value <= 55.0:\n"
    "            rsi_neutral[i] = value\n"
    "        else:\n"
    "            rsi_gray[i] = value\n"
    "\n"
    "previous = np.concatenate([[np.nan], final_values[:-1]])\n"
    "long_signal = np.isfinite(final_values) & np.isfinite(previous) & (final_values > 50.0) & (previous <= 50.0)\n"
    "short_signal = np.isfinite(final_values) & np.isfinite(previous) & (final_values < 50.0) & (previous >= 50.0)\n"
    'low_values = df["low"].astype(float).to_numpy(dtype=float)\n'
    'high_values = df["high"].astype(float).to_numpy(dtype=float)\n'
    "long_marks = [float(low_values[i]) * 0.995 if long_signal[i] and np.isfinite(low_values[i]) else None for i in range(n)]\n"
    "short_marks = [float(high_values[i]) * 1.005 if short_signal[i] and np.isfinite(high_values[i]) else None for i in range(n)]\n"
    "\n"
    'if color_scheme == "deuteranopia":\n'
    '    bull_color, bear_color = "#0072B2", "#D55E00"\n'
    'elif color_scheme == "protanopia":\n'
    '    bull_color, bear_color = "#009E73", "#CC79A7"\n'
    'elif color_scheme == "tritanopia":\n'
    '    bull_color, bear_color = "#1F77B4", "#D62728"\n'
    'elif color_scheme == "monochrome":\n'
    '    bull_color, bear_color = "#E0E0E0", "#757575"\n'
    "elif neon_effect:\n"
    '    bull_color, bear_color = "#00FF88", "#FF3D81"\n'
    "else:\n"
    '    bull_color, bear_color = "#00E676", "#FF5252"\n'
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "RSI Bull", "data": _plot_values(rsi_bull), "color": bull_color, "overlay": False},\n'
    '        {"name": "RSI Bear", "data": _plot_values(rsi_bear), "color": bear_color, "overlay": False},\n'
    '        {"name": "RSI Neutral", "data": _plot_values(rsi_neutral), "color": "#FFFFFF", "overlay": False},\n'
    '        {"name": "RSI Gray", "data": _plot_values(rsi_gray), "color": "#9E9E9E", "overlay": False},\n'
    '        {"name": "Midline", "data": [50.0] * n, "color": "#9E9E9E", "overlay": False, "style": "dashed"},\n'
    '        {"name": "Upper", "data": [overbought] * n, "color": "#9E9E9E", "overlay": False},\n'
    '        {"name": "Lower", "data": [oversold] * n, "color": "#9E9E9E", "overlay": False},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "MLRSI+", "data": long_marks, "color": bull_color},\n'
    '        {"type": "sell", "text": "MLRSI-", "data": short_marks, "color": bear_color},\n'
    "    ],\n"
    '    "layers": [],\n'
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "rsi": _plot_values(final_values),\n'
    '        "knn_rsi": _plot_values(knn_values),\n'
    '        "color_mode": color_mode,\n'
    '        "color_scheme": color_scheme,\n'
    '        "overbought": overbought,\n'
    '        "oversold": oversold,\n'
    '        "use_knn": use_knn,\n'
    '        "use_filter": use_filter,\n'
    '        "filter_method": filter_method,\n'
    '        "show_table": show_table,\n'
    '        "table_position": table_position,\n'
    "    },\n"
    "}\n"
)
