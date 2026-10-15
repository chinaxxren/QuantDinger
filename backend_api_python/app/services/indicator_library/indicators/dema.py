"""Reviewed backend calculation for the dema indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _ema, _integer, _line, _output, pd


def _dema(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=300)
    close = _close(df)
    first = _ema(close, period)
    values = 2 * first - _ema(first, period)
    return _output("Double Exponential Moving Average", [_line("dema", f"DEMA({period})", values, overlay=True)])


compute = _dema
