"""Reviewed backend calculation for the mfi indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, _series, np, pd


def _mfi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 14)
    typical = (_series(df, "high") + _series(df, "low") + _close(df)) / 3
    flow = typical * _series(df, "volume").fillna(0)
    direction = typical.diff()
    positive = flow.where(direction > 0, 0).rolling(period, min_periods=period).sum()
    negative = flow.where(direction < 0, 0).rolling(period, min_periods=period).sum()
    ratio = positive / negative.replace(0, np.nan)
    values = 100 - 100 / (1 + ratio)
    values = values.mask((negative == 0) & (positive > 0), 100).mask((negative == 0) & (positive == 0), 0)
    return _output("MFI", [_line("mfi", f"MFI({period})", values)])


compute = _mfi
