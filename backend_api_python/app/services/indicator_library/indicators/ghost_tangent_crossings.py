"""Chart-only source for the ghost_tangent_crossings indicator."""

SOURCE_CODE = (
    "# ============================================================\n"
    "# [Default] Ghost Tangent Crossings\n"
    "# --- QuantDinger chart indicator contract ---\n"
    "# ------------------------------------------------------------\n"
    "# Causal swing geometry inspired by ChartPrime's Ghost Tangent Crossings.\n"
    "# Confirmed pivots create a tangent projection and provisional swings create a\n"
    "# one-bar ghost point. Break markers are visual only and never place trades.\n"
    "# ============================================================\n"
    "\n"
    'my_indicator_name = "[Default] Ghost Tangent Crossings"\n'
    "my_indicator_description = (\n"
    '    "Causal swing tangent projections with ghost swing points and chart-only break markers."\n'
    ")\n"
    "\n"
    "# @param pivot_type string Wick Pivot source: Wick or Body\n"
    "# @param pivot_forward int 25 Right-side pivot confirmation bars range=2:100:1\n"
    "# @param show_elliptical_zig bool True Show confirmed swing points\n"
    "# @param show_ghosts bool True Show the current provisional ghost swing\n"
    "# @param show_break bool True Show tangent crossing markers\n"
    "# @param max_zig int 0 Maximum retained swing count; zero keeps all causal history range=0:100:1\n"
    "# @param equipoint_style string Directional Equipoint style: Directional, Horizontal, or None\n"
    "# @param extend_line bool False Keep the active tangent projection extended\n"
    "# @param up_color string #1bcf66 Confirmed upward swing color\n"
    "# @param down_color string #ee2d2d Confirmed downward swing color\n"
    "# @param ghost_up_color string #1bcf663a Provisional upward swing color\n"
    "# @param ghost_down_color string #ee2d2d3a Provisional downward swing color\n"
    "# @param text_color string #EEEEEE Break marker text color\n"
    "\n"
    'pivot_type = str(params.get("pivot_type", "Wick")).strip().lower()\n'
    'pivot_forward = max(2, int(params.get("pivot_forward", 25)))\n'
    'show_elliptical_zig = params.get("show_elliptical_zig", True)\n'
    'show_ghosts = params.get("show_ghosts", True)\n'
    'show_break = params.get("show_break", True)\n'
    'max_zig = max(0, int(params.get("max_zig", 0)))\n'
    'equipoint_style = str(params.get("equipoint_style", "Directional")).strip().lower()\n'
    'extend_line = params.get("extend_line", False)\n'
    'up_color = str(params.get("up_color", "#1bcf66"))\n'
    'down_color = str(params.get("down_color", "#ee2d2d"))\n'
    'ghost_up_color = str(params.get("ghost_up_color", "#1bcf663a"))\n'
    'ghost_down_color = str(params.get("ghost_down_color", "#ee2d2d3a"))\n'
    'text_color = str(params.get("text_color", "#EEEEEE"))\n'
    "\n"
    "# Accept JSON form values as well as native booleans without making truthy\n"
    '# strings such as "false" accidentally enable a layer.\n'
    "def as_bool(value, default=True):\n"
    "    if value is None:\n"
    "        return default\n"
    '    if str(value).strip().lower() in ("false", "0", "no", "off"):\n'
    "        return False\n"
    '    if str(value).strip().lower() in ("true", "1", "yes", "on"):\n'
    "        return True\n"
    "    return bool(value)\n"
    "\n"
    "show_elliptical_zig = as_bool(show_elliptical_zig)\n"
    "show_ghosts = as_bool(show_ghosts)\n"
    "show_break = as_bool(show_break)\n"
    "extend_line = as_bool(extend_line, False)\n"
    'if equipoint_style not in ("directional", "horizontal", "none"):\n'
    '    raise ValueError("equipoint_style must be Directional, Horizontal, or None")\n'
    "\n"
    "\n"
    "df = df.copy()\n"
    'open_price = df["open"].astype(float) if "open" in df else df["close"].astype(float)\n'
    'high = df["high"].astype(float)\n'
    'low = df["low"].astype(float)\n'
    'close = df["close"].astype(float)\n'
    "open_values = open_price.to_numpy(dtype=float)\n"
    "high_values = high.to_numpy(dtype=float)\n"
    "low_values = low.to_numpy(dtype=float)\n"
    "close_values = close.to_numpy(dtype=float)\n"
    "\n"
    "n = len(df)\n"
    'if pivot_type == "body":\n'
    "    high_source = np.maximum(open_values, close_values)\n"
    "    low_source = np.minimum(open_values, close_values)\n"
    "else:\n"
    "    high_source = high_values\n"
    "    low_source = low_values\n"
    "\n"
    "zigzag_up = np.full(n, np.nan, dtype=float)\n"
    "zigzag_down = np.full(n, np.nan, dtype=float)\n"
    "ghost_zigzag_up = np.full(n, np.nan, dtype=float)\n"
    "ghost_zigzag_down = np.full(n, np.nan, dtype=float)\n"
    "equipoint_up = np.full(n, np.nan, dtype=float)\n"
    "equipoint_down = np.full(n, np.nan, dtype=float)\n"
    "ghost_equipoint_up = np.full(n, np.nan, dtype=float)\n"
    "ghost_equipoint_down = np.full(n, np.nan, dtype=float)\n"
    "tangent_price = np.full(n, np.nan, dtype=float)\n"
    "tangent_slope = np.full(n, np.nan, dtype=float)\n"
    "polarity = np.zeros(n, dtype=int)\n"
    "long_signal = np.zeros(n, dtype=bool)\n"
    "short_signal = np.zeros(n, dtype=bool)\n"
    "\n"
    "# A pivot is only accepted after all right-hand confirmation bars have closed.\n"
    "# This makes the confirmed event stable when more candles are appended.\n"
    "pivots = []\n"
    "last_pivot = None\n"
    "active_slope = np.nan\n"
    "active_level = np.nan\n"
    "active_start = None\n"
    "active_polarity = 0\n"
    "previous_projected = np.nan\n"
    "previous_close = np.nan\n"
    "confirmed_segments = []\n"
    "\n"
    "\n"
    "def finite(value):\n"
    "    return np.isfinite(value)\n"
    "\n"
    "\n"
    "def ellipse_tangent(start_x, start_y, end_x, end_y):\n"
    '    """Return a midpoint tangent slope for a quarter-ellipse swing."""\n'
    "    dx = float(end_x - start_x)\n"
    "    dy = float(end_y - start_y)\n"
    "    if dx <= 0 or not finite(dx) or not finite(dy):\n"
    "        return np.nan, float(end_y)\n"
    "    # The midpoint tangent is a stable approximation of the sampled ellipse\n"
    "    # tangent and avoids writing any values to the unconfirmed historical arc.\n"
    "    slope = dy / dx\n"
    "    tangent_x = float(start_x + dx * 0.5)\n"
    "    tangent_y = float(start_y + dy * 0.5)\n"
    "    return slope, tangent_y - slope * tangent_x\n"
    "\n"
    "\n"
    "def provisional_ghost(i):\n"
    '    """Return the current unconfirmed extreme after the last confirmed pivot."""\n'
    "    if last_pivot is None or i <= last_pivot[0]:\n"
    "        return None\n"
    "    start_index, start_price, start_kind = last_pivot\n"
    "    window_high = high_source[start_index + 1:i + 1]\n"
    "    window_low = low_source[start_index + 1:i + 1]\n"
    "    if len(window_high) == 0 or len(window_low) == 0:\n"
    "        return None\n"
    '    if start_kind == "low":\n'
    "        relative = int(np.argmax(window_high))\n"
    "        end_index = start_index + 1 + relative\n"
    "        end_price = float(window_high[relative])\n"
    "        direction = 1\n"
    "    else:\n"
    "        relative = int(np.argmin(window_low))\n"
    "        end_index = start_index + 1 + relative\n"
    "        end_price = float(window_low[relative])\n"
    "        direction = -1\n"
    "    if end_index <= start_index or not finite(end_price):\n"
    "        return None\n"
    "    return end_index, end_price, direction\n"
    "\n"
    "\n"
    "def plot_list(values):\n"
    "    return [None if not finite(value) else float(value) for value in values]\n"
    "\n"
    "\n"
    "for i in range(n):\n"
    "    pivot_index = i - pivot_forward\n"
    "    new_pivot = None\n"
    "    if pivot_index >= pivot_forward:\n"
    "        pivot_high = high_source[pivot_index]\n"
    "        pivot_low = low_source[pivot_index]\n"
    "        left_high = high_source[pivot_index - pivot_forward:pivot_index]\n"
    "        right_high = high_source[pivot_index + 1:i + 1]\n"
    "        left_low = low_source[pivot_index - pivot_forward:pivot_index]\n"
    "        right_low = low_source[pivot_index + 1:i + 1]\n"
    "        if (\n"
    "            finite(pivot_high)\n"
    "            and len(left_high) == pivot_forward\n"
    "            and len(right_high) == pivot_forward\n"
    "            and np.all(np.isfinite(left_high))\n"
    "            and np.all(np.isfinite(right_high))\n"
    "            and pivot_high > np.max(left_high)\n"
    "            and pivot_high >= np.max(right_high)\n"
    "        ):\n"
    '            new_pivot = (pivot_index, float(pivot_high), "high")\n'
    "        if (\n"
    "            finite(pivot_low)\n"
    "            and len(left_low) == pivot_forward\n"
    "            and len(right_low) == pivot_forward\n"
    "            and np.all(np.isfinite(left_low))\n"
    "            and np.all(np.isfinite(right_low))\n"
    "            and pivot_low < np.min(left_low)\n"
    "            and pivot_low <= np.min(right_low)\n"
    "        ):\n"
    '            low_pivot = (pivot_index, float(pivot_low), "low")\n'
    "            # A single candle can technically satisfy both tests. Keep the\n"
    "            # more recent alternating swing and ignore same-direction noise.\n"
    '            if new_pivot is None or last_pivot is None or last_pivot[2] != "low":\n'
    "                new_pivot = low_pivot\n"
    "\n"
    "    if new_pivot is not None and (last_pivot is None or new_pivot[2] != last_pivot[2]):\n"
    "        if last_pivot is not None:\n"
    "            start_x, start_y, start_kind = last_pivot\n"
    "            end_x, end_y, end_kind = new_pivot\n"
    "            slope, intercept = ellipse_tangent(start_x, start_y, end_x, end_y)\n"
    "            if finite(slope) and finite(intercept):\n"
    "                active_slope = slope\n"
    "                active_level = intercept + slope * i\n"
    "                active_start = i\n"
    "                active_polarity = 1 if end_y > start_y else -1\n"
    "                tangent_price[i] = float(start_y + (end_y - start_y) * 0.5)\n"
    "                tangent_slope[i] = float(slope)\n"
    "                polarity[i] = active_polarity\n"
    "                confirmed_segments.append(\n"
    "                    {\n"
    '                        "start": int(start_x),\n'
    '                        "end": int(end_x),\n'
    '                        "confirmation": int(i),\n'
    '                        "direction": "up" if active_polarity > 0 else "down",\n'
    "                    }\n"
    "                )\n"
    "                # The chart renderer receives the confirmed endpoint on the\n"
    "                # confirmation bar. Backfilling the historical arc would make\n"
    "                # the output repaint when this pivot becomes known.\n"
    "                if show_elliptical_zig:\n"
    "                    if active_polarity > 0:\n"
    "                        zigzag_up[i] = float(end_y)\n"
    "                    else:\n"
    "                        zigzag_down[i] = float(end_y)\n"
    "            pivots.append(new_pivot)\n"
    "        last_pivot = new_pivot\n"
    "\n"
    "    if active_start is not None and finite(active_slope) and finite(active_level):\n"
    "        projected = active_level + active_slope * (i - active_start)\n"
    "        if active_polarity > 0:\n"
    "            polarity[i] = 1\n"
    "        elif active_polarity < 0:\n"
    "            polarity[i] = -1\n"
    '        if equipoint_style != "none":\n'
    "            if active_polarity > 0:\n"
    "                equipoint_up[i] = projected\n"
    "            else:\n"
    "                equipoint_down[i] = projected\n"
    "        tangent_price[i] = tangent_price[i] if finite(tangent_price[i]) else projected\n"
    "        tangent_slope[i] = tangent_slope[i] if finite(tangent_slope[i]) else active_slope\n"
    "\n"
    "        if show_break and finite(previous_projected) and finite(previous_close) and finite(close_values[i]):\n"
    "            crossed_up = previous_close <= previous_projected and close_values[i] > projected\n"
    "            crossed_down = previous_close >= previous_projected and close_values[i] < projected\n"
    "            if crossed_up:\n"
    "                long_signal[i] = True\n"
    "            if crossed_down:\n"
    "                short_signal[i] = True\n"
    "        previous_projected = projected\n"
    "    else:\n"
    "        previous_projected = np.nan\n"
    "\n"
    "    # Only the current bar receives ghost values. This intentionally avoids\n"
    "    # repainting earlier candles as the provisional extreme moves.\n"
    "    ghost = provisional_ghost(i)\n"
    "    if show_ghosts and ghost is not None:\n"
    "        ghost_index, ghost_price, ghost_direction = ghost\n"
    "        ghost_slope, ghost_intercept = ellipse_tangent(\n"
    "            last_pivot[0], last_pivot[1], ghost_index, ghost_price\n"
    "        )\n"
    "        if ghost_direction > 0:\n"
    "            ghost_zigzag_up[i] = ghost_price\n"
    "        else:\n"
    "            ghost_zigzag_down[i] = ghost_price\n"
    '        if finite(ghost_slope) and finite(ghost_intercept) and equipoint_style != "none":\n'
    "            ghost_value = ghost_intercept + ghost_slope * i\n"
    "            if ghost_direction > 0:\n"
    "                ghost_equipoint_up[i] = ghost_value\n"
    "            else:\n"
    "                ghost_equipoint_down[i] = ghost_value\n"
    "\n"
    "    previous_close = close_values[i] if finite(close_values[i]) else previous_close\n"
    "\n"
    "# The original implementation can remove old polylines. QuantDinger keeps\n"
    "# historical values immutable instead, so max_zig is exposed as metadata while\n"
    "# preserving causal chart history.\n"
    "if max_zig > 0:\n"
    "    confirmed_segments = confirmed_segments[-max_zig:]\n"
    "\n"
    "long_marks = [\n"
    "    float(low_values[i]) * 0.995 if long_signal[i] and finite(low_values[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "short_marks = [\n"
    "    float(high_values[i]) * 1.005 if short_signal[i] and finite(high_values[i]) else None\n"
    "    for i in range(n)\n"
    "]\n"
    "\n"
    "output = {\n"
    '    "name": my_indicator_name,\n'
    '    "plots": [\n'
    '        {"name": "Swing Up", "data": plot_list(zigzag_up), "color": up_color, "overlay": True},\n'
    '        {"name": "Swing Down", "data": plot_list(zigzag_down), "color": down_color, "overlay": True},\n'
    '        {"name": "Ghost Swing Up", "data": plot_list(ghost_zigzag_up), "color": ghost_up_color, "overlay": True, "style": "dashed"},\n'
    '        {"name": "Ghost Swing Down", "data": plot_list(ghost_zigzag_down), "color": ghost_down_color, "overlay": True, "style": "dashed"},\n'
    '        {"name": "Equipoint Up", "data": plot_list(equipoint_up), "color": up_color, "overlay": True, "style": "dashed"},\n'
    '        {"name": "Equipoint Down", "data": plot_list(equipoint_down), "color": down_color, "overlay": True, "style": "dashed"},\n'
    '        {"name": "Ghost Equipoint Up", "data": plot_list(ghost_equipoint_up), "color": ghost_up_color, "overlay": True, "style": "dashed"},\n'
    '        {"name": "Ghost Equipoint Down", "data": plot_list(ghost_equipoint_down), "color": ghost_down_color, "overlay": True, "style": "dashed"},\n'
    "    ],\n"
    '    "signals": [\n'
    '        {"type": "buy", "text": "B", "data": long_marks, "color": up_color},\n'
    '        {"type": "sell", "text": "B", "data": short_marks, "color": down_color},\n'
    "    ],\n"
    '    "metadata": {\n'
    '        "tangent_price": plot_list(tangent_price),\n'
    '        "tangent_slope": plot_list(tangent_slope),\n'
    '        "polarity": [int(value) if value else None for value in polarity],\n'
    '        "causal": True,\n'
    '        "pivot_type": "Body" if pivot_type == "body" else "Wick",\n'
    '        "pivot_forward": pivot_forward,\n'
    '        "equipoint_style": equipoint_style,\n'
    '        "extend_line": extend_line,\n'
    '        "max_zig": max_zig,\n'
    '        "text_color": text_color,\n'
    '        "confirmed_segments": confirmed_segments,\n'
    "    },\n"
    '    "layers": [],\n'
    "}\n"
)
