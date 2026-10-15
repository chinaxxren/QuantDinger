"""Reviewed backend calculation for the bop indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _bop(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "smooth_period", 1, minimum=1, maximum=100)
    open_price, high, low, close = (_series(df, key) for key in ("open", "high", "low", "close"))
    values = (
        ((close - open_price) / (high - low).replace(0, np.nan))
        .replace([np.inf, -np.inf], np.nan)
        .where(high != low, 0)
        .clip(-1, 1)
    )
    if period > 1:
        values = values.rolling(period, min_periods=period).mean()
    return _output("Balance of Power", [_line("bop", "BOP", values, color="#26a69a")])


compute = _bop
