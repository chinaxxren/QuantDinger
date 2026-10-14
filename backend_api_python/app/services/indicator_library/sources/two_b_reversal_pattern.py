# ============================================================
# [Default] 2B Reversal Pattern (Expo)
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# A causal two-stage reversal detector: price first breaks a confirmed swing,
# then reverses through the breakout candle's opposite extreme. Signals are
# visual only and never place trades.
# ============================================================

my_indicator_name = "[Default] 2B Reversal Pattern (Expo)"
my_indicator_description = (
    "Confirmed swing false-break reversals with causal pending levels and chart-only signals."
)

# @param prd int 20 Swing pivot period range=2:100:1
# @param max_break int 10 Maximum confirmation window; zero means unlimited range=0:200:1
# @param min_break int 3 Minimum bars before reversal confirmation range=1:100:1
# @param setup_src string close Source for the first breakout: close or wick
# @param confirm_src string close Source for the reversal confirmation: close or wick
# @param cancel_on_invalid_cross bool True Cancel a pending setup after its window expires
# @param allow_multiple bool False Keep multiple pending setups
# @param signal_mode string Custom Preset: Custom, Original, Relaxed, or Aggressive
# @param bUp string #6ce5a0 Upward 2B line color
# @param bDn string #f23645 Downward 2B line color
# @param pCol string #00FFFF Swing and pending level color

prd = max(2, int(params.get("prd", 20)))
max_break = max(0, int(params.get("max_break", 10)))
min_break = max(1, int(params.get("min_break", 3)))
setup_src = str(params.get("setup_src", "close")).strip().lower()
confirm_src = str(params.get("confirm_src", "close")).strip().lower()
cancel_on_invalid_cross = params.get("cancel_on_invalid_cross", True)
allow_multiple = params.get("allow_multiple", False)
signal_mode = str(params.get("signal_mode", "Custom")).strip().lower()
b_up = str(params.get("bUp", "#6ce5a0"))
b_down = str(params.get("bDn", "#f23645"))
pivot_color = str(params.get("pCol", "#00FFFF"))


def as_bool(value, default=True):
    if value is None:
        return default
    if str(value).strip().lower() in ("false", "0", "no", "off"):
        return False
    if str(value).strip().lower() in ("true", "1", "yes", "on"):
        return True
    return bool(value)


cancel_on_invalid_cross = as_bool(cancel_on_invalid_cross)
allow_multiple = as_bool(allow_multiple, False)
if signal_mode == "original":
    min_break, max_break = 3, 10
    setup_src, confirm_src = "close", "close"
    cancel_on_invalid_cross, allow_multiple = True, False
elif signal_mode == "relaxed":
    min_break, max_break = 1, 30
    setup_src, confirm_src = "close", "close"
    cancel_on_invalid_cross, allow_multiple = True, False
elif signal_mode == "aggressive":
    min_break, max_break = 1, 0
    setup_src, confirm_src = "wick", "wick"
    cancel_on_invalid_cross, allow_multiple = False, True
elif signal_mode != "custom":
    raise ValueError("signal_mode must be Custom, Original, Relaxed, or Aggressive")

if setup_src not in ("close", "wick"):
    raise ValueError("setup_src must be close or wick")
if confirm_src not in ("close", "wick"):
    raise ValueError("confirm_src must be close or wick")


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

ph_level = np.full(n, np.nan, dtype=float)
pl_level = np.full(n, np.nan, dtype=float)
bo_pending = np.full(n, np.nan, dtype=float)
bo_break_up = np.full(n, np.nan, dtype=float)
bo_break_down = np.full(n, np.nan, dtype=float)
long_signal = np.zeros(n, dtype=bool)
short_signal = np.zeros(n, dtype=bool)


def finite(value):
    return np.isfinite(value)


def plot_list(values):
    return [None if not finite(value) else float(value) for value in values]


def crossed_up(source_now, source_before, level):
    return (
        finite(source_now)
        and finite(source_before)
        and finite(level)
        and source_before <= level
        and source_now > level
    )


def crossed_down(source_now, source_before, level):
    return (
        finite(source_now)
        and finite(source_before)
        and finite(level)
        and source_before >= level
        and source_now < level
    )


# Each pending entry describes the first break. kind="high" means price broke
# a swing high and must later fall through the breakout candle low; kind="low"
# is the symmetric bullish false break.
pending = []
last_ph = np.nan
last_pl = np.nan
last_setup_up = np.nan
last_setup_down = np.nan
last_confirm_up = np.nan
last_confirm_down = np.nan

for i in range(n):
    pivot_index = i - prd
    if pivot_index >= prd:
        pivot_high = high_values[pivot_index]
        pivot_low = low_values[pivot_index]
        left_high = high_values[pivot_index - prd:pivot_index]
        right_high = high_values[pivot_index + 1:i + 1]
        left_low = low_values[pivot_index - prd:pivot_index]
        right_low = low_values[pivot_index + 1:i + 1]
        if (
            finite(pivot_high)
            and len(left_high) == prd
            and len(right_high) == prd
            and np.all(np.isfinite(left_high))
            and np.all(np.isfinite(right_high))
            and pivot_high > np.max(left_high)
            and pivot_high > np.max(right_high)
        ):
            last_ph = float(pivot_high)
        if (
            finite(pivot_low)
            and len(left_low) == prd
            and len(right_low) == prd
            and np.all(np.isfinite(left_low))
            and np.all(np.isfinite(right_low))
            and pivot_low < np.min(left_low)
            and pivot_low < np.min(right_low)
        ):
            last_pl = float(pivot_low)

    ph_level[i] = last_ph if finite(last_ph) else np.nan
    pl_level[i] = last_pl if finite(last_pl) else np.nan

    if setup_src == "wick":
        setup_up_now, setup_up_before = high_values[i], last_setup_up
        setup_down_now, setup_down_before = low_values[i], last_setup_down
    else:
        setup_up_now, setup_up_before = close_values[i], last_setup_up
        setup_down_now, setup_down_before = close_values[i], last_setup_down

    if finite(last_ph) and crossed_up(setup_up_now, setup_up_before, last_ph):
        entry = {
            "kind": "high",
            "bar": i,
            "level": float(low_values[i]),
            "pivot_level": float(last_ph),
        }
        if allow_multiple:
            pending.append(entry)
        else:
            pending = [entry]
    if finite(last_pl) and crossed_down(setup_down_now, setup_down_before, last_pl):
        entry = {
            "kind": "low",
            "bar": i,
            "level": float(high_values[i]),
            "pivot_level": float(last_pl),
        }
        if allow_multiple:
            pending.append(entry)
        else:
            pending = [entry]

    if pending:
        bo_pending[i] = float(pending[-1]["level"])

    if confirm_src == "wick":
        confirm_up_now, confirm_up_before = high_values[i], last_confirm_up
        confirm_down_now, confirm_down_before = low_values[i], last_confirm_down
    else:
        confirm_up_now, confirm_up_before = close_values[i], last_confirm_up
        confirm_down_now, confirm_down_before = close_values[i], last_confirm_down

    remaining = []
    for entry in pending:
        age = i - int(entry["bar"])
        if age < min_break:
            remaining.append(entry)
            continue
        in_window = max_break == 0 or age <= max_break
        if not in_window:
            # Expiration is causal: no previous pending line is removed from
            # the returned array, only future bars stop displaying it.
            continue

        is_short_reversal = entry["kind"] == "high"
        confirmed = (
            crossed_down(confirm_down_now, confirm_down_before, entry["level"])
            if is_short_reversal
            else crossed_up(confirm_up_now, confirm_up_before, entry["level"])
        )
        if confirmed:
            if is_short_reversal:
                bo_break_down[i] = float(entry["level"])
                short_signal[i] = True
            else:
                bo_break_up[i] = float(entry["level"])
                long_signal[i] = True
            continue

        if cancel_on_invalid_cross and max_break > 0 and age == max_break:
            continue
        remaining.append(entry)
    pending = remaining

    last_setup_up = setup_up_now if finite(setup_up_now) else last_setup_up
    last_setup_down = setup_down_now if finite(setup_down_now) else last_setup_down
    last_confirm_up = confirm_up_now if finite(confirm_up_now) else last_confirm_up
    last_confirm_down = confirm_down_now if finite(confirm_down_now) else last_confirm_down

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
        {"name": "Swing High Level", "data": plot_list(ph_level), "color": pivot_color, "overlay": True, "style": "dashed"},
        {"name": "Swing Low Level", "data": plot_list(pl_level), "color": pivot_color, "overlay": True, "style": "dashed"},
        {"name": "Pending Breakout", "data": plot_list(bo_pending), "color": pivot_color, "overlay": True, "style": "dashed"},
        {"name": "2B Break Up", "data": plot_list(bo_break_up), "color": b_up, "overlay": True},
        {"name": "2B Break Down", "data": plot_list(bo_break_down), "color": b_down, "overlay": True},
    ],
    "signals": [
        {"type": "buy", "text": "2B", "data": long_marks, "color": b_up},
        {"type": "sell", "text": "2B", "data": short_marks, "color": b_down},
    ],
    "metadata": {
        "causal": True,
        "prd": prd,
        "max_break": max_break,
        "min_break": min_break,
        "setup_src": setup_src,
        "confirm_src": confirm_src,
        "cancel_on_invalid_cross": cancel_on_invalid_cross,
        "allow_multiple": allow_multiple,
        "signal_mode": signal_mode,
    },
    "layers": [],
}
