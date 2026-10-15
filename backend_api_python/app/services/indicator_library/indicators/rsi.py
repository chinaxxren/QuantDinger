"""Reviewed backend calculation for the rsi indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, _rsi_series, pd


def _rsi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 14)
    return _output("RSI", [_line("rsi", f"RSI({period})", _rsi_series(_close(df), period))])


compute = _rsi
