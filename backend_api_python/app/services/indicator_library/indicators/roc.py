"""Reviewed backend calculation for the roc indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, pd


def _roc(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 12)
    smoothing = _integer(params, "smoothing", 1)
    values = _close(df).pct_change(periods=period) * 100
    if smoothing > 1:
        values = values.rolling(smoothing, min_periods=smoothing).mean()
    return _output("Rate of Change", [_line("roc", f"ROC({period})", values)])


compute = _roc
