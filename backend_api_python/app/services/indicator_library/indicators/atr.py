"""Reviewed backend calculation for the atr indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _atr, _integer, _line, _output, pd


def _atr_indicator(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14)
    return _output("ATR", [_line("atr", f"ATR({period})", _atr(df, period))])


compute = _atr_indicator
