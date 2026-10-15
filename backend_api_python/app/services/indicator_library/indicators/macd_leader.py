"""Chart-only source for the macd_leader indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] MACD Leader\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# MACD Leader uses a second EMA over each fast/slow EMA residual to reduce\n"
    "# lag. It is a pure oscillator and does not place trades.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] MACD Leader"\n'
    "my_indicator_description = (\n"
    '    "Residual-corrected MACD Leader oscillator with optional conventional MACD lines."\n'
    ")\n"
    "\n"
    "# @param short_length int 12 Fast EMA period range=1:200:1\n"
    "# @param long_length int 26 Slow EMA period range=2:500:1\n"
    "# @param sig_length int 9 Signal SMA period range=1:200:1\n"
    "# @param show_macd bool False Show conventional MACD\n"
    "# @param show_macdsignal bool False Show conventional MACD signal line\n"
    "# @param src string close Source: close, hl2, hlc3, or ohlc4\n"
    "# @param ema_seed string sma EMA seed: sma or first\n"
    "\n"
    'short_length = max(1, int(params.get("short_length", 12)))\n'
    'long_length = max(short_length + 1, int(params.get("long_length", 26)))\n'
    'sig_length = max(1, int(params.get("sig_length", 9)))\n'
    'show_macd = params.get("show_macd", False)\n'
    'show_macdsignal = params.get("show_macdsignal", False)\n'
    'src_name = str(params.get("src", "close")).strip().lower()\n'
    'ema_seed = str(params.get("ema_seed", "sma")).strip().lower()\n'
    "\n"
    "\n"
    "def as_bool(value, default=False):\n"
    "    if value is None:\n"
    "        return default\n"
    '    if str(value).strip().lower() in ("false", "0", "no", "off"):\n'
    "        return False\n"
    '    if str(value).strip().lower() in ("true", "1", "yes", "on"):\n'
    "        return True\n"
    "    return bool(value)\n"
    "\n"
    "\n"
    "show_macd = as_bool(show_macd)\n"
    "show_macdsignal = as_bool(show_macdsignal)\n"
    'if ema_seed not in ("sma", "first"):\n'
    '    raise ValueError("ema_seed must be sma or first")\n'
    "\n"
    "\n"
    "df = df.copy()\n"
    'open_price = df["open"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    'if src_name == "hl2":\n'
    "    source = ((high + low) / 2.0).to_numpy(dtype=float)\n"
    'elif src_name == "hlc3":\n'
    "    source = ((high + low + close) / 3.0).to_numpy(dtype=float)\n"
    'elif src_name == "ohlc4":\n'
    "    source = ((open_price + high + low + close) / 4.0).to_numpy(dtype=float)\n"
    "else:\n"
    "    source = close.to_numpy(dtype=float)\n"
    "\n"
    "n = len(source)\n"
    "\n"
    "\n"
    "def ema(values, period, seed_mode):\n"
    "    result = np.full(len(values), np.nan, dtype=float)\n"
    "    alpha = 2.0 / (period + 1.0)\n"
    "    finite_indexes = np.where(np.isfinite(values))[0]\n"
    "    if len(finite_indexes) == 0:\n"
    "        return result\n"
    "    start = int(finite_indexes[0])\n"
    '    if seed_mode == "first":\n'
    "        result[start] = float(values[start])\n"
    "        for i in range(start + 1, len(values)):\n"
    "            if np.isfinite(values[i]) and np.isfinite(result[i - 1]):\n"
    "                result[i] = alpha * values[i] + (1.0 - alpha) * result[i - 1]\n"
    "        return result\n"
    "\n"
    "    seed_end = start + period - 1\n"
    "    if seed_end >= len(values):\n"
    "        return result\n"
    "    seed = values[start:seed_end + 1]\n"
    "    if len(seed) != period or not np.all(np.isfinite(seed)):\n"
    "        return result\n"
    "    result[seed_end] = float(np.mean(seed))\n"
    "    for i in range(seed_end + 1, len(values)):\n"
    "        if np.isfinite(values[i]) and np.isfinite(result[i - 1]):\n"
    "            result[i] = alpha * values[i] + (1.0 - alpha) * result[i - 1]\n"
    "    return result\n"
    "\n"
    "\n"
    "def sma(values, period):\n"
    "    result = np.full(len(values), np.nan, dtype=float)\n"
    "    for i in range(period - 1, len(values)):\n"
    "        window = values[i - period + 1:i + 1]\n"
    "        if len(window) == period and np.all(np.isfinite(window)):\n"
    "            result[i] = float(np.mean(window))\n"
    "    return result\n"
    "\n"
    "\n"
    "sema = ema(source, short_length, ema_seed)\n"
    "lema = ema(source, long_length, ema_seed)\n"
    "fast_residual = source - sema\n"
    "slow_residual = source - lema\n"
    "i1 = sema + ema(fast_residual, short_length, ema_seed)\n"
    "i2 = lema + ema(slow_residual, long_length, ema_seed)\n"
    "macdl = i1 - i2\n"
    "macd = sema - lema\n"
    "signal = sma(macd, sig_length)\n"
    "\n"
    "if not show_macd:\n"
    "    macd_plot = np.full(n, np.nan, dtype=float)\n"
    "else:\n"
    "    macd_plot = macd\n"
    "if not show_macdsignal:\n"
    "    signal_plot = np.full(n, np.nan, dtype=float)\n"
    "else:\n"
    "    signal_plot = signal\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "MACD Leader", "data": plot_list(macdl), "color": "#800000", "overlay": False, "width": 2},\n'
    '        {"name": "MACD", "data": plot_list(macd_plot), "color": "#008000", "overlay": False, "width": 1},\n'
    '        {"name": "MACD Signal", "data": plot_list(signal_plot), "color": "#FF0000", "overlay": False, "width": 1},\n'
    "    ],\n"
    '    "signals": [],\n'
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "src": src_name if src_name in ("close", "hl2", "hlc3", "ohlc4") else "close",\n'
    '        "short_length": short_length,\n'
    '        "long_length": long_length,\n'
    '        "sig_length": sig_length,\n'
    '        "ema_seed": ema_seed,\n'
    '        "show_macd": show_macd,\n'
    '        "show_macdsignal": show_macdsignal,\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
