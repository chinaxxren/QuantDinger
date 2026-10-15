"""Reviewed backend calculation for the kama indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, np, pd


def _kama(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 10, minimum=2, maximum=100)
    fast = _integer(params, "fast_period", 2, minimum=1, maximum=50)
    slow = _integer(params, "slow_period", 30, minimum=2, maximum=200)
    if fast >= slow:
        raise ValueError("invalid parameter: fast_period")
    close = _close(df)
    efficiency = (
        close.diff(period).abs() / close.diff().abs().rolling(period, min_periods=period).sum().replace(0, np.nan)
    ).fillna(0)
    fast_sc, slow_sc = 2 / (fast + 1), 2 / (slow + 1)
    smoothing = (efficiency * (fast_sc - slow_sc) + slow_sc) ** 2
    values = pd.Series(np.nan, index=df.index)
    if len(close) > period:
        values.iloc[period] = close.iloc[period]
        for index in range(period + 1, len(close)):
            values.iloc[index] = values.iloc[index - 1] + smoothing.iloc[index] * (
                close.iloc[index] - values.iloc[index - 1]
            )
    return _output(
        "Kaufman Adaptive Moving Average", [_line("kama", f"KAMA({period})", values, overlay=True, color="#ab47bc")]
    )


compute = _kama
