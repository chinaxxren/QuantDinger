"""Chart-only source for the macd_bollinger_bands indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] MACD Bollinger Bands\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Bollinger bands applied to the MACD line. All values are chart data only;\n"
    "# this indicator does not submit orders or manage trading positions.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] MACD Bollinger Bands"\n'
    "my_indicator_description = (\n"
    '    "MACD oscillator with a Bollinger envelope and optional chart-only crossover signals."\n'
    ")\n"
    "\n"
    "# @param fast_length int 12 Fast EMA period range=2:50:1\n"
    "# @param slow_length int 26 Slow EMA period range=3:100:1\n"
    "# @param signal_length int 9 MACD signal EMA period range=2:50:1\n"
    "# @param band_length int 20 Bollinger period range=2:100:1\n"
    "# @param band_multiplier float 2.0 Bollinger standard deviation multiplier range=0.5:4.0:0.1\n"
    "# @param source string close Source: close, hl2, hlc3, or ohlc4\n"
    "# @param show_bands bool True Show Bollinger bands\n"
    "# @param show_signals bool True Show MACD crossover markers\n"
    "\n"
    "\n"
    "def as_bool(value, default=False):\n"
    "    if value is None:\n"
    "        return default\n"
    "    if isinstance(value, str):\n"
    "        lowered = value.strip().lower()\n"
    '        if lowered in ("false", "0", "no", "off"):\n'
    "            return False\n"
    '        if lowered in ("true", "1", "yes", "on"):\n'
    "            return True\n"
    "    return bool(value)\n"
    "\n"
    "\n"
    'fast_length = max(2, int(params.get("fast_length", 12)))\n'
    'slow_length = max(fast_length + 1, int(params.get("slow_length", 26)))\n'
    'signal_length = max(2, int(params.get("signal_length", 9)))\n'
    'band_length = max(2, int(params.get("band_length", 20)))\n'
    'band_multiplier = max(0.1, float(params.get("band_multiplier", 2.0)))\n'
    'source_name = str(params.get("source", "close")).strip().lower()\n'
    'show_bands = as_bool(params.get("show_bands", True), True)\n'
    'show_signals = as_bool(params.get("show_signals", True), True)\n'
    "\n"
    "\n"
    "df = df.copy()\n"
    'open_price = df["open"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    'if source_name == "hl2":\n'
    "    source = (high + low) / 2.0\n"
    'elif source_name == "hlc3":\n'
    "    source = (high + low + close) / 3.0\n"
    'elif source_name == "ohlc4":\n'
    "    source = (open_price + high + low + close) / 4.0\n"
    "else:\n"
    '    source_name = "close"\n'
    "    source = close\n"
    "\n"
    "fast_ema = source.ewm(span=fast_length, adjust=False, min_periods=fast_length).mean()\n"
    "slow_ema = source.ewm(span=slow_length, adjust=False, min_periods=slow_length).mean()\n"
    "macd_line = fast_ema - slow_ema\n"
    "signal_line = macd_line.ewm(\n"
    "    span=signal_length, adjust=False, min_periods=signal_length\n"
    ").mean()\n"
    "histogram = macd_line - signal_line\n"
    "\n"
    "band_basis = macd_line.rolling(band_length, min_periods=band_length).mean()\n"
    "band_std = macd_line.rolling(band_length, min_periods=band_length).std(ddof=0)\n"
    "band_upper = band_basis + band_multiplier * band_std\n"
    "band_lower = band_basis - band_multiplier * band_std\n"
    "\n"
    "macd_values = macd_line.to_numpy(dtype=float)\n"
    "signal_values = signal_line.to_numpy(dtype=float)\n"
    "histogram_values = histogram.to_numpy(dtype=float)\n"
    "n = len(df)\n"
    "buy = np.zeros(n, dtype=bool)\n"
    "sell = np.zeros(n, dtype=bool)\n"
    "for i in range(1, n):\n"
    "    if (\n"
    "        np.isfinite(macd_values[i])\n"
    "        and np.isfinite(signal_values[i])\n"
    "        and np.isfinite(macd_values[i - 1])\n"
    "        and np.isfinite(signal_values[i - 1])\n"
    "    ):\n"
    "        buy[i] = macd_values[i] > signal_values[i] and macd_values[i - 1] <= signal_values[i - 1]\n"
    "        sell[i] = macd_values[i] < signal_values[i] and macd_values[i - 1] >= signal_values[i - 1]\n"
    "\n"
    "if not show_bands:\n"
    "    band_upper_plot = np.full(n, np.nan, dtype=float)\n"
    "    band_basis_plot = np.full(n, np.nan, dtype=float)\n"
    "    band_lower_plot = np.full(n, np.nan, dtype=float)\n"
    "else:\n"
    "    band_upper_plot = band_upper.to_numpy(dtype=float)\n"
    "    band_basis_plot = band_basis.to_numpy(dtype=float)\n"
    "    band_lower_plot = band_lower.to_numpy(dtype=float)\n"
    "\n"
    "if not show_signals:\n"
    "    buy = np.zeros(n, dtype=bool)\n"
    "    sell = np.zeros(n, dtype=bool)\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "MACD", "data": plot_list(macd_values), "color": "#2962FF", "overlay": False},\n'
    '        {"name": "Signal", "data": plot_list(signal_values), "color": "#FF6D00", "overlay": False},\n'
    '        {"name": "Histogram", "data": plot_list(histogram_values), "color": "#26A69A", "overlay": False},\n'
    '        {"name": "BB Upper", "data": plot_list(band_upper_plot), "color": "#AB47BC", "overlay": False},\n'
    '        {"name": "BB Basis", "data": plot_list(band_basis_plot), "color": "#7E57C2", "overlay": False},\n'
    '        {"name": "BB Lower", "data": plot_list(band_lower_plot), "color": "#AB47BC", "overlay": False},\n'
    "    ],\n"
    '    "signals": [\n'
    "        {\n"
    '            "type": "buy",\n'
    '            "text": "MACD Bullish Cross",\n'
    '            "data": [\n'
    "                float(macd_values[i]) if buy[i] and np.isfinite(macd_values[i]) else None\n"
    "                for i in range(n)\n"
    "            ],\n"
    '            "color": "#00C853",\n'
    "        },\n"
    "        {\n"
    '            "type": "sell",\n'
    '            "text": "MACD Bearish Cross",\n'
    '            "data": [\n'
    "                float(macd_values[i]) if sell[i] and np.isfinite(macd_values[i]) else None\n"
    "                for i in range(n)\n"
    "            ],\n"
    '            "color": "#FF5252",\n'
    "        },\n"
    "    ],\n"
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "source": source_name,\n'
    '        "fast_length": fast_length,\n'
    '        "slow_length": slow_length,\n'
    '        "signal_length": signal_length,\n'
    '        "band_length": band_length,\n'
    '        "band_multiplier": band_multiplier,\n'
    '        "show_bands": show_bands,\n'
    '        "show_signals": show_signals,\n'
    '        "macd": plot_list(macd_values),\n'
    '        "signal": plot_list(signal_values),\n'
    '        "histogram": plot_list(histogram_values),\n'
    '        "band_upper": plot_list(band_upper.to_numpy(dtype=float)),\n'
    '        "band_basis": plot_list(band_basis.to_numpy(dtype=float)),\n'
    '        "band_lower": plot_list(band_lower.to_numpy(dtype=float)),\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
