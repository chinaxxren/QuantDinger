"""Reviewed backend calculation for the stochastic indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _stochastic(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    period = _integer(params, "length", 14, minimum=3, maximum=200)
    smooth_k = _integer(params, "smooth_k", 3, minimum=1, maximum=50)
    smooth_d = _integer(params, "smooth_d", 3, minimum=1, maximum=50)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    highest = high.rolling(period, min_periods=period).max()
    lowest = low.rolling(period, min_periods=period).min()
    raw_k = 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)
    percent_k = raw_k.rolling(smooth_k, min_periods=smooth_k).mean()
    percent_d = percent_k.rolling(smooth_d, min_periods=smooth_d).mean()
    return _output(
        "Stochastic Oscillator",
        [
            _line("percent_k", f"%K({period},{smooth_k})", percent_k, color="#2962ff"),
            _line("percent_d", f"%D({smooth_d})", percent_d, color="#ff6d00"),
        ],
    )


compute = _stochastic
