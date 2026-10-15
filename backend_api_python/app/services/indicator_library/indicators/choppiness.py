"""Reviewed backend calculation for the choppiness indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _choppiness(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "period", 14, minimum=2, maximum=200)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    previous_close = close.shift(1)
    true_range = pd.concat([high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(
        axis=1
    )
    range_sum = true_range.rolling(period, min_periods=period).sum()
    span = (high.rolling(period, min_periods=period).max() - low.rolling(period, min_periods=period).min()).replace(
        0, np.nan
    )
    ratio = (range_sum / span).replace([np.inf, -np.inf], np.nan)
    values = (100 * np.log10(ratio) / np.log10(float(period))).replace([np.inf, -np.inf], np.nan).clip(0, 100)
    return _output("Choppiness Index", [_line("choppiness", f"CHOP({period})", values, color="#ab47bc")])


compute = _choppiness
