"""Reviewed backend calculation for the bb indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _number, _output, pd


def _bollinger(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 20)
    multiplier = _number(params, "mult", 2.0, minimum=0.1, maximum=10)
    close = _close(df)
    middle = close.rolling(period, min_periods=period).mean()
    std = close.rolling(period, min_periods=period).std(ddof=0)
    return _output(
        "Bollinger Bands",
        [
            _line("upper", f"Upper({period},{multiplier:g})", middle + multiplier * std, overlay=True),
            _line("middle", f"Middle({period})", middle, overlay=True, color="#8c8c8c"),
            _line("lower", f"Lower({period},{multiplier:g})", middle - multiplier * std, overlay=True),
        ],
    )


compute = _bollinger
