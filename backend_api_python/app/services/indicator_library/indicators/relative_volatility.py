"""Reviewed backend calculation for the relative_volatility indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _integer, _line, _output, _wilder, np, pd


def _rvi_volatility(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14, minimum=2, maximum=200)
    close = _close(df)
    change = close.diff()
    volatility = close.rolling(period, min_periods=period).std(ddof=0)
    up = volatility.where(change > 0, 0)
    down = volatility.where(change < 0, 0)
    up_average = _wilder(up, period)
    down_average = _wilder(down, period)
    total = up_average + down_average
    values = (100 * up_average / total.replace(0, np.nan)).where(total != 0, 50).clip(0, 100)
    return _output("Relative Volatility Index", [_line("rvi_volatility", "RVI", values, color="#7e57c2")])


compute = _rvi_volatility
