# ============================================================
# [Default] SMT Divergences
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Causal swing-high/swing-low divergence detector. Optional comparison data
# can be supplied through params; without it the indicator still exposes the
# primary symbol's confirmed swing levels but does not fabricate SMT signals.
# ============================================================

my_indicator_name = "[Default] SMT Divergences"
my_indicator_description = (
    "Confirmed swing divergence detector with optional comparison series and "
    "chart-only SMT markers."
)

# @param length int 3 Pivot lookback and confirmation width range=2:20:1
# @param use_sym1 bool True Enable comparison series 1
# @param sym1 string None Comparison series 1 identifier or payload
# @param use_sym2 bool True Enable comparison series 2
# @param sym2 string None Comparison series 2 identifier or payload
# @param bull_color string #ff1100 Swing-high divergence color
# @param bear_color string #2157f3 Swing-low divergence color
# @param show_dash bool False Retained for source compatibility

length = max(2, min(20, int(params.get("length", 3))))
use_sym1 = bool(params.get("use_sym1", True))
use_sym2 = bool(params.get("use_sym2", True))
bull_color = str(params.get("bull_color", "#ff1100"))
bear_color = str(params.get("bear_color", "#2157f3"))

# Comparison K-lines are optional because the chart-indicator execution
# contract currently receives one symbol's bars. Integrations that have
# already loaded comparison data may pass either:
#   params["sym1"] = {"high": [...], "low": [...], "close": [...]}
# or params["sym1_high"], params["sym1_low"], params["sym1_close"] arrays.
def _as_array(value):
    if value is None or isinstance(value, str):
        return None
    try:
        values = np.asarray(value, dtype=float).reshape(-1)
    except Exception:
        return None
    return values if len(values) else None


def _comparison_array(name, field, n):
    payload = params.get(name)
    value = None
    if isinstance(payload, dict):
        value = payload.get(field)
        if value is None and field != "close":
            value = payload.get("close")
    if value is None:
        value = params.get(name + "_" + field)
    values = _as_array(value)
    if values is None:
        return None
    # Comparison data is aligned by the tail, matching the MiniBT adapter.
    aligned = np.full(n, np.nan, dtype=float)
    if len(values) >= n:
        aligned[:] = values[-n:]
    else:
        aligned[n - len(values):] = values
    return aligned


df = df.copy()
open_price = df["open"].astype(float).to_numpy(dtype=float)
high = df["high"].astype(float).to_numpy(dtype=float)
low = df["low"].astype(float).to_numpy(dtype=float)
close = df["close"].astype(float).to_numpy(dtype=float)
n = len(df)


def _confirmed_pivots(values, want_high):
    """Return pivot values at their causal right-side confirmation bar."""
    events = np.full(n, np.nan, dtype=float)
    pivot_indexes = np.full(n, -1, dtype=int)
    for confirmation in range(2 * length, n):
        pivot = confirmation - length
        left = values[pivot - length:pivot]
        right = values[pivot + 1:confirmation + 1]
        candidate = values[pivot]
        if not np.isfinite(candidate) or not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
            continue
        if want_high:
            valid = candidate >= np.max(left) and candidate > np.max(right)
        else:
            valid = candidate <= np.min(left) and candidate < np.min(right)
        if valid:
            events[confirmation] = candidate
            pivot_indexes[confirmation] = pivot
    return events, pivot_indexes


def _fixnan(events):
    values = np.full(n, np.nan, dtype=float)
    last = np.nan
    for i in range(n):
        if np.isfinite(events[i]):
            last = events[i]
        values[i] = last
    return values


primary_high_events, primary_high_indexes = _confirmed_pivots(high, True)
primary_low_events, primary_low_indexes = _confirmed_pivots(low, False)
pivot_high = _fixnan(primary_high_events)
pivot_low = _fixnan(primary_low_events)

div_high = np.full(n, np.nan, dtype=float)
div_low = np.full(n, np.nan, dtype=float)
high_source_tag = np.zeros(n, dtype=int)
low_source_tag = np.zeros(n, dtype=int)
smt_high = np.zeros(n, dtype=int)
smt_low = np.zeros(n, dtype=int)


def _process_comparison(bit, name):
    comparison_high = _comparison_array(name, "high", n)
    comparison_low = _comparison_array(name, "low", n)
    comparison_close = _comparison_array(name, "close", n)
    if comparison_high is None and comparison_close is not None:
        comparison_high = comparison_close.copy()
    if comparison_low is None and comparison_close is not None:
        comparison_low = comparison_close.copy()
    if comparison_high is None or comparison_low is None:
        return False

    comparison_high_events, _ = _confirmed_pivots(comparison_high, True)
    comparison_low_events, _ = _confirmed_pivots(comparison_low, False)

    previous_primary_high = np.nan
    previous_comparison_high = np.nan
    previous_primary_low = np.nan
    previous_comparison_low = np.nan
    for i in range(n):
        primary_high_value = primary_high_events[i]
        comparison_high_value = comparison_high_events[i]
        if np.isfinite(primary_high_value):
            if np.isfinite(comparison_high_value):
                if (
                    np.isfinite(previous_primary_high)
                    and np.isfinite(previous_comparison_high)
                    and (primary_high_value - previous_primary_high)
                    * (comparison_high_value - previous_comparison_high) < 0.0
                ):
                    div_high[i] = primary_high_value
                    high_source_tag[i] += bit
                    smt_high[i] += 1
                previous_primary_high = primary_high_value
                previous_comparison_high = comparison_high_value
            else:
                # Do not pair a primary pivot with a stale comparison pivot.
                previous_primary_high = np.nan
                previous_comparison_high = np.nan

        primary_low_value = primary_low_events[i]
        comparison_low_value = comparison_low_events[i]
        if np.isfinite(primary_low_value):
            if np.isfinite(comparison_low_value):
                if (
                    np.isfinite(previous_primary_low)
                    and np.isfinite(previous_comparison_low)
                    and (primary_low_value - previous_primary_low)
                    * (comparison_low_value - previous_comparison_low) < 0.0
                ):
                    div_low[i] = primary_low_value
                    low_source_tag[i] += bit
                    smt_low[i] += 1
                previous_primary_low = primary_low_value
                previous_comparison_low = comparison_low_value
            else:
                previous_primary_low = np.nan
                previous_comparison_low = np.nan
    return True


comparison_names = []
if use_sym1 and _process_comparison(1, "sym1"):
    comparison_names.append(str(params.get("sym1_name", params.get("sym1", "sym1"))))
if use_sym2 and _process_comparison(2, "sym2"):
    comparison_names.append(str(params.get("sym2_name", params.get("sym2", "sym2"))))

# The first comparison pass writes the divergence endpoint; subsequent passes
# add another source tag and count without changing the endpoint value.
# Rebuild source-specific counters from the accumulated tags so both symbols
# remain visible when they diverge on the same confirmation bar.
for i in range(n):
    smt_high[i] = 1 if high_source_tag[i] else 0
    smt_low[i] = 1 if low_source_tag[i] else 0


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


def int_list(values):
    return [int(value) if value else None for value in values]

high_text = "SMT High"
low_text = "SMT Low"
if comparison_names:
    high_text = "SMT High: " + " | ".join(comparison_names)
    low_text = "SMT Low: " + " | ".join(comparison_names)

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Pivot High", "data": plot_list(pivot_high), "color": bull_color, "overlay": True},
        {"name": "Pivot Low", "data": plot_list(pivot_low), "color": bear_color, "overlay": True},
        {"name": "SMT High Divergence", "data": plot_list(div_high), "color": bull_color, "overlay": True, "width": 1.5},
        {"name": "SMT Low Divergence", "data": plot_list(div_low), "color": bear_color, "overlay": True, "width": 1.5},
    ],
    "signals": [
        {
            "type": "buy",
            "text": low_text,
            "data": [float(low[i]) if low_source_tag[i] and np.isfinite(low[i]) else None for i in range(n)],
            "color": bear_color,
        },
        {
            "type": "sell",
            "text": high_text,
            "data": [float(high[i]) if high_source_tag[i] and np.isfinite(high[i]) else None for i in range(n)],
            "color": bull_color,
        },
    ],
    "metadata": {
        "smt_high": int_list(smt_high),
        "smt_low": int_list(smt_low),
        "div_high_tag": int_list(high_source_tag),
        "div_low_tag": int_list(low_source_tag),
        "comparison_data_used": bool(comparison_names),
        "causal": True,
    },
    "layers": [],
}
