"""Chart-only source for the swing_failure_pattern indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Swing Failure Pattern\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal SFP detector inspired by Swing Failure Pattern [LuxAlgo]. A swing is\n"
    "# confirmed only after right-side bars are available; no historical values are\n"
    "# backfilled when the pivot becomes known. Signals are chart-only.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Swing Failure Pattern"\n'
    "my_indicator_description = (\n"
    '    "Causal swing-failure reversal detector with sweep and confirmation signals."\n'
    ")\n"
    "\n"
    "# @param length int 5 Swing left/right confirmation range=2:100:1\n"
    "# @param bullish bool True Detect bullish swing failures\n"
    "# @param bearish bool True Detect bearish swing failures\n"
    "# @param swing_lines bool True Show confirmed swing levels\n"
    "# @param confirm_lines bool True Show opposite confirmation levels\n"
    "# @param sfp_labels bool True Show sweep and confirmation markers\n"
    "# @param bull_color string #089981 Bullish color\n"
    "# @param bear_color string #f23645 Bearish color\n"
    "# @param validation string None Volume validation mode (recorded only)\n"
    "# @param percent float 25.0 Allowed sweep penetration percentage range=0:100:1\n"
    "\n"
    "\n"
    "def as_bool(value, default=False):\n"
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
    "    return min(maximum, max(minimum, parsed))\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not np.isfinite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    'length = clamp_int(params.get("length", 5), 5, 2, 100)\n'
    'show_bullish = as_bool(params.get("bullish", True), True)\n'
    'show_bearish = as_bool(params.get("bearish", True), True)\n'
    'show_swing_lines = as_bool(params.get("swing_lines", True), True)\n'
    'show_confirm_lines = as_bool(params.get("confirm_lines", True), True)\n'
    'show_labels = as_bool(params.get("sfp_labels", True), True)\n'
    'bull_color = str(params.get("bull_color", "#089981"))\n'
    'bear_color = str(params.get("bear_color", "#f23645"))\n'
    'validation = str(params.get("validation", "None"))\n'
    'percent = clamp_float(params.get("percent", 25.0), 25.0, 0.0, 100.0)\n'
    "\n"
    "df = df.copy()\n"
    'high = pd.to_numeric(df["high"], errors="coerce").to_numpy(dtype=float)\n'
    'low = pd.to_numeric(df["low"], errors="coerce").to_numpy(dtype=float)\n'
    'close = pd.to_numeric(df["close"], errors="coerce").to_numpy(dtype=float)\n'
    'open_price = pd.to_numeric(df["open"], errors="coerce").to_numpy(dtype=float)\n'
    "n = len(close)\n"
    "\n"
    "swing_high = np.full(n, np.nan, dtype=float)\n"
    "opposite_low = np.full(n, np.nan, dtype=float)\n"
    "swing_low = np.full(n, np.nan, dtype=float)\n"
    "opposite_high = np.full(n, np.nan, dtype=float)\n"
    "bull_sweep = np.full(n, np.nan, dtype=float)\n"
    "bear_sweep = np.full(n, np.nan, dtype=float)\n"
    "long_signal = np.full(n, np.nan, dtype=float)\n"
    "short_signal = np.full(n, np.nan, dtype=float)\n"
    "\n"
    "latest_high = None\n"
    "latest_low = None\n"
    "pending_bull = None\n"
    "pending_bear = None\n"
    "\n"
    "for i in range(n):\n"
    "    pivot_index = i - length\n"
    "    if pivot_index >= length:\n"
    "        left_high = high[pivot_index - length:pivot_index]\n"
    "        right_high = high[pivot_index + 1:i + 1]\n"
    "        left_low = low[pivot_index - length:pivot_index]\n"
    "        right_low = low[pivot_index + 1:i + 1]\n"
    "        if (\n"
    "            np.isfinite(high[pivot_index])\n"
    "            and np.all(np.isfinite(left_high))\n"
    "            and np.all(np.isfinite(right_high))\n"
    "            and high[pivot_index] > np.max(left_high)\n"
    "            and high[pivot_index] >= np.max(right_high)\n"
    "        ):\n"
    "            latest_high = {\n"
    '                "level": float(high[pivot_index]),\n'
    '                "opposite": float(low[pivot_index]),\n'
    '                "index": pivot_index,\n'
    "            }\n"
    "            pending_bear = None\n"
    "        if (\n"
    "            np.isfinite(low[pivot_index])\n"
    "            and np.all(np.isfinite(left_low))\n"
    "            and np.all(np.isfinite(right_low))\n"
    "            and low[pivot_index] < np.min(left_low)\n"
    "            and low[pivot_index] <= np.min(right_low)\n"
    "        ):\n"
    "            latest_low = {\n"
    '                "level": float(low[pivot_index]),\n'
    '                "opposite": float(high[pivot_index]),\n'
    '                "index": pivot_index,\n'
    "            }\n"
    "            pending_bull = None\n"
    "\n"
    "    # A bearish SFP sweeps a confirmed swing high, then closes back below it.\n"
    "    if show_bearish and latest_high is not None and pending_bear is None:\n"
    '        level = latest_high["level"]\n'
    '        penetration_limit = abs(level - latest_high["opposite"]) * (percent / 100.0)\n'
    "        swept = high[i] > level and high[i] <= level + penetration_limit if penetration_limit else high[i] > level\n"
    "        recovered = close[i] < level and open_price[i] <= level\n"
    "        if swept and recovered:\n"
    '            pending_bear = {"level": level, "index": i}\n'
    "            if show_labels:\n"
    "                bear_sweep[i] = high[i]\n"
    "\n"
    "    # A bullish SFP sweeps a confirmed swing low, then closes back above it.\n"
    "    if show_bullish and latest_low is not None and pending_bull is None:\n"
    '        level = latest_low["level"]\n'
    '        penetration_limit = abs(latest_low["opposite"] - level) * (percent / 100.0)\n'
    "        swept = low[i] < level and low[i] >= level - penetration_limit if penetration_limit else low[i] < level\n"
    "        recovered = close[i] > level and open_price[i] >= level\n"
    "        if swept and recovered:\n"
    '            pending_bull = {"level": level, "index": i}\n'
    "            if show_labels:\n"
    "                bull_sweep[i] = low[i]\n"
    "\n"
    "    # The next opposite-level close is the confirmation event. Keeping the\n"
    "    # pending record in local state means later bars cannot repaint the sweep.\n"
    '    if pending_bear is not None and i > pending_bear["index"]:\n'
    '        if close[i] < latest_high["opposite"]:\n'
    "            if show_labels:\n"
    "                short_signal[i] = high[i]\n"
    "            pending_bear = None\n"
    '        elif close[i] > pending_bear["level"]:\n'
    "            pending_bear = None\n"
    '    if pending_bull is not None and i > pending_bull["index"]:\n'
    '        if close[i] > latest_low["opposite"]:\n'
    "            if show_labels:\n"
    "                long_signal[i] = low[i]\n"
    "            pending_bull = None\n"
    '        elif close[i] < pending_bull["level"]:\n'
    "            pending_bull = None\n"
    "\n"
    "    if show_swing_lines:\n"
    "        if latest_high is not None:\n"
    '            swing_high[i] = latest_high["level"]\n'
    "        if latest_low is not None:\n"
    '            swing_low[i] = latest_low["level"]\n'
    "    if show_confirm_lines:\n"
    "        if latest_high is not None:\n"
    '            opposite_low[i] = latest_high["opposite"]\n'
    "        if latest_low is not None:\n"
    '            opposite_high[i] = latest_low["opposite"]\n'
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Swing High", "data": plot_list(swing_high), "color": bear_color, "overlay": True},\n'
    '        {"name": "Opposite Low", "data": plot_list(opposite_low), "color": bull_color, "overlay": True},\n'
    '        {"name": "Swing Low", "data": plot_list(swing_low), "color": bull_color, "overlay": True},\n'
    '        {"name": "Opposite High", "data": plot_list(opposite_high), "color": bear_color, "overlay": True},\n'
    '        {"name": "Bullish Sweep", "data": plot_list(bull_sweep), "color": bull_color, "overlay": True},\n'
    '        {"name": "Bearish Sweep", "data": plot_list(bear_sweep), "color": bear_color, "overlay": True},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "SFP Confirm", "data": plot_list(long_signal), "color": bull_color},\n'
    '        {"type": "sell", "text": "SFP Confirm", "data": plot_list(short_signal), "color": bear_color},\n'
    "    ],\n"
    '    "layers": [],\n'
    '    "metadata": {\n'
    '        "causal": True,\n'
    '        "length": length,\n'
    '        "validation": validation,\n'
    '        "percent": percent,\n'
    "    },\n"
    "}\n"
)
