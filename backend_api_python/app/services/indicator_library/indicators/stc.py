"""Reviewed backend calculation for the stc indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _ema, _integer, _line, _number, _output, np, pd


def _stc(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast_period", 23, minimum=2, maximum=150)
    slow = _integer(params, "slow_period", 50, minimum=3, maximum=250)
    cycle = _integer(params, "cycle_period", 10, minimum=2, maximum=100)
    smoothing = _number(params, "smoothing", 0.5, minimum=0.1, maximum=1)
    if fast >= slow:
        raise ValueError("invalid parameter: fast_period")
    close = _close(df)
    macd = _ema(close, fast) - _ema(close, slow)
    minimum = macd.rolling(cycle, min_periods=cycle).min()
    maximum = macd.rolling(cycle, min_periods=cycle).max()
    width = maximum - minimum
    raw = (100 * (macd - minimum) / width.replace(0, np.nan)).where(width != 0, 50)
    first = pd.Series(np.nan, index=df.index)
    previous = 50.0
    for index, value in enumerate(raw):
        if np.isfinite(value):
            previous = smoothing * float(value) + (1 - smoothing) * previous
            first.iloc[index] = previous
    low = first.rolling(cycle, min_periods=cycle).min()
    high = first.rolling(cycle, min_periods=cycle).max()
    second_width = high - low
    second_raw = (100 * (first - low) / second_width.replace(0, np.nan)).where(second_width != 0, 50)
    result = pd.Series(np.nan, index=df.index)
    previous = 50.0
    for index, value in enumerate(second_raw):
        if np.isfinite(value):
            previous = smoothing * float(value) + (1 - smoothing) * previous
            result.iloc[index] = previous
    return _output("Schaff Trend Cycle", [_line("stc", "STC", result, color="#2962ff")])


compute = _stc
