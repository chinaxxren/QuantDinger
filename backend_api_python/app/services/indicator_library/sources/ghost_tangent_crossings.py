# ============================================================
# [Default] Ghost Tangent Crossings
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal swing geometry inspired by ChartPrime's Ghost Tangent Crossings.
# Confirmed pivots create a tangent projection and provisional swings create a
# one-bar ghost point. Break markers are visual only and never place trades.
# ============================================================

my_indicator_name = "[Default] Ghost Tangent Crossings"
my_indicator_description = (
    "Causal swing tangent projections with ghost swing points and chart-only break markers."
)

# @param pivot_type string Wick Pivot source: Wick or Body
# @param pivot_forward int 25 Right-side pivot confirmation bars range=2:100:1
# @param show_elliptical_zig bool True Show confirmed swing points
# @param show_ghosts bool True Show the current provisional ghost swing
# @param show_break bool True Show tangent crossing markers
# @param max_zig int 0 Maximum retained swing count; zero keeps all causal history range=0:100:1
# @param equipoint_style string Directional Equipoint style: Directional, Horizontal, or None
# @param extend_line bool False Keep the active tangent projection extended
# @param up_color string #1bcf66 Confirmed upward swing color
# @param down_color string #ee2d2d Confirmed downward swing color
# @param ghost_up_color string #1bcf663a Provisional upward swing color
# @param ghost_down_color string #ee2d2d3a Provisional downward swing color
# @param text_color string #EEEEEE Break marker text color

pivot_type = str(params.get("pivot_type", "Wick")).strip().lower()
pivot_forward = max(2, int(params.get("pivot_forward", 25)))
show_elliptical_zig = params.get("show_elliptical_zig", True)
show_ghosts = params.get("show_ghosts", True)
show_break = params.get("show_break", True)
max_zig = max(0, int(params.get("max_zig", 0)))
equipoint_style = str(params.get("equipoint_style", "Directional")).strip().lower()
extend_line = params.get("extend_line", False)
up_color = str(params.get("up_color", "#1bcf66"))
down_color = str(params.get("down_color", "#ee2d2d"))
ghost_up_color = str(params.get("ghost_up_color", "#1bcf663a"))
ghost_down_color = str(params.get("ghost_down_color", "#ee2d2d3a"))
text_color = str(params.get("text_color", "#EEEEEE"))

# Accept JSON form values as well as native booleans without making truthy
# strings such as "false" accidentally enable a layer.
def as_bool(value, default=True):
    if value is None:
        return default
    if str(value).strip().lower() in ("false", "0", "no", "off"):
        return False
    if str(value).strip().lower() in ("true", "1", "yes", "on"):
        return True
    return bool(value)

show_elliptical_zig = as_bool(show_elliptical_zig)
show_ghosts = as_bool(show_ghosts)
show_break = as_bool(show_break)
extend_line = as_bool(extend_line, False)
if equipoint_style not in ("directional", "horizontal", "none"):
    raise ValueError("equipoint_style must be Directional, Horizontal, or None")


df = df.copy()
open_price = df["open"].astype(float) if "open" in df else df["close"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
open_values = open_price.to_numpy(dtype=float)
high_values = high.to_numpy(dtype=float)
low_values = low.to_numpy(dtype=float)
close_values = close.to_numpy(dtype=float)

n = len(df)
if pivot_type == "body":
    high_source = np.maximum(open_values, close_values)
    low_source = np.minimum(open_values, close_values)
else:
    high_source = high_values
    low_source = low_values

zigzag_up = np.full(n, np.nan, dtype=float)
zigzag_down = np.full(n, np.nan, dtype=float)
ghost_zigzag_up = np.full(n, np.nan, dtype=float)
ghost_zigzag_down = np.full(n, np.nan, dtype=float)
equipoint_up = np.full(n, np.nan, dtype=float)
equipoint_down = np.full(n, np.nan, dtype=float)
ghost_equipoint_up = np.full(n, np.nan, dtype=float)
ghost_equipoint_down = np.full(n, np.nan, dtype=float)
tangent_price = np.full(n, np.nan, dtype=float)
tangent_slope = np.full(n, np.nan, dtype=float)
polarity = np.zeros(n, dtype=int)
long_signal = np.zeros(n, dtype=bool)
short_signal = np.zeros(n, dtype=bool)

# A pivot is only accepted after all right-hand confirmation bars have closed.
# This makes the confirmed event stable when more candles are appended.
pivots = []
last_pivot = None
active_slope = np.nan
active_level = np.nan
active_start = None
active_polarity = 0
previous_projected = np.nan
previous_close = np.nan
confirmed_segments = []


def finite(value):
    return np.isfinite(value)


def ellipse_tangent(start_x, start_y, end_x, end_y):
    """Return a midpoint tangent slope for a quarter-ellipse swing."""
    dx = float(end_x - start_x)
    dy = float(end_y - start_y)
    if dx <= 0 or not finite(dx) or not finite(dy):
        return np.nan, float(end_y)
    # The midpoint tangent is a stable approximation of the sampled ellipse
    # tangent and avoids writing any values to the unconfirmed historical arc.
    slope = dy / dx
    tangent_x = float(start_x + dx * 0.5)
    tangent_y = float(start_y + dy * 0.5)
    return slope, tangent_y - slope * tangent_x


def provisional_ghost(i):
    """Return the current unconfirmed extreme after the last confirmed pivot."""
    if last_pivot is None or i <= last_pivot[0]:
        return None
    start_index, start_price, start_kind = last_pivot
    window_high = high_source[start_index + 1:i + 1]
    window_low = low_source[start_index + 1:i + 1]
    if len(window_high) == 0 or len(window_low) == 0:
        return None
    if start_kind == "low":
        relative = int(np.argmax(window_high))
        end_index = start_index + 1 + relative
        end_price = float(window_high[relative])
        direction = 1
    else:
        relative = int(np.argmin(window_low))
        end_index = start_index + 1 + relative
        end_price = float(window_low[relative])
        direction = -1
    if end_index <= start_index or not finite(end_price):
        return None
    return end_index, end_price, direction


def plot_list(values):
    return [None if not finite(value) else float(value) for value in values]


for i in range(n):
    pivot_index = i - pivot_forward
    new_pivot = None
    if pivot_index >= pivot_forward:
        pivot_high = high_source[pivot_index]
        pivot_low = low_source[pivot_index]
        left_high = high_source[pivot_index - pivot_forward:pivot_index]
        right_high = high_source[pivot_index + 1:i + 1]
        left_low = low_source[pivot_index - pivot_forward:pivot_index]
        right_low = low_source[pivot_index + 1:i + 1]
        if (
            finite(pivot_high)
            and len(left_high) == pivot_forward
            and len(right_high) == pivot_forward
            and np.all(np.isfinite(left_high))
            and np.all(np.isfinite(right_high))
            and pivot_high > np.max(left_high)
            and pivot_high >= np.max(right_high)
        ):
            new_pivot = (pivot_index, float(pivot_high), "high")
        if (
            finite(pivot_low)
            and len(left_low) == pivot_forward
            and len(right_low) == pivot_forward
            and np.all(np.isfinite(left_low))
            and np.all(np.isfinite(right_low))
            and pivot_low < np.min(left_low)
            and pivot_low <= np.min(right_low)
        ):
            low_pivot = (pivot_index, float(pivot_low), "low")
            # A single candle can technically satisfy both tests. Keep the
            # more recent alternating swing and ignore same-direction noise.
            if new_pivot is None or last_pivot is None or last_pivot[2] != "low":
                new_pivot = low_pivot

    if new_pivot is not None and (last_pivot is None or new_pivot[2] != last_pivot[2]):
        if last_pivot is not None:
            start_x, start_y, start_kind = last_pivot
            end_x, end_y, end_kind = new_pivot
            slope, intercept = ellipse_tangent(start_x, start_y, end_x, end_y)
            if finite(slope) and finite(intercept):
                active_slope = slope
                active_level = intercept + slope * i
                active_start = i
                active_polarity = 1 if end_y > start_y else -1
                tangent_price[i] = float(start_y + (end_y - start_y) * 0.5)
                tangent_slope[i] = float(slope)
                polarity[i] = active_polarity
                confirmed_segments.append(
                    {
                        "start": int(start_x),
                        "end": int(end_x),
                        "confirmation": int(i),
                        "direction": "up" if active_polarity > 0 else "down",
                    }
                )
                # The chart renderer receives the confirmed endpoint on the
                # confirmation bar. Backfilling the historical arc would make
                # the output repaint when this pivot becomes known.
                if show_elliptical_zig:
                    if active_polarity > 0:
                        zigzag_up[i] = float(end_y)
                    else:
                        zigzag_down[i] = float(end_y)
            pivots.append(new_pivot)
        last_pivot = new_pivot

    if active_start is not None and finite(active_slope) and finite(active_level):
        projected = active_level + active_slope * (i - active_start)
        if active_polarity > 0:
            polarity[i] = 1
        elif active_polarity < 0:
            polarity[i] = -1
        if equipoint_style != "none":
            if active_polarity > 0:
                equipoint_up[i] = projected
            else:
                equipoint_down[i] = projected
        tangent_price[i] = tangent_price[i] if finite(tangent_price[i]) else projected
        tangent_slope[i] = tangent_slope[i] if finite(tangent_slope[i]) else active_slope

        if show_break and finite(previous_projected) and finite(previous_close) and finite(close_values[i]):
            crossed_up = previous_close <= previous_projected and close_values[i] > projected
            crossed_down = previous_close >= previous_projected and close_values[i] < projected
            if crossed_up:
                long_signal[i] = True
            if crossed_down:
                short_signal[i] = True
        previous_projected = projected
    else:
        previous_projected = np.nan

    # Only the current bar receives ghost values. This intentionally avoids
    # repainting earlier candles as the provisional extreme moves.
    ghost = provisional_ghost(i)
    if show_ghosts and ghost is not None:
        ghost_index, ghost_price, ghost_direction = ghost
        ghost_slope, ghost_intercept = ellipse_tangent(
            last_pivot[0], last_pivot[1], ghost_index, ghost_price
        )
        if ghost_direction > 0:
            ghost_zigzag_up[i] = ghost_price
        else:
            ghost_zigzag_down[i] = ghost_price
        if finite(ghost_slope) and finite(ghost_intercept) and equipoint_style != "none":
            ghost_value = ghost_intercept + ghost_slope * i
            if ghost_direction > 0:
                ghost_equipoint_up[i] = ghost_value
            else:
                ghost_equipoint_down[i] = ghost_value

    previous_close = close_values[i] if finite(close_values[i]) else previous_close

# The original implementation can remove old polylines. QuantDinger keeps
# historical values immutable instead, so max_zig is exposed as metadata while
# preserving causal chart history.
if max_zig > 0:
    confirmed_segments = confirmed_segments[-max_zig:]

long_marks = [
    float(low_values[i]) * 0.995 if long_signal[i] and finite(low_values[i]) else None
    for i in range(n)
]
short_marks = [
    float(high_values[i]) * 1.005 if short_signal[i] and finite(high_values[i]) else None
    for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Swing Up", "data": plot_list(zigzag_up), "color": up_color, "overlay": True},
        {"name": "Swing Down", "data": plot_list(zigzag_down), "color": down_color, "overlay": True},
        {"name": "Ghost Swing Up", "data": plot_list(ghost_zigzag_up), "color": ghost_up_color, "overlay": True, "style": "dashed"},
        {"name": "Ghost Swing Down", "data": plot_list(ghost_zigzag_down), "color": ghost_down_color, "overlay": True, "style": "dashed"},
        {"name": "Equipoint Up", "data": plot_list(equipoint_up), "color": up_color, "overlay": True, "style": "dashed"},
        {"name": "Equipoint Down", "data": plot_list(equipoint_down), "color": down_color, "overlay": True, "style": "dashed"},
        {"name": "Ghost Equipoint Up", "data": plot_list(ghost_equipoint_up), "color": ghost_up_color, "overlay": True, "style": "dashed"},
        {"name": "Ghost Equipoint Down", "data": plot_list(ghost_equipoint_down), "color": ghost_down_color, "overlay": True, "style": "dashed"},
    ],
    "signals": [
        {"type": "buy", "text": "B", "data": long_marks, "color": up_color},
        {"type": "sell", "text": "B", "data": short_marks, "color": down_color},
    ],
    "metadata": {
        "tangent_price": plot_list(tangent_price),
        "tangent_slope": plot_list(tangent_slope),
        "polarity": [int(value) if value else None for value in polarity],
        "causal": True,
        "pivot_type": "Body" if pivot_type == "body" else "Wick",
        "pivot_forward": pivot_forward,
        "equipoint_style": equipoint_style,
        "extend_line": extend_line,
        "max_zig": max_zig,
        "text_color": text_color,
        "confirmed_segments": confirmed_segments,
    },
    "layers": [],
}
