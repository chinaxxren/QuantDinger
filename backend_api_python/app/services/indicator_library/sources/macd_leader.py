# ============================================================
# [Default] MACD Leader
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# MACD Leader uses a second EMA over each fast/slow EMA residual to reduce
# lag. It is a pure oscillator and does not place trades.
# ============================================================

my_indicator_name = "[Default] MACD Leader"
my_indicator_description = (
    "Residual-corrected MACD Leader oscillator with optional conventional MACD lines."
)

# @param short_length int 12 Fast EMA period range=1:200:1
# @param long_length int 26 Slow EMA period range=2:500:1
# @param sig_length int 9 Signal SMA period range=1:200:1
# @param show_macd bool False Show conventional MACD
# @param show_macdsignal bool False Show conventional MACD signal line
# @param src string close Source: close, hl2, hlc3, or ohlc4
# @param ema_seed string sma EMA seed: sma or first

short_length = max(1, int(params.get("short_length", 12)))
long_length = max(short_length + 1, int(params.get("long_length", 26)))
sig_length = max(1, int(params.get("sig_length", 9)))
show_macd = params.get("show_macd", False)
show_macdsignal = params.get("show_macdsignal", False)
src_name = str(params.get("src", "close")).strip().lower()
ema_seed = str(params.get("ema_seed", "sma")).strip().lower()


def as_bool(value, default=False):
    if value is None:
        return default
    if str(value).strip().lower() in ("false", "0", "no", "off"):
        return False
    if str(value).strip().lower() in ("true", "1", "yes", "on"):
        return True
    return bool(value)


show_macd = as_bool(show_macd)
show_macdsignal = as_bool(show_macdsignal)
if ema_seed not in ("sma", "first"):
    raise ValueError("ema_seed must be sma or first")


df = df.copy()
open_price = df["open"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
if src_name == "hl2":
    source = ((high + low) / 2.0).to_numpy(dtype=float)
elif src_name == "hlc3":
    source = ((high + low + close) / 3.0).to_numpy(dtype=float)
elif src_name == "ohlc4":
    source = ((open_price + high + low + close) / 4.0).to_numpy(dtype=float)
else:
    source = close.to_numpy(dtype=float)

n = len(source)


def ema(values, period, seed_mode):
    result = np.full(len(values), np.nan, dtype=float)
    alpha = 2.0 / (period + 1.0)
    finite_indexes = np.where(np.isfinite(values))[0]
    if len(finite_indexes) == 0:
        return result
    start = int(finite_indexes[0])
    if seed_mode == "first":
        result[start] = float(values[start])
        for i in range(start + 1, len(values)):
            if np.isfinite(values[i]) and np.isfinite(result[i - 1]):
                result[i] = alpha * values[i] + (1.0 - alpha) * result[i - 1]
        return result

    seed_end = start + period - 1
    if seed_end >= len(values):
        return result
    seed = values[start:seed_end + 1]
    if len(seed) != period or not np.all(np.isfinite(seed)):
        return result
    result[seed_end] = float(np.mean(seed))
    for i in range(seed_end + 1, len(values)):
        if np.isfinite(values[i]) and np.isfinite(result[i - 1]):
            result[i] = alpha * values[i] + (1.0 - alpha) * result[i - 1]
    return result


def sma(values, period):
    result = np.full(len(values), np.nan, dtype=float)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1:i + 1]
        if len(window) == period and np.all(np.isfinite(window)):
            result[i] = float(np.mean(window))
    return result


sema = ema(source, short_length, ema_seed)
lema = ema(source, long_length, ema_seed)
fast_residual = source - sema
slow_residual = source - lema
i1 = sema + ema(fast_residual, short_length, ema_seed)
i2 = lema + ema(slow_residual, long_length, ema_seed)
macdl = i1 - i2
macd = sema - lema
signal = sma(macd, sig_length)

if not show_macd:
    macd_plot = np.full(n, np.nan, dtype=float)
else:
    macd_plot = macd
if not show_macdsignal:
    signal_plot = np.full(n, np.nan, dtype=float)
else:
    signal_plot = signal


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "MACD Leader", "data": plot_list(macdl), "color": "#800000", "overlay": False, "width": 2},
        {"name": "MACD", "data": plot_list(macd_plot), "color": "#008000", "overlay": False, "width": 1},
        {"name": "MACD Signal", "data": plot_list(signal_plot), "color": "#FF0000", "overlay": False, "width": 1},
    ],
    "signals": [],
    "metadata": {
        "causal": True,
        "src": src_name if src_name in ("close", "hl2", "hlc3", "ohlc4") else "close",
        "short_length": short_length,
        "long_length": long_length,
        "sig_length": sig_length,
        "ema_seed": ema_seed,
        "show_macd": show_macd,
        "show_macdsignal": show_macdsignal,
    },
    "layers": [],
}
