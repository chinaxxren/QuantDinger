"""Reviewed backend calculation for the turtle_channels indicator."""

from app.services.indicator_library.runtime import Any, Mapping, _integer, _line, _output, _series, np, pd


def _turtle(df: pd.DataFrame, params: Mapping[str, Any]) -> dict[str, Any]:
    entry = _integer(params, "entry_length", 20, minimum=5, maximum=100)
    exit_period = _integer(params, "exit_length", 10, minimum=2, maximum=50)
    high, low, close = (_series(df, key) for key in ("high", "low", "close"))
    entry_upper = high.rolling(entry, min_periods=entry).max().shift(1)
    entry_lower = low.rolling(entry, min_periods=entry).min().shift(1)
    exit_upper = high.rolling(exit_period, min_periods=exit_period).max().shift(1)
    exit_lower = low.rolling(exit_period, min_periods=exit_period).min().shift(1)
    closes = close.to_numpy()
    long_condition, short_condition = closes > entry_upper.to_numpy(), closes < entry_lower.to_numpy()
    previous_long, previous_short = (
        np.concatenate(([False], long_condition[:-1])),
        np.concatenate(([False], short_condition[:-1])),
    )
    buys, sells = long_condition & ~previous_long, short_condition & ~previous_short
    return {
        **_output(
            "Turtle Trade Channels",
            [
                _line("turtle_entry_upper", "Entry Upper", entry_upper, overlay=True, color="#26a69a"),
                _line("turtle_entry_lower", "Entry Lower", entry_lower, overlay=True, color="#ef5350"),
                _line("turtle_exit_upper", "Exit Upper", exit_upper, overlay=True, color="#80cbc4"),
                _line("turtle_exit_lower", "Exit Lower", exit_lower, overlay=True, color="#ef9a9a"),
            ],
        ),
        "signals": [
            {
                "type": "buy",
                "text": "Turtle+",
                "data": [float(low.iloc[index]) * 0.995 if buys[index] else None for index in range(len(df))],
                "color": "#00e676",
            },
            {
                "type": "sell",
                "text": "Turtle-",
                "data": [float(high.iloc[index]) * 1.005 if sells[index] else None for index in range(len(df))],
                "color": "#ff5252",
            },
        ],
    }


compute = _turtle
