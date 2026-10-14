# ============================================================
# [Default] Flawless Victory Strategy
# --- QuantDinger chart indicator contract ---
# ------------------------------------------------------------
# Bollinger mean-reversion bands with RSI/MFI filters. The source is
# intentionally chart-only: it exposes entry/exit markers and visual risk
# levels but never submits orders or mutates a trading position.
# ============================================================

my_indicator_name = "[Default] Flawless Victory Strategy"
my_indicator_description = (
    "Bollinger mean-reversion bands with RSI/MFI filters and chart-only "
    "long-entry, exit, stop-loss, and take-profit markers."
)

# @param version string v1 Version: v1, v2, or v3
# @param bb_length int 20 Bollinger period (v2 uses 17 by default) range=2:100:1
# @param bb_multiplier float 1.0 Bollinger standard deviation multiplier range=0.1:4.0:0.1
# @param rsi_length int 14 RSI period range=2:100:1
# @param mfi_length int 14 MFI period range=2:100:1
# @param v1_rsi_lower float 42.0 v1 entry RSI threshold range=0:100:0.1
# @param v1_rsi_upper float 70.0 v1 exit RSI threshold range=0:100:0.1
# @param v2_rsi_lower float 42.0 v2 entry RSI threshold range=0:100:0.1
# @param v2_rsi_upper float 76.0 v2 exit RSI threshold range=0:100:0.1
# @param v2_stoploss float 6.604 v2 stop loss percentage range=0:100:0.001
# @param v2_takeprofit float 2.328 v2 take profit percentage range=0:100:0.001
# @param v3_mfi_lower float 60.0 v3 entry MFI threshold range=0:100:0.1
# @param v3_rsi_upper float 65.0 v3 exit RSI threshold range=0:100:0.1
# @param v3_mfi_upper float 64.0 v3 exit MFI threshold range=0:100:0.1
# @param v3_stoploss float 8.882 v3 stop loss percentage range=0:100:0.001
# @param v3_takeprofit float 2.317 v3 take profit percentage range=0:100:0.001


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


version = str(params.get("version", "v1")).strip().lower()
if version not in ("v1", "v2", "v3"):
    version = "v1"

configured_bb_length = max(2, int(params.get("bb_length", 20)))
if "bb_length" not in params:
    configured_bb_length = 17 if version == "v2" else 20
bb_length = configured_bb_length
bb_multiplier = max(0.1, float(params.get("bb_multiplier", 1.0)))
rsi_length = max(2, int(params.get("rsi_length", 14)))
mfi_length = max(2, int(params.get("mfi_length", 14)))

v1_rsi_lower = float(params.get("v1_rsi_lower", 42.0))
v1_rsi_upper = float(params.get("v1_rsi_upper", 70.0))
v2_rsi_lower = float(params.get("v2_rsi_lower", 42.0))
v2_rsi_upper = float(params.get("v2_rsi_upper", 76.0))
v2_stoploss = max(0.0, float(params.get("v2_stoploss", 6.604)))
v2_takeprofit = max(0.0, float(params.get("v2_takeprofit", 2.328)))
v3_mfi_lower = float(params.get("v3_mfi_lower", 60.0))
v3_rsi_upper = float(params.get("v3_rsi_upper", 65.0))
v3_mfi_upper = float(params.get("v3_mfi_upper", 64.0))
v3_stoploss = max(0.0, float(params.get("v3_stoploss", 8.882)))
v3_takeprofit = max(0.0, float(params.get("v3_takeprofit", 2.317)))


def plot_list(values):
    return [None if not np.isfinite(value) else float(value) for value in values]


def rsi_wilder(values, length):
    delta = values.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    average_gain = gain.ewm(
        alpha=1.0 / length, adjust=False, min_periods=length
    ).mean()
    average_loss = loss.ewm(
        alpha=1.0 / length, adjust=False, min_periods=length
    ).mean()
    gain_values = average_gain.to_numpy(dtype=float)
    loss_values = average_loss.to_numpy(dtype=float)
    result = np.full(len(values), np.nan, dtype=float)
    valid = np.isfinite(gain_values) & np.isfinite(loss_values)
    nonzero_loss = valid & (loss_values > 0.0)
    result[nonzero_loss] = 100.0 - (100.0 / (1.0 + gain_values[nonzero_loss] / loss_values[nonzero_loss]))
    result[valid & (loss_values <= 0.0) & (gain_values > 0.0)] = 100.0
    result[valid & (loss_values <= 0.0) & (gain_values <= 0.0)] = 50.0
    return result


df = df.copy()
open_price = df["open"].astype(float)
high = df["high"].astype(float)
low = df["low"].astype(float)
close = df["close"].astype(float)
volume = df["volume"].astype(float)

basis_series = close.rolling(bb_length, min_periods=bb_length).mean()
std_series = close.rolling(bb_length, min_periods=bb_length).std(ddof=0)
basis = basis_series.to_numpy(dtype=float)
upper = (basis_series + bb_multiplier * std_series).to_numpy(dtype=float)
lower = (basis_series - bb_multiplier * std_series).to_numpy(dtype=float)

rsi = rsi_wilder(close, rsi_length)
typical_price = (high + low + close) / 3.0
money_flow = typical_price * volume
price_delta = typical_price.diff().to_numpy(dtype=float)
money_flow_values = money_flow.to_numpy(dtype=float)
positive_flow = np.where(price_delta > 0.0, money_flow_values, 0.0)
negative_flow = np.where(price_delta < 0.0, money_flow_values, 0.0)
positive_sum = pd.Series(positive_flow, index=df.index).rolling(
    mfi_length, min_periods=mfi_length
).sum().to_numpy(dtype=float)
negative_sum = pd.Series(negative_flow, index=df.index).rolling(
    mfi_length, min_periods=mfi_length
).sum().to_numpy(dtype=float)
mfi = np.full(len(df), np.nan, dtype=float)
valid_mfi = np.isfinite(positive_sum) & np.isfinite(negative_sum)
nonzero_negative = valid_mfi & (negative_sum > 0.0)
mfi[nonzero_negative] = 100.0 - (
    100.0 / (1.0 + positive_sum[nonzero_negative] / negative_sum[nonzero_negative])
)
mfi[valid_mfi & (negative_sum <= 0.0) & (positive_sum > 0.0)] = 100.0
mfi[valid_mfi & (negative_sum <= 0.0) & (positive_sum <= 0.0)] = 50.0

close_values = close.to_numpy(dtype=float)
high_values = high.to_numpy(dtype=float)
low_values = low.to_numpy(dtype=float)
n = len(df)

if version == "v2":
    entry_condition = (close_values < lower) & (rsi > v2_rsi_lower)
    exit_condition = (close_values > upper) & (rsi > v2_rsi_upper)
    stoploss_percent = v2_stoploss
    takeprofit_percent = v2_takeprofit
elif version == "v3":
    entry_condition = (close_values < lower) & (mfi < v3_mfi_lower)
    exit_condition = (
        (close_values > upper) & (rsi > v3_rsi_upper) & (mfi > v3_mfi_upper)
    )
    stoploss_percent = v3_stoploss
    takeprofit_percent = v3_takeprofit
else:
    entry_condition = (close_values < lower) & (rsi > v1_rsi_lower)
    exit_condition = (close_values > upper) & (rsi > v1_rsi_upper)
    stoploss_percent = 0.0
    takeprofit_percent = 0.0

long_signal = np.zeros(n, dtype=bool)
exitlong_signal = np.zeros(n, dtype=bool)
stoploss = np.full(n, np.nan, dtype=float)
takeprofit = np.full(n, np.nan, dtype=float)
active_entry = np.nan
active_stoploss = np.nan
active_takeprofit = np.nan
active = False

for i in range(n):
    if active:
        stop_hit = (
            np.isfinite(active_stoploss)
            and np.isfinite(low_values[i])
            and low_values[i] <= active_stoploss
        )
        takeprofit_hit = (
            np.isfinite(active_takeprofit)
            and np.isfinite(high_values[i])
            and high_values[i] >= active_takeprofit
        )
        exit_hit = bool(exit_condition[i]) or stop_hit or takeprofit_hit
        stoploss[i] = active_stoploss
        takeprofit[i] = active_takeprofit
        if exit_hit:
            exitlong_signal[i] = True
            active = False
            active_entry = np.nan
            active_stoploss = np.nan
            active_takeprofit = np.nan
        continue

    if bool(entry_condition[i]) and np.isfinite(close_values[i]):
        long_signal[i] = True
        active = True
        active_entry = close_values[i]
        if version != "v1":
            active_stoploss = active_entry * (1.0 - stoploss_percent / 100.0)
            active_takeprofit = active_entry * (1.0 + takeprofit_percent / 100.0)
            stoploss[i] = active_stoploss
            takeprofit[i] = active_takeprofit

# Keep the unused entry variable explicit for source-level reviewers and safe
# execution validation; it is only used as the basis for chart risk levels.
_ = active_entry

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "Basis", "data": plot_list(basis), "color": "#9E9E9E", "overlay": True},
        {"name": "Upper", "data": plot_list(upper), "color": "#2962FF", "overlay": True},
        {"name": "Lower", "data": plot_list(lower), "color": "#2962FF", "overlay": True},
        {"name": "Stop Loss", "data": plot_list(stoploss), "color": "#EF5350", "overlay": True},
        {"name": "Take Profit", "data": plot_list(takeprofit), "color": "#26A69A", "overlay": True},
    ],
    "signals": [
        {
            "type": "buy",
            "text": "Long Entry",
            "data": [
                float(low_values[i]) * 0.995
                if long_signal[i] and np.isfinite(low_values[i])
                else None
                for i in range(n)
            ],
            "color": "#00C853",
        },
        {
            "type": "sell",
            "text": "Long Exit",
            "data": [
                float(high_values[i]) * 1.005
                if exitlong_signal[i] and np.isfinite(high_values[i])
                else None
                for i in range(n)
            ],
            "color": "#FF5252",
        },
    ],
    "metadata": {
        "version": version,
        "bb_length": bb_length,
        "basis": plot_list(basis),
        "upper": plot_list(upper),
        "lower": plot_list(lower),
        "rsi": plot_list(rsi),
        "mfi": plot_list(mfi),
        "stoploss": plot_list(stoploss),
        "takeprofit": plot_list(takeprofit),
        "causal": True,
        "chart_only": True,
    },
    "layers": [],
}
