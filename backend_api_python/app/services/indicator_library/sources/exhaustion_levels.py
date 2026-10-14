# ============================================================
# [Default] Exhaustion Levels
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Leledc-style exhaustion counters with persistent support and resistance
# levels. This implementation emits chart lines and visual markers only.
# ============================================================

my_indicator_name = "[Default] Exhaustion Levels"
my_indicator_description = (
    "Causal exhaustion counters with persistent support/resistance levels and "
    "chart-only reversal markers."
)

# @param exhaustion_switch bool True Show exhaustion signal markers
# @param level_switch bool True Show persistent exhaustion levels
# @param length int 40 Extreme-window length range=2:200:1
# @param bars int 10 Exhaustion counter threshold range=1:100:1
# @param thickness int 2 Support/resistance line width range=1:5:1

exhaustion_switch = bool(params.get("exhaustion_switch", True))
level_switch = bool(params.get("level_switch", True))
length = max(2, int(params.get("length", 40)))
bars = max(1, int(params.get("bars", 10)))
thickness = max(1, min(5, int(params.get("thickness", 2))))

df = df.copy()
open_price = df["open"].astype(float).to_numpy(dtype=float)
high = df["high"].astype(float).to_numpy(dtype=float)
low = df["low"].astype(float).to_numpy(dtype=float)
close = df["close"].astype(float).to_numpy(dtype=float)
n = len(df)

# The source indicator uses persistent counters. A counter is incremented when
# the current close is above/below the close four bars ago; equality leaves it
# unchanged. Exhaustion resets the corresponding counter on the trigger bar.
bindex = np.zeros(n, dtype=int)
sindex = np.zeros(n, dtype=int)
exhaustion = np.zeros(n, dtype=int)
resistance = np.full(n, np.nan, dtype=float)
support = np.full(n, np.nan, dtype=float)

b_count = 0
s_count = 0
last_resistance = np.nan
last_support = np.nan
for i in range(n):
    previous_resistance = last_resistance
    previous_support = last_support

    if i >= 4 and np.isfinite(close[i]) and np.isfinite(close[i - 4]):
        if close[i] > close[i - 4]:
            b_count += 1
        elif close[i] < close[i - 4]:
            s_count += 1

    highest_window = high[max(0, i - length + 1):i + 1]
    lowest_window = low[max(0, i - length + 1):i + 1]
    highest_value = np.max(highest_window) if len(highest_window) and np.isfinite(highest_window).all() else np.nan
    lowest_value = np.min(lowest_window) if len(lowest_window) and np.isfinite(lowest_window).all() else np.nan

    top_exhaustion = (
        b_count > bars
        and np.isfinite(close[i])
        and np.isfinite(open_price[i])
        and np.isfinite(high[i])
        and close[i] < open_price[i]
        and np.isfinite(highest_value)
        and high[i] >= highest_value
    )
    bottom_exhaustion = (
        s_count > bars
        and np.isfinite(close[i])
        and np.isfinite(open_price[i])
        and np.isfinite(low[i])
        and close[i] > open_price[i]
        and np.isfinite(lowest_value)
        and low[i] <= lowest_value
    )

    # Preserve the original Lelex convention: -1 marks a top and +1 marks a
    # bottom. A top takes priority if both conditions are theoretically true.
    if top_exhaustion:
        exhaustion[i] = -1
        b_count = 0
    elif bottom_exhaustion:
        exhaustion[i] = 1
        s_count = 0

    bindex[i] = b_count
    sindex[i] = s_count

    # The levels are stepped forward from the latest exhaustion candle. They
    # never depend on future bars and remain stable until a new level appears.
    if exhaustion[i] != 0 and np.isfinite(high[i]) and close[i] < open_price[i]:
        last_resistance = high[i]
    if exhaustion[i] != 0 and np.isfinite(low[i]) and close[i] > open_price[i]:
        last_support = low[i]

    resistance[i] = last_resistance if np.isfinite(last_resistance) else previous_resistance
    support[i] = last_support if np.isfinite(last_support) else previous_support


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]

resistance_plot = resistance if level_switch else np.full(n, np.nan, dtype=float)
support_plot = support if level_switch else np.full(n, np.nan, dtype=float)
long_marks = [
    float(low[i]) if exhaustion_switch and exhaustion[i] == 1 and np.isfinite(low[i]) else None
    for i in range(n)
]
short_marks = [
    float(high[i]) if exhaustion_switch and exhaustion[i] == -1 and np.isfinite(high[i]) else None
    for i in range(n)
]

output = {
    "name": my_indicator_name,
    "plots": [
        {
            "name": "Exhaustion Resistance",
            "data": plot_list(resistance_plot),
            "color": "#EF5350",
            "overlay": True,
            "width": thickness,
        },
        {
            "name": "Exhaustion Support",
            "data": plot_list(support_plot),
            "color": "#138484",
            "overlay": True,
            "width": thickness,
        },
    ],
    "signals": [
        {"type": "buy", "text": "Exhaustion Bottom", "data": long_marks, "color": "#00C853"},
        {"type": "sell", "text": "Exhaustion Top", "data": short_marks, "color": "#EF5350"},
    ],
    "metadata": {
        "exhaustion": [int(value) if value else None for value in exhaustion],
        "bindex": [int(value) for value in bindex],
        "sindex": [int(value) for value in sindex],
        "causal": True,
    },
    "layers": [],
}
