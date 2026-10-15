"""Reviewed backend calculation for the klinger indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _ema, _integer, _line, _output, _series, np, pd


def _klinger(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast_period", 34, minimum=2, maximum=200)
    slow = _integer(params, "slow_period", 55, minimum=3, maximum=250)
    signal_period = _integer(params, "signal_period", 13, minimum=2, maximum=100)
    if fast >= slow:
        raise ValueError("invalid parameter: fast_period")
    high = _series(df, "high").to_numpy()
    low = _series(df, "low").to_numpy()
    close = _close(df).to_numpy()
    volume = _series(df, "volume").fillna(0).clip(lower=0).to_numpy()
    force = np.full(len(df), np.nan)
    trend, previous_range, cumulative_range, previous_sum = 0.0, 0.0, 0.0, np.nan
    for index in range(len(df)):
        price_sum = high[index] + low[index] + close[index]
        bar_range = max(0.0, high[index] - low[index])
        if not np.isfinite(price_sum):
            continue
        current_trend = 1.0 if not np.isfinite(previous_sum) or price_sum >= previous_sum else -1.0
        cumulative_range = (
            cumulative_range + bar_range if trend == 0 or current_trend == trend else previous_range + bar_range
        )
        if cumulative_range > 0:
            force[index] = volume[index] * abs(2 * bar_range / cumulative_range - 1) * current_trend * 100
        trend, previous_range, previous_sum = current_trend, bar_range, price_sum
    force_series = pd.Series(force, index=df.index)
    kvo = _ema(force_series, fast) - _ema(force_series, slow)
    signal = _ema(kvo, signal_period)
    return _output(
        "Klinger Volume Oscillator", [_line("kvo", "KVO", kvo), _line("kvo_signal", "Signal", signal, color="#ff6d00")]
    )


compute = _klinger
