"""Reviewed backend calculation for the ad indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _line, _output, _series, np, pd


def _ad(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    volume = _series(df, "volume").fillna(0)
    clv = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    return _output("AD", [_line("ad", "AD", (clv.fillna(0) * volume).cumsum())])


compute = _ad
