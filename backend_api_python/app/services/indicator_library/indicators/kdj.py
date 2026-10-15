"""Reviewed backend calculation for the kdj indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _kdj(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 9)
    k_period = _integer(params, "k", 3)
    d_period = _integer(params, "d", 3)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    highest = high.rolling(period, min_periods=period).max()
    lowest = low.rolling(period, min_periods=period).min()
    rsv = ((close - lowest) / (highest - lowest).replace(0, np.nan) * 100).fillna(50)
    k = pd.Series(np.nan, index=df.index, dtype=float)
    d = pd.Series(np.nan, index=df.index, dtype=float)
    k_prev, d_prev = 50.0, 50.0
    for index in range(len(df)):
        if index < period - 1:
            continue
        k_prev = ((k_period - 1) * k_prev + rsv.iloc[index]) / k_period
        d_prev = ((d_period - 1) * d_prev + k_prev) / d_period
        k.iloc[index], d.iloc[index] = k_prev, d_prev
    return _output(
        "KDJ",
        [
            _line("k", f"K({period},{k_period})", k),
            _line("d", f"D({d_period})", d, color="#4ECDC4"),
            _line("j", "J", 3 * k - 2 * d, color="#95E1D3"),
        ],
    )


compute = _kdj
