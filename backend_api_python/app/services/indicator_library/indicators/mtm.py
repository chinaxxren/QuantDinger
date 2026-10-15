"""Reviewed backend calculation for the mtm indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, pd


def _momentum(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 12)
    smoothing = _integer(params, "smoothing", 1)
    values = _close(df).diff(period)
    if smoothing > 1:
        values = values.rolling(smoothing, min_periods=smoothing).mean()
    return _output("Momentum", [_line("mtm", f"MTM({period})", values)])


compute = _momentum
