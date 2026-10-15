"""Reviewed backend calculation for the adosc indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _ema, _integer, _line, _output, _series, np, pd


def _adosc(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast", 3)
    slow = _integer(params, "slow", 10, minimum=2)
    if fast >= slow:
        raise ValueError("invalid parameter: fast")
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    volume = _series(df, "volume").fillna(0)
    ad = ((((close - low) - (high - close)) / (high - low).replace(0, np.nan)).fillna(0) * volume).cumsum()
    return _output("ADOSC", [_line("adosc", f"ADOSC({fast},{slow})", _ema(ad, fast) - _ema(ad, slow))])


compute = _adosc
