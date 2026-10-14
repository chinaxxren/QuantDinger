# ============================================================
# [Default] MACD Bollinger Bands
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Bollinger bands applied to the MACD line. All values are chart data only;
# this indicator does not submit orders or manage trading positions.
# ============================================================

my_indicator_name = "[Default] MACD Bollinger Bands"
my_indicator_description = (
    "MACD oscillator with a Bollinger envelope and optional chart-only crossover signals."
)

# @param fast_length int 12 Fast EMA period range=2:50:1
# @param slow_length int 26 Slow EMA period range=3:100:1
# @param signal_length int 9 MACD signal EMA period range=2:50:1
# @param band_length int 20 Bollinger period range=2:100:1
# @param band_multiplier float 2.0 Bollinger standard deviation multiplier range=0.5:4.0:0.1
# @param source string close Source: close, hl2, hlc3, or ohlc4
# @param show_bands bool True Show Bollinger bands
# @param show_signals bool True Show MACD crossover markers


def as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("false", "0", "no", "off"):
            return False
        if lowered in ("true", "1", "yes", "on"):
            return True
    return bool(value)


fast_length = max(2, int(params.get("fast_length", 12)))
slow_length = max(fast_length + 1, int(params.get("slow_length", 26)))
signal_length = max(2, int(params.get("signal_length", 9)))
band_length = max(2, int(params.get("band_length", 20)))
band_multiplier = max(0.1, float(params.get("band_multiplier", 2.0)))
source_name = str(params.get("source", "close")).strip().lower()
show_bands = as_bool(params.get("show_bands", True), True)
show_signals = as_bool(params.get("show_signals", True), True)


df = df.copy()
open_price = df["open"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
if source_name == "hl2":
    source = (high + low) / 2.0
elif source_name == "hlc3":
    source = (high + low + close) / 3.0
elif source_name == "ohlc4":
    source = (open_price + high + low + close) / 4.0
else:
    source_name = "close"
    source = close

fast_ema = source.ewm(span=fast_length, adjust=False, min_periods=fast_length).mean()
slow_ema = source.ewm(span=slow_length, adjust=False, min_periods=slow_length).mean()
macd_line = fast_ema - slow_ema
signal_line = macd_line.ewm(
    span=signal_length, adjust=False, min_periods=signal_length
).mean()
histogram = macd_line - signal_line

band_basis = macd_line.rolling(band_length, min_periods=band_length).mean()
band_std = macd_line.rolling(band_length, min_periods=band_length).std(ddof=0)
band_upper = band_basis + band_multiplier * band_std
band_lower = band_basis - band_multiplier * band_std

macd_values = macd_line.to_numpy(dtype=float)
signal_values = signal_line.to_numpy(dtype=float)
histogram_values = histogram.to_numpy(dtype=float)
n = len(df)
buy = np.zeros(n, dtype=bool)
sell = np.zeros(n, dtype=bool)
for i in range(1, n):
    if (
        np.isfinite(macd_values[i])
        and np.isfinite(signal_values[i])
        and np.isfinite(macd_values[i - 1])
        and np.isfinite(signal_values[i - 1])
    ):
        buy[i] = macd_values[i] > signal_values[i] and macd_values[i - 1] <= signal_values[i - 1]
        sell[i] = macd_values[i] < signal_values[i] and macd_values[i - 1] >= signal_values[i - 1]

if not show_bands:
    band_upper_plot = np.full(n, np.nan, dtype=float)
    band_basis_plot = np.full(n, np.nan, dtype=float)
    band_lower_plot = np.full(n, np.nan, dtype=float)
else:
    band_upper_plot = band_upper.to_numpy(dtype=float)
    band_basis_plot = band_basis.to_numpy(dtype=float)
    band_lower_plot = band_lower.to_numpy(dtype=float)

if not show_signals:
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "MACD", "data": plot_list(macd_values), "color": "#2962FF", "overlay": False},
        {"name": "Signal", "data": plot_list(signal_values), "color": "#FF6D00", "overlay": False},
        {"name": "Histogram", "data": plot_list(histogram_values), "color": "#26A69A", "overlay": False},
        {"name": "BB Upper", "data": plot_list(band_upper_plot), "color": "#AB47BC", "overlay": False},
        {"name": "BB Basis", "data": plot_list(band_basis_plot), "color": "#7E57C2", "overlay": False},
        {"name": "BB Lower", "data": plot_list(band_lower_plot), "color": "#AB47BC", "overlay": False},
    ],
    "signals": [
        {
            "type": "buy",
            "text": "MACD Bullish Cross",
            "data": [
                float(macd_values[i]) if buy[i] and np.isfinite(macd_values[i]) else None
                for i in range(n)
            ],
            "color": "#00C853",
        },
        {
            "type": "sell",
            "text": "MACD Bearish Cross",
            "data": [
                float(macd_values[i]) if sell[i] and np.isfinite(macd_values[i]) else None
                for i in range(n)
            ],
            "color": "#FF5252",
        },
    ],
    "metadata": {
        "causal": True,
        "source": source_name,
        "fast_length": fast_length,
        "slow_length": slow_length,
        "signal_length": signal_length,
        "band_length": band_length,
        "band_multiplier": band_multiplier,
        "show_bands": show_bands,
        "show_signals": show_signals,
        "macd": plot_list(macd_values),
        "signal": plot_list(signal_values),
        "histogram": plot_list(histogram_values),
        "band_upper": plot_list(band_upper.to_numpy(dtype=float)),
        "band_basis": plot_list(band_basis.to_numpy(dtype=float)),
        "band_lower": plot_list(band_lower.to_numpy(dtype=float)),
    },
    "layers": [],
}
