"""Reviewed backend calculation for the vwap indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, _series, np, pd


def _vwap(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20)
    typical = (_series(df, "high") + _series(df, "low") + _close(df)) / 3
    volume = _series(df, "volume").fillna(0)
    denom = volume.rolling(period, min_periods=period).sum().replace(0, np.nan)
    values = (typical * volume).rolling(period, min_periods=period).sum() / denom
    return _output("Volume Weighted Average Price", [_line("vwap", f"VWAP({period})", values, overlay=True)])


compute = _vwap
