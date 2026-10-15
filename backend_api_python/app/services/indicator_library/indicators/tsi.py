"""Reviewed backend calculation for the tsi indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _close, _ema, _integer, _line, _output, np, pd


def _tsi(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    long = _integer(params, "long_period", 25, minimum=2, maximum=200)
    short = _integer(params, "short_period", 13, minimum=2, maximum=100)
    signal_period = _integer(params, "signal_period", 7, minimum=2, maximum=100)
    momentum = _close(df).diff()
    smooth = lambda values: _ema(_ema(values, long), short)
    denominator = smooth(momentum.abs()).replace(0, np.nan)
    tsi = (100 * smooth(momentum) / denominator).replace([np.inf, -np.inf], np.nan)
    signal = _ema(tsi, signal_period)
    return _output(
        "True Strength Index", [_line("tsi", "TSI", tsi), _line("tsi_signal", "Signal", signal, color="#ff6d00")]
    )


compute = _tsi
