"""Reviewed backend calculation for the ppo indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _bar, _close, _ema, _integer, _line, _output, np, pd


def _ppo(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    fast = _integer(params, "fast_period", 12, minimum=2, maximum=100)
    slow = _integer(params, "slow_period", 26, minimum=3, maximum=200)
    signal_period = _integer(params, "signal_period", 9, minimum=2, maximum=100)
    if fast >= slow:
        raise ValueError("invalid parameter: fast_period")
    close = _close(df)
    slow_ema = _ema(close, slow)
    ppo = 100 * (_ema(close, fast) - slow_ema) / slow_ema.replace(0, np.nan)
    signal = _ema(ppo, signal_period)
    return _output(
        "Percentage Price Oscillator",
        [
            _line("ppo", "PPO", ppo),
            _line("ppo_signal", "Signal", signal, color="#ff6d00"),
            _bar("ppo_histogram", "Histogram", ppo - signal, color="#26a69a"),
        ],
    )


compute = _ppo
