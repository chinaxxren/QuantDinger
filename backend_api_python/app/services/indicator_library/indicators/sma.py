"""Reviewed backend calculation for the sma indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, pd


def _sma(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 20)
    return _output(
        "SMA", [_line("sma", f"SMA({period})", _close(df).rolling(period, min_periods=period).mean(), overlay=True)]
    )


compute = _sma
