"""Built-in indicator library smoke tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.services.builtin_indicators import _builtin_specs
from app.utils.safe_exec import build_safe_builtins, safe_exec_with_validation


LEGACY_EXECUTION_TOKENS = (
    "open_long",
    "close_long",
    "open_short",
    "close_short",
    "# @strategy",
    "exit_owner",
    "signal_form",
)


def _mock_df(length: int = 220) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    close = 10000 * np.exp(np.cumsum(rng.normal(0, 0.003, length)))
    open_price = close * (1 + rng.normal(0, 0.0008, length))
    high = np.maximum(open_price, close) * (1 + rng.uniform(0.0002, 0.002, length))
    low = np.minimum(open_price, close) * (1 - rng.uniform(0.0002, 0.002, length))
    volume = rng.lognormal(mean=7.0, sigma=0.35, size=length)
    return pd.DataFrame(
        {
            "time": np.arange(length) * 60_000,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


def test_builtin_indicator_library_has_multiple_file_backed_indicators():
    specs = _builtin_specs()
    assert len(specs) >= 6
    assert len({spec["source_file"] for spec in specs}) == len(specs)
    assert len({spec["name"] for spec in specs}) == len(specs)
    indicator_dir = Path(__file__).parents[1] / "app/services/indicator_library/indicators"
    assert all(spec["source_file"] == f"{spec['id']}.py" for spec in specs)
    assert all((indicator_dir / spec["source_file"]).is_file() for spec in specs)


def test_builtin_indicator_sources_are_chart_only():
    for spec in _builtin_specs():
        code = spec["code"]
        assert all(token not in code for token in LEGACY_EXECUTION_TOKENS), spec["name"]
        assert "my_indicator_name" in code
        assert "output" in code


def test_builtin_indicator_sources_execute_and_return_aligned_output():
    df = _mock_df()
    for spec in _builtin_specs():
        env = {
            "df": df.copy(),
            "pd": pd,
            "np": np,
            "params": {},
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(code=spec["code"], exec_globals=env, exec_locals=env, timeout=15)
        assert result.get("success"), f"{spec['name']}: {result.get('error')}"
        output = env.get("output")
        assert isinstance(output, dict), spec["name"]
        assert output.get("plots") or output.get("signals"), spec["name"]
        for plot in output.get("plots") or []:
            assert len(plot.get("data") or []) == len(df), f"{spec['name']} plot {plot.get('name')}"
        for signal in output.get("signals") or []:
            assert len(signal.get("data") or []) == len(df), f"{spec['name']} signal {signal.get('type')}"


def test_breaks_and_retests_is_causal_and_supports_parameter_controls():
    specs = _builtin_specs()
    spec = next(spec for spec in specs if spec["name"] == "[Default] Breaks and Retests")

    def execute(bars):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": {
                "lookback": 8,
                "ret_since": 1,
                "ret_valid": 4,
                "breakouts": True,
                "retests": True,
            },
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(code=spec["code"], exec_globals=env, exec_locals=env, timeout=15)
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df(180)
    output = execute(bars)
    assert output["metadata"]["causal"] is True
    assert len(output["plots"]) == 4
    assert len(output["signals"]) == 2
    for series in output["plots"] + output["signals"]:
        assert len(series["data"]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in series["data"])

    prefix_length = len(bars) - 17
    prefix_output = execute(bars.iloc[:prefix_length])
    for full_series, prefix_series in zip(output["plots"], prefix_output["plots"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]
    for full_series, prefix_series in zip(output["signals"], prefix_output["signals"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]


def test_swing_failure_pattern_is_causal_and_supports_direction_controls():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] Swing Failure Pattern")

    def execute(bars):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": {"length": 6, "bullish": True, "bearish": True, "percent": 50},
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(code=spec["code"], exec_globals=env, exec_locals=env, timeout=15)
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df(190)
    output = execute(bars)
    assert output["metadata"]["causal"] is True
    assert len(output["plots"]) == 6
    assert len(output["signals"]) == 2
    for series in output["plots"] + output["signals"]:
        assert len(series["data"]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in series["data"])

    prefix_length = len(bars) - 19
    prefix_output = execute(bars.iloc[:prefix_length])
    for full_series, prefix_series in zip(output["plots"], prefix_output["plots"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]
    for full_series, prefix_series in zip(output["signals"], prefix_output["signals"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]


class _FakeIndicatorCursor:
    def __init__(self, db):
        self.db = db
        self.rows = []
        self.rowcount = 0

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split()).lower()
        self.rowcount = 0
        if normalized == "select id from qd_users":
            self.rows = [{"id": user_id} for user_id in self.db.users]
        elif normalized.startswith("select name from qd_indicator_codes"):
            user_id = params[0]
            self.rows = [{"name": name} for name in self.db.indicators.get(user_id, {})]
        elif normalized.startswith("insert into qd_indicator_codes"):
            user_id, name = params[0], params[1]
            self.db.indicators.setdefault(user_id, {})[name] = params[2]
            self.rowcount = 1
        else:
            raise AssertionError(f"Unexpected SQL: {sql}")

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class _FakeIndicatorDb:
    def __init__(self, users, indicators):
        self.users = users
        self.indicators = indicators
        self.commits = 0
        self.rollbacks = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return _FakeIndicatorCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_builtin_indicator_library_syncs_missing_specs_without_overwriting_existing(monkeypatch):
    from app.services.builtin_indicators import sync_builtin_indicator_library_for_existing_users

    specs = _builtin_specs()
    existing_code = "# user-customized SuperTrend"
    db = _FakeIndicatorDb(
        users=[1, 2],
        indicators={1: {specs[0]["name"]: existing_code}, 2: {}},
    )
    monkeypatch.setattr("app.utils.db.get_db_connection", lambda: db)

    assert sync_builtin_indicator_library_for_existing_users() == (len(specs) - 1) + len(specs)
    assert db.indicators[1][specs[0]["name"]] == existing_code
    assert set(db.indicators[1]) == {spec["name"] for spec in specs}
    assert set(db.indicators[2]) == {spec["name"] for spec in specs}
    assert db.commits == 1

    assert sync_builtin_indicator_library_for_existing_users() == 0
    assert db.commits == 2


def test_recent_builtin_indicators_do_not_rewrite_historical_values():
    df = _mock_df()
    recent_names = {
        "[Default] Double Exponential Moving Average",
        "[Default] Kaufman Adaptive Moving Average",
        "[Default] Chaikin Oscillator",
        "[Default] STD-Filtered N-Pole Gaussian Filter",
        "[Default] Adaptive Trend Filter",
        "[Default] Multi-Step Vegas SuperTrend",
        "[Default] Optimized Trend Tracker",
        "[Default] DSAV Dynamic Swing Anchored VWAP",
        "[Default] LOWESS Locally Weighted Scatterplot Smoothing",
        "[Default] John Ehlers The Price Radio",
        "[Default] Trend State Signals",
        "[Default] Trendlines with Breaks",
        "[Default] Adaptive Trend Trail",
        "[Default] SPMA Trend NAL",
        "[Default] Lorentzian Classification",
        "[Default] kNN Lorentzian Machine Learning",
        "[Default] Divergence for Many Indicators v4",
        "[Default] Auto Chart Patterns",
        "[Default] Scalping PullBack Tool",
        "[Default] Swing Highs/Lows & Candle Patterns",
        "[Default] Adaptive SuperTrend",
        "[Default] Zero Lag Trend Signals",
        "[Default] Range Filter B&S Signals",
        "[Default] Range Filter Buy and Sell",
        "[Default] Twin Range Filter",
        "[Default] Follow Line Indicator",
        "[Default] SuperBollingerTrend",
        "[Default] RMI Trend Sniper",
        "[Default] Exhaustion Levels",
        "[Default] SMT Divergences",
        "[Default] PMax on RSI w T3",
        "[Default] RSI Divergence Indicator",
        "[Default] Ghost Tangent Crossings",
        "[Default] 2B Reversal Pattern (Expo)",
        "[Default] MACD Leader",
        "[Default] Machine Learning RSI",
        "[Default] Volume SuperTrend AI",
        "[Default] False Breakout (Expo)",
        "[Default] Multi Kernel Regression [ChartPrime]",
        "[Default] Twin Optimized Trend Tracker",
        "[Default] Scalp Pro",
    }
    specs = [spec for spec in _builtin_specs() if spec["name"] in recent_names]
    assert len(specs) == len(recent_names)

    def execute(code, bars):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": {},
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(code=code, exec_globals=env, exec_locals=env, timeout=15)
        assert result.get("success"), result.get("error")
        return env["output"]

    prefix_length = len(df) - 17
    for spec in specs:
        full_output = execute(spec["code"], df)
        prefix_output = execute(spec["code"], df.iloc[:prefix_length])
        assert len(full_output["plots"]) == len(prefix_output["plots"])
        for full_plot, prefix_plot in zip(full_output["plots"], prefix_output["plots"]):
            assert len(full_plot["data"]) == len(df), spec["name"]
            assert all(value is None or np.isfinite(float(value)) for value in full_plot["data"]), spec["name"]
            assert full_plot["data"][:prefix_length] == prefix_plot["data"], spec["name"]


def test_ghost_tangent_crossings_supports_causal_rendering_options():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] Ghost Tangent Crossings")

    def execute(params):
        env = {
            "df": _mock_df(),
            "pd": pd,
            "np": np,
            "params": params,
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(
            code=spec["code"],
            exec_globals=env,
            exec_locals=env,
            timeout=15,
        )
        assert result.get("success"), result.get("error")
        return env["output"]

    output = execute(
        {
            "pivot_type": "Body",
            "pivot_forward": 5,
            "show_ghosts": False,
            "show_break": False,
            "equipoint_style": "None",
        }
    )
    assert output["metadata"]["causal"] is True
    assert output["metadata"]["pivot_type"] == "Body"
    assert output["metadata"]["equipoint_style"] == "none"
    for plot in output["plots"]:
        assert len(plot["data"]) == len(_mock_df())
        assert all(value is None or np.isfinite(float(value)) for value in plot["data"])
    assert all(value is None for value in output["plots"][2]["data"])
    assert all(value is None for value in output["plots"][3]["data"])
    assert all(value is None for value in output["plots"][4]["data"])
    assert all(value is None for value in output["plots"][5]["data"])
    assert all(value is None for value in output["plots"][6]["data"])
    assert all(value is None for value in output["plots"][7]["data"])
    assert all(value is None for value in output["signals"][0]["data"])
    assert all(value is None for value in output["signals"][1]["data"])


def test_machine_learning_rsi_supports_modes_and_causal_knn_output():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] Machine Learning RSI")

    def execute(bars, params):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": params,
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(
            code=spec["code"],
            exec_globals=env,
            exec_locals=env,
            timeout=15,
        )
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df()
    params = {
        "src": "ohlc4",
        "ma_type": "HMA",
        "use_knn": True,
        "knn_lookback": 60,
        "knn_neighbors": 7,
        "feature_count": 5,
        "filter_method": "DoubleEMA",
        "color_mode": "Impulse",
        "show_table": False,
    }
    output = execute(bars, params)
    assert output["metadata"]["causal"] is True
    assert output["metadata"]["color_mode"] == "impulse"
    assert output["metadata"]["filter_method"] == "doubleema"
    for plot in output["plots"]:
        assert len(plot["data"]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in plot["data"])
    for signal in output["signals"]:
        assert len(signal["data"]) == len(bars)

    prefix_length = len(bars) - 23
    prefix = execute(bars.iloc[:prefix_length], params)
    assert output["metadata"]["rsi"][:prefix_length] == prefix["metadata"]["rsi"]
    assert output["metadata"]["knn_rsi"][:prefix_length] == prefix["metadata"]["knn_rsi"]
    for full_plot, prefix_plot in zip(output["plots"], prefix["plots"]):
        assert full_plot["data"][:prefix_length] == prefix_plot["data"]

    none_output = execute(bars, {"color_mode": "None", "use_knn": False, "use_filter": False})
    assert all(value is None for plot in none_output["plots"][:4] for value in plot["data"])


def test_volume_supertrend_ai_supports_causal_knn_cloud_and_signal_options():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] Volume SuperTrend AI")

    def execute(bars, params):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": params,
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(
            code=spec["code"],
            exec_globals=env,
            exec_locals=env,
            timeout=15,
        )
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df()
    params = {
        "k": 7,
        "n_data": 60,
        "knn_price_len": 12,
        "knn_st_len": 45,
        "length": 8,
        "factor": 2.2,
        "ma_src": "VWMA",
        "cloud_layers": 2,
        "cloud_transp": 65,
        "ai_signals": True,
    }
    output = execute(bars, params)
    assert output["metadata"]["causal"] is True
    assert output["metadata"]["ma_src"] == "vwma"
    assert output["metadata"]["cloud_layers"] == 2
    assert len(output["plots"]) == 8
    assert len(output["signals"]) == 4
    for plot in output["plots"]:
        assert len(plot["data"]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in plot["data"])
    for signal in output["signals"]:
        assert len(signal["data"]) == len(bars)

    prefix_length = len(bars) - 29
    prefix = execute(bars.iloc[:prefix_length], params)
    for full_plot, prefix_plot in zip(output["plots"], prefix["plots"]):
        assert full_plot["data"][:prefix_length] == prefix_plot["data"]
    assert output["metadata"]["ai_label"][:prefix_length] == prefix["metadata"]["ai_label"]

    hidden_cloud = execute(bars, {"show_cloud": False, "ai_signals": False})
    assert all(value is None for plot in hidden_cloud["plots"][3:] for value in plot["data"])
    assert all(value is None for signal in hidden_cloud["signals"] for value in signal["data"])


def test_false_breakout_supports_causal_modes_and_chart_only_signals():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] False Breakout (Expo)")

    def execute(bars, params):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": params,
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(
            code=spec["code"],
            exec_globals=env,
            exec_locals=env,
            timeout=15,
        )
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df(240)
    params = {
        "prd": 8,
        "minperiod": 2,
        "maxperiod": 12,
        "ma_type": "WMA",
        "length": 4,
        "aggressive": False,
    }
    output = execute(bars, params)
    assert output["metadata"]["causal"] is True
    assert output["metadata"]["ma_type"] == "wma"
    assert output["metadata"]["aggressive"] is False
    assert len(output["plots"]) == 2
    assert len(output["signals"]) == 2
    for plot in output["plots"]:
        assert len(plot["data"]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in plot["data"])
    for signal in output["signals"]:
        assert len(signal["data"]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in signal["data"])
    for key in ("hi", "lo", "val", "count"):
        assert len(output["metadata"][key]) == len(bars)

    prefix_length = len(bars) - 31
    prefix = execute(bars.iloc[:prefix_length], params)
    for full_plot, prefix_plot in zip(output["plots"], prefix["plots"]):
        assert full_plot["data"][:prefix_length] == prefix_plot["data"]
    assert output["metadata"]["val"][:prefix_length] == prefix["metadata"]["val"]
    assert output["metadata"]["count"][:prefix_length] == prefix["metadata"]["count"]

    aggressive = execute(bars, {"ma_type": "HMA", "length": 5, "aggressive": True})
    assert aggressive["metadata"]["ma_type"] == "hma"
    assert aggressive["metadata"]["aggressive"] is True
    assert all(value is None or np.isfinite(float(value)) for plot in aggressive["plots"] for value in plot["data"])

    # Two separated local highs followed by a close below the latest trigger
    # level exercise the documented short-side false-breakout signal.
    synthetic = pd.DataFrame(
        {
            "open": [9.5, 10.5, 8.5, 11.5, 9.5, 12.5, 11.7],
            "high": [10, 11, 10, 12, 11, 13, 13],
            "low": [9, 10, 8, 11, 9, 12, 11.5],
            "close": [9.5, 10.5, 8.5, 11.5, 9.5, 12.5, 11.7],
            "volume": [1] * 7,
        }
    )
    signal_output = execute(
        synthetic,
        {"prd": 2, "minperiod": 1, "maxperiod": 5, "ma_type": "None"},
    )
    assert signal_output["signals"][1]["data"][-1] == 13.0
    assert signal_output["metadata"]["count"][-1] == 0

    assert all(token not in spec["code"] for token in LEGACY_EXECUTION_TOKENS)


def test_multi_kernel_regression_supports_causal_kernels_bands_and_confirmation():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] Multi Kernel Regression [ChartPrime]")

    def execute(bars, params):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": params,
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(
            code=spec["code"],
            exec_globals=env,
            exec_locals=env,
            timeout=15,
        )
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df(240)
    kernels = (
        "Triangular",
        "Gaussian",
        "Epanechnikov",
        "Logistic",
        "Log Logistic",
        "Cosine",
        "Sinc",
        "Laplace",
        "Quartic",
        "Parabolic",
        "Exponential",
        "Silverman",
        "Cauchy",
        "Tent",
        "Wave",
        "Power",
        "Morters",
    )
    for kernel in kernels:
        output = execute(
            bars,
            {
                "kernel": kernel,
                "bandwidth": 14,
                "source": "hlc3",
                "deviations": 2.0,
                "enable": True,
                "repaint": True,
                "confirm_bars": 3,
            },
        )
        assert output["metadata"]["causal"] is True
        assert output["metadata"]["repaint"] is False
        assert output["metadata"]["repaint_requested"] is True
        assert output["metadata"]["kernel"] == kernel
        assert len(output["plots"]) == 4
        assert len(output["signals"]) == 2
        for plot in output["plots"]:
            assert len(plot["data"]) == len(bars)
            assert all(value is None or np.isfinite(float(value)) for value in plot["data"])
        for signal in output["signals"]:
            assert len(signal["data"]) == len(bars)
        for key in ("nrp", "nrp_std", "upper", "lower", "long_signal", "short_signal"):
            assert len(output["metadata"][key]) == len(bars)

    disabled = execute(bars, {"enable": False})
    assert all(value is None for plot in disabled["plots"][2:] for value in plot["data"])

    short = execute(bars.iloc[:8], {"bandwidth": 20, "confirm_bars": 1})
    assert all(len(plot["data"]) == 8 for plot in short["plots"])
    assert all(len(signal["data"]) == 8 for signal in short["signals"])

    prefix_length = len(bars) - 29
    full = execute(bars, {"kernel": "Gaussian", "bandwidth": 18, "confirm_bars": 4})
    prefix = execute(bars.iloc[:prefix_length], {"kernel": "Gaussian", "bandwidth": 18, "confirm_bars": 4})
    for full_plot, prefix_plot in zip(full["plots"], prefix["plots"]):
        assert full_plot["data"][:prefix_length] == prefix_plot["data"]
    for key in ("nrp", "nrp_std", "long_signal", "short_signal"):
        assert full["metadata"][key][:prefix_length] == prefix["metadata"][key]

    assert all(token not in spec["code"] for token in LEGACY_EXECUTION_TOKENS)


def test_twin_optimized_trend_tracker_supports_ma_modes_delay_and_visual_options():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] Twin Optimized Trend Tracker")

    def execute(bars, params):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": params,
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(
            code=spec["code"],
            exec_globals=env,
            exec_locals=env,
            timeout=15,
        )
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df(240)
    for ma_type in ("SMA", "EMA", "WMA", "TMA", "VAR", "WWMA", "ZLEMA", "TSF"):
        for source in ("close", "hl2", "hlc3", "ohlc4"):
            output = execute(
                bars,
                {
                    "length": 12,
                    "percent": 1.0,
                    "coeff": 0.001,
                    "ma_type": ma_type,
                    "var_length": 9,
                    "source": source,
                    "ma_seed": "first",
                    "show_support": True,
                    "show_signals": True,
                },
            )
            assert output["metadata"]["causal"] is True
            assert output["metadata"]["ma_type"] == ma_type
            assert output["metadata"]["source"] == source
            assert len(output["plots"]) == 3
            assert len(output["signals"]) == 2
            for plot in output["plots"]:
                assert len(plot["data"]) == len(bars)
                assert all(value is None or np.isfinite(float(value)) for value in plot["data"])
            for signal in output["signals"]:
                assert len(signal["data"]) == len(bars)
            for key in (
                "ott",
                "ott_up_raw",
                "ott_dn_raw",
                "long_stop",
                "short_stop",
                "direction",
                "long_signal",
                "short_signal",
            ):
                assert len(output["metadata"][key]) == len(bars)

    hidden = execute(
        bars,
        {
            "length": 12,
            "ma_type": "VAR",
            "source": "ohlc4",
            "ma_seed": "zero",
            "show_support": False,
            "show_signals": False,
        },
    )
    assert all(value is None for value in hidden["plots"][0]["data"])
    assert all(value is None for value in hidden["signals"][0]["data"])
    assert all(value is None for value in hidden["signals"][1]["data"])
    assert hidden["metadata"]["ma_seed"] == "zero"

    # Twin lines are delayed by exactly two already-computed bars.
    delayed = execute(bars, {"length": 10, "ma_type": "EMA", "coeff": 0.01})
    raw_up = delayed["metadata"]["ott_up_raw"]
    raw_dn = delayed["metadata"]["ott_dn_raw"]
    up = delayed["plots"][1]["data"]
    dn = delayed["plots"][2]["data"]
    assert up[:2] == [None, None]
    assert dn[:2] == [None, None]
    for i in range(2, len(bars)):
        assert up[i] == raw_up[i - 2]
        assert dn[i] == raw_dn[i - 2]

    prefix_length = len(bars) - 31
    full = execute(bars, {"length": 13, "ma_type": "VAR", "source": "hlc3"})
    prefix = execute(bars.iloc[:prefix_length], {"length": 13, "ma_type": "VAR", "source": "hlc3"})
    for full_plot, prefix_plot in zip(full["plots"], prefix["plots"]):
        assert full_plot["data"][:prefix_length] == prefix_plot["data"]
    for key in ("ott", "ott_up_raw", "ott_dn_raw", "long_signal", "short_signal"):
        assert full["metadata"][key][:prefix_length] == prefix["metadata"][key]

    assert all(token not in spec["code"] for token in LEGACY_EXECUTION_TOKENS)


def test_scalp_pro_supports_causal_super_smoother_modes_and_visual_options():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] Scalp Pro")

    def execute(bars, params):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": params,
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(
            code=spec["code"],
            exec_globals=env,
            exec_locals=env,
            timeout=15,
        )
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df(240)
    for source in ("close", "hl2", "hlc3", "ohlc4"):
        output = execute(
            bars,
            {
                "fast_length": 8,
                "slow_length": 10,
                "smooth_length": 8,
                "scale": 10000000.0,
                "source": source,
                "show_fill": True,
                "show_signals": True,
            },
        )
        assert output["metadata"]["causal"] is True
        assert output["metadata"]["source"] == source
        assert output["metadata"]["show_fill"] is True
        assert len(output["plots"]) == 2
        assert len(output["signals"]) == 2
        for plot in output["plots"]:
            assert len(plot["data"]) == len(bars)
            assert all(value is None or np.isfinite(float(value)) for value in plot["data"])
        for signal in output["signals"]:
            assert len(signal["data"]) == len(bars)
            assert all(value is None or np.isfinite(float(value)) for value in signal["data"])
        for key in ("ssmooth", "ssmooth2", "macd", "signal", "long_signal", "short_signal"):
            assert len(output["metadata"][key]) == len(bars)

    hidden = execute(
        bars,
        {
            "fast_length": 5,
            "slow_length": 9,
            "smooth_length": 4,
            "scale": 1000,
            "source": "ohlc4",
            "show_fill": False,
            "show_signals": False,
        },
    )
    assert hidden["metadata"]["show_fill"] is False
    assert hidden["metadata"]["show_signals"] is False
    assert all(value is None for signal in hidden["signals"] for value in signal["data"])

    # SuperSmoother state is causal: adding future bars cannot change the prefix.
    params = {"fast_length": 7, "slow_length": 13, "smooth_length": 6, "scale": 10000}
    full = execute(bars, params)
    prefix_length = len(bars) - 37
    prefix = execute(bars.iloc[:prefix_length], params)
    for full_plot, prefix_plot in zip(full["plots"], prefix["plots"]):
        assert full_plot["data"][:prefix_length] == prefix_plot["data"]
    for key in ("ssmooth", "ssmooth2", "macd", "signal", "long_signal", "short_signal"):
        assert full["metadata"][key][:prefix_length] == prefix["metadata"][key]

    assert all(token not in spec["code"] for token in LEGACY_EXECUTION_TOKENS)


def test_smart_money_breakouts_is_causal_and_supports_chart_only_controls():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] Smart Money Breakouts")

    def execute(bars, params=None):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": params or {},
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(code=spec["code"], exec_globals=env, exec_locals=env, timeout=15)
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df(260)
    params = {
        "length": 8,
        "candle_type": "Body",
        "rr_ratio": 1.5,
        "sl_type": "High/Low",
        "show_sl": True,
        "line_style": "Dotted",
    }
    output = execute(bars, params)
    assert output["metadata"]["causal"] is True
    assert output["metadata"]["candle_type"] == "Body"
    assert output["metadata"]["show_sl"] is True
    assert output["metadata"]["line_style"] == "dotted"
    assert len(output["plots"]) == 4
    assert len(output["signals"]) == 2
    for series in output["plots"] + output["signals"]:
        assert len(series["data"]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in series["data"])
    for key in (
        "break_type",
        "vol_sign",
        "winning",
        "losing",
        "trade_on",
    ):
        assert len(output["metadata"][key]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in output["metadata"][key])

    hidden = execute(bars, {"length": 8, "show_sl": False})
    assert all(value is None for value in hidden["plots"][3]["data"])

    prefix_length = len(bars) - 31
    prefix = execute(bars.iloc[:prefix_length], params)
    for full_series, prefix_series in zip(output["plots"], prefix["plots"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]
    for full_series, prefix_series in zip(output["signals"], prefix["signals"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]
    for key in ("break_type", "vol_sign", "winning", "losing", "trade_on"):
        assert output["metadata"][key][:prefix_length] == prefix["metadata"][key]


def test_macd_bollinger_bands_is_causal_and_supports_chart_only_controls():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] MACD Bollinger Bands")

    def execute(bars, params):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": params,
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(code=spec["code"], exec_globals=env, exec_locals=env, timeout=15)
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df(240)
    params = {
        "fast_length": 8,
        "slow_length": 21,
        "signal_length": 7,
        "band_length": 15,
        "band_multiplier": 1.8,
        "source": "hlc3",
        "show_bands": True,
        "show_signals": True,
    }
    output = execute(bars, params)
    assert output["metadata"]["causal"] is True
    assert output["metadata"]["source"] == "hlc3"
    assert output["metadata"]["show_bands"] is True
    assert output["metadata"]["show_signals"] is True
    assert len(output["plots"]) == 6
    assert len(output["signals"]) == 2
    for series in output["plots"] + output["signals"]:
        assert len(series["data"]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in series["data"])
    for key in ("macd", "signal", "histogram", "band_upper", "band_basis", "band_lower"):
        assert len(output["metadata"][key]) == len(bars)

    hidden = execute(
        bars,
        {
            "fast_length": 8,
            "slow_length": 21,
            "signal_length": 7,
            "band_length": 15,
            "show_bands": False,
            "show_signals": False,
        },
    )
    assert hidden["metadata"]["show_bands"] is False
    assert hidden["metadata"]["show_signals"] is False
    assert all(value is None for plot in hidden["plots"][3:] for value in plot["data"])
    assert all(value is None for signal in hidden["signals"] for value in signal["data"])

    prefix_length = len(bars) - 29
    prefix = execute(bars.iloc[:prefix_length], params)
    for full_plot, prefix_plot in zip(output["plots"], prefix["plots"]):
        assert full_plot["data"][:prefix_length] == prefix_plot["data"]
    for full_signal, prefix_signal in zip(output["signals"], prefix["signals"]):
        assert full_signal["data"][:prefix_length] == prefix_signal["data"]
    for key in ("macd", "signal", "histogram", "band_upper", "band_basis", "band_lower"):
        assert output["metadata"][key][:prefix_length] == prefix["metadata"][key]

    assert all(token not in spec["code"] for token in LEGACY_EXECUTION_TOKENS)


def test_flawless_victory_strategy_is_chart_only_and_causal():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] Flawless Victory Strategy")

    def execute(bars, params):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": params,
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(code=spec["code"], exec_globals=env, exec_locals=env, timeout=15)
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df(260)
    params = {
        "version": "v2",
        "bb_length": 17,
        "bb_multiplier": 1.0,
        "rsi_length": 14,
        "mfi_length": 14,
    }
    output = execute(bars, params)
    assert output["metadata"]["causal"] is True
    assert output["metadata"]["chart_only"] is True
    assert output["metadata"]["version"] == "v2"
    assert len(output["plots"]) == 5
    assert len(output["signals"]) == 2
    for series in output["plots"] + output["signals"]:
        assert len(series["data"]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in series["data"])
    for key in ("basis", "upper", "lower", "rsi", "mfi", "stoploss", "takeprofit"):
        assert len(output["metadata"][key]) == len(bars)

    v1 = execute(bars, {"version": "v1"})
    assert all(value is None for value in v1["plots"][3]["data"])
    assert all(value is None for value in v1["plots"][4]["data"])

    prefix_length = len(bars) - 31
    prefix = execute(bars.iloc[:prefix_length], params)
    for full_series, prefix_series in zip(output["plots"], prefix["plots"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]
    for full_series, prefix_series in zip(output["signals"], prefix["signals"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]
    for key in ("basis", "upper", "lower", "rsi", "mfi", "stoploss", "takeprofit"):
        assert output["metadata"][key][:prefix_length] == prefix["metadata"][key]

    assert all(token not in spec["code"] for token in LEGACY_EXECUTION_TOKENS)


def test_trading_abc_is_chart_only_causal_and_parameterized():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] Trading ABC")

    def execute(bars, params):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": params,
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(code=spec["code"], exec_globals=env, exec_locals=env, timeout=15)
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df(280)
    params = {
        "prd": 5,
        "fiboup": 0.618,
        "fibodn": 0.382,
        "errorrate": 8,
        "src_ma": "hlc3",
        "showabc": True,
        "keepabc": True,
        "showcloud": True,
        "showzigzag": True,
    }
    output = execute(bars, params)
    assert output["metadata"]["causal"] is True
    assert output["metadata"]["chart_only"] is True
    assert output["metadata"]["params"]["src_ma"] == "hlc3"
    assert len(output["plots"]) == 2
    assert len(output["signals"]) == 3
    for series in output["plots"] + output["signals"]:
        assert len(series["data"]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in series["data"])
    for key in (
        "trend",
        "abc",
        "abc_rate",
        "zigzag_direction",
        "zigzag_events",
        "abc_events",
        "upper_count",
        "lower_count",
    ):
        assert len(output["metadata"][key]) == len(bars)

    hidden = execute(
        bars,
        {
            "showabc": False,
            "showzigzag": False,
            "showcloud": False,
            "src_ma": "ohlc4",
        },
    )
    assert hidden["metadata"]["params"]["showabc"] is False
    assert hidden["metadata"]["params"]["showzigzag"] is False
    assert hidden["metadata"]["params"]["showcloud"] is False
    assert all(value is None for value in hidden["plots"][0]["data"])
    assert all(value is None for value in hidden["plots"][1]["data"])
    assert all(value == 0 for value in hidden["metadata"]["trend"])

    prefix_length = len(bars) - 37
    prefix = execute(bars.iloc[:prefix_length], params)
    for full_plot, prefix_plot in zip(output["plots"], prefix["plots"]):
        assert full_plot["data"][:prefix_length] == prefix_plot["data"]
    for full_signal, prefix_signal in zip(output["signals"], prefix["signals"]):
        assert full_signal["data"][:prefix_length] == prefix_signal["data"]
    for key in (
        "trend",
        "abc",
        "abc_rate",
        "zigzag_direction",
        "zigzag_events",
        "abc_events",
        "upper_count",
        "lower_count",
    ):
        assert output["metadata"][key][:prefix_length] == prefix["metadata"][key]

    assert all(token not in spec["code"] for token in LEGACY_EXECUTION_TOKENS)


def test_rmi_trend_sniper_is_causal_and_supports_visual_controls():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] RMI Trend Sniper")

    def execute(bars, params=None):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": params or {},
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(code=spec["code"], exec_globals=env, exec_locals=env, timeout=15)
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df(240)
    params = {"length": 20, "pmom": 66, "nmom": 30, "chart_only": True, "filleshow": True}
    output = execute(bars, params)
    assert output["metadata"]["causal"] is True
    assert output["metadata"]["chart_only"] is True
    assert output["metadata"]["filleshow"] is True
    assert len(output["plots"]) == 6
    assert len(output["signals"]) == 2
    for series in output["plots"] + output["signals"]:
        assert len(series["data"]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in series["data"])
    for key in ("rmi", "rsi_mfi", "trend", "rwma", "band"):
        assert len(output["metadata"][key]) == len(bars)

    hidden = execute(bars, {"filleshow": False})
    assert hidden["metadata"]["filleshow"] is False
    assert all(value is None for plot in hidden["plots"] for value in plot["data"])

    prefix_length = len(bars) - 27
    prefix = execute(bars.iloc[:prefix_length], params)
    for full_series, prefix_series in zip(output["plots"], prefix["plots"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]
    for full_series, prefix_series in zip(output["signals"], prefix["signals"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]
    for key in ("rmi", "rsi_mfi", "trend", "rwma", "band"):
        assert output["metadata"][key][:prefix_length] == prefix["metadata"][key]
    assert all(token not in spec["code"] for token in LEGACY_EXECUTION_TOKENS)


def test_exhaustion_levels_is_causal_and_supports_level_and_signal_switches():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] Exhaustion Levels")

    def execute(bars, params=None):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": params or {},
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(code=spec["code"], exec_globals=env, exec_locals=env, timeout=15)
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df(240)
    params = {"bars": 5, "length": 20, "exhaustion_switch": True, "level_switch": True}
    output = execute(bars, params)
    assert output["metadata"]["causal"] is True
    assert len(output["plots"]) == 2
    assert len(output["signals"]) == 2
    for series in output["plots"] + output["signals"]:
        assert len(series["data"]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in series["data"])
    for key in ("bindex", "sindex", "exhaustion"):
        assert len(output["metadata"][key]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in output["metadata"][key])

    no_signals = execute(bars, {"bars": 5, "exhaustion_switch": False, "level_switch": True})
    assert all(value is None for signal in no_signals["signals"] for value in signal["data"])
    no_levels = execute(bars, {"bars": 5, "exhaustion_switch": True, "level_switch": False})
    assert all(value is None for plot in no_levels["plots"] for value in plot["data"])

    prefix_length = len(bars) - 23
    prefix = execute(bars.iloc[:prefix_length], params)
    for full_series, prefix_series in zip(output["plots"], prefix["plots"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]
    for full_series, prefix_series in zip(output["signals"], prefix["signals"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]
    for key in ("bindex", "sindex", "exhaustion"):
        assert output["metadata"][key][:prefix_length] == prefix["metadata"][key]
    assert all(token not in spec["code"] for token in LEGACY_EXECUTION_TOKENS)


def test_renko_candles_overlay_supports_fixed_and_atr_modes_causally():
    spec = next(spec for spec in _builtin_specs() if spec["name"] == "[Default] Renko Candles Overlay")

    def execute(bars, params):
        env = {
            "df": bars.copy(),
            "pd": pd,
            "np": np,
            "params": params,
            "output": None,
            "__builtins__": build_safe_builtins(),
        }
        result = safe_exec_with_validation(code=spec["code"], exec_globals=env, exec_locals=env, timeout=15)
        assert result.get("success"), result.get("error")
        return env["output"]

    bars = _mock_df(240)
    fixed_params = {"brick_mode": "Fixed", "brick_size": 3.0}
    fixed = execute(bars, fixed_params)
    assert fixed["metadata"]["causal"] is True
    assert fixed["metadata"]["chart_only"] is True
    assert fixed["metadata"]["brick_mode"] == "Fixed"
    assert len(fixed["plots"]) == 4
    assert len(fixed["signals"]) == 2
    for series in fixed["plots"] + fixed["signals"]:
        assert len(series["data"]) == len(bars)
        assert all(value is None or np.isfinite(float(value)) for value in series["data"])
    assert all(value is None or np.isfinite(float(value)) for value in fixed["metadata"]["brick_size"])
    assert len(fixed["metadata"]["direction"]) == len(bars)
    assert any(value != 0 for value in fixed["metadata"]["direction"])

    atr = execute(bars, {"brick_mode": "ATR", "atr_period": 14, "atr_multiplier": 1.2})
    assert atr["metadata"]["brick_mode"] == "ATR"
    assert len(atr["plots"][0]["data"]) == len(bars)
    assert any(value is not None for value in atr["metadata"]["brick_size"])

    prefix_length = len(bars) - 29
    prefix = execute(bars.iloc[:prefix_length], fixed_params)
    for full_series, prefix_series in zip(fixed["plots"], prefix["plots"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]
    for full_series, prefix_series in zip(fixed["signals"], prefix["signals"]):
        assert full_series["data"][:prefix_length] == prefix_series["data"]
    for key in ("brick_size", "direction"):
        assert fixed["metadata"][key][:prefix_length] == prefix["metadata"][key]
    assert all(token not in spec["code"] for token in LEGACY_EXECUTION_TOKENS)
