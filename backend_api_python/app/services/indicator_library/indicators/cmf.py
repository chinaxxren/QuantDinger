"""Reviewed backend calculation for the cmf indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _cmf(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 20, minimum=2, maximum=200)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    volume = _series(df, "volume").fillna(0).clip(lower=0)
    clv = (((close - low) - (high - close)) / (high - low).replace(0, np.nan)).fillna(0)
    denominator = volume.rolling(period, min_periods=period).sum().replace(0, np.nan)
    values = (clv * volume).rolling(period, min_periods=period).sum() / denominator
    return _output("Chaikin Money Flow", [_line("cmf", f"CMF({period})", values, color="#26a69a")])


compute = _cmf
