"""Reviewed backend calculation for the sar indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _line, _output, _sar_rate, _series, np, pd


def _sar(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    # Preserve the existing frontend public defaults (2/2/20) while computing
    # with decimal SAR acceleration values (0.02/0.02/0.2).
    step = _sar_rate(params, "step", 2)
    maximum = _sar_rate(params, "max", 20)
    if maximum < step:
        raise ValueError("invalid parameter: max")
    high = _series(df, "high").to_numpy(dtype=float, copy=False)
    low = _series(df, "low").to_numpy(dtype=float, copy=False)
    values = np.full(len(df), np.nan)
    if len(df):
        rising, af, extreme, sar = True, step, high[0], low[0]
        values[0] = sar
        for index in range(1, len(df)):
            sar = sar + af * (extreme - sar)
            if rising:
                sar = min(sar, low[index - 1], low[index - 2] if index > 1 else low[index - 1])
                if low[index] < sar:
                    rising, sar, extreme, af = False, extreme, low[index], step
                elif high[index] > extreme:
                    extreme, af = high[index], min(maximum, af + step)
            else:
                sar = max(sar, high[index - 1], high[index - 2] if index > 1 else high[index - 1])
                if high[index] > sar:
                    rising, sar, extreme, af = True, extreme, high[index], step
                elif low[index] < extreme:
                    extreme, af = low[index], min(maximum, af + step)
            values[index] = sar
    return _output("Parabolic SAR", [_line("sar", "SAR", values, overlay=True)])


compute = _sar
