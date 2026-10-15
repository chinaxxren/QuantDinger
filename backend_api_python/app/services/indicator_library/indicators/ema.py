"""Reviewed backend calculation for the ema indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _ema, _integer, _line, _output, pd


def _ema_indicator(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 20)
    return _output("EMA", [_line("ema", f"EMA({period})", _ema(_close(df), period), overlay=True)])


compute = _ema_indicator
