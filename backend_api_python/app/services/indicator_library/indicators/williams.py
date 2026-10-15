"""Reviewed backend calculation for the williams indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, _series, np, pd


def _williams(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 14)
    high, low = _series(df, "high"), _series(df, "low")
    highest = high.rolling(period, min_periods=period).max()
    lowest = low.rolling(period, min_periods=period).min()
    denominator = (highest - lowest).replace(0, np.nan)
    return _output("Williams %R", [_line("williams", f"W%R({period})", -100 * (highest - _close(df)) / denominator)])


compute = _williams
