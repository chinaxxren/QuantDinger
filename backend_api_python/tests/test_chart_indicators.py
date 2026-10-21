from __future__ import annotations

import math
import re
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from app.services.indicator_catalog import (
    compute_chart_indicators,
    get_chart_indicator_definition,
    get_indicator_source_code,
    list_chart_indicators,
)
from app.services.indicator_library.catalog import get_indicator_compute
from app.utils.safe_exec import safe_exec_with_validation


def _sample_bars(length: int = 80) -> pd.DataFrame:
    rows = []
    for i in range(length):
        base = 100 + i * 0.7 + math.sin(i / 4) * 2
        open_ = base - 0.4
        close = base + ((i % 5) - 2) * 0.25
        high = max(open_, close) + 1.2
        low = min(open_, close) - 1.1
        rows.append(
            {
                "time": 1_700_000_000 + i * 60,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1_000 + i * 13,
            }
        )
    return pd.DataFrame(rows)


def _assert_aligned_result(result: dict, length: int) -> None:
    assert result["success"] is True
    for plot in result.get("plots", []):
        assert len(plot["data"]) == length, plot.get("name")
        for value in plot["data"]:
            assert value is None or math.isfinite(float(value))
    for signal in result.get("signals", []):
        assert len(signal["data"]) == length, signal.get("type")
        for value in signal["data"]:
            assert value is None or math.isfinite(float(value))


def _source_indicator_ids() -> list[str]:
    return [
        item["id"]
        for item in list_chart_indicators()
        if get_chart_indicator_definition(item["id"]).compute is None and get_indicator_source_code(item["id"])
    ]


def _oscillating_bars(length: int = 360) -> pd.DataFrame:
    rng = np.random.default_rng(72)
    close = 100 + np.sin(np.arange(length) / 9) * 12 + np.cumsum(rng.normal(0, 0.7, length))
    open_price = close + rng.normal(0, 1, length)
    return pd.DataFrame(
        {
            "time": np.arange(length) * 60 + 1_700_000_000,
            "open": open_price,
            "close": close,
            "high": np.maximum(open_price, close) + rng.uniform(0.3, 2, length),
            "low": np.minimum(open_price, close) - rng.uniform(0.3, 2, length),
            "volume": rng.lognormal(7, 0.6, length),
        }
    )


def test_chart_indicator_catalog_ids_are_unique_and_match_existing_chart_buttons():
    catalog = list_chart_indicators()
    ids = [item["id"] for item in catalog]
    assert len(ids) == len(set(ids))
    assert ids == [
        "sma",
        "ema",
        "rsi",
        "macd",
        "bb",
        "atr",
        "cci",
        "williams",
        "mfi",
        "adx",
        "obv",
        "adosc",
        "ad",
        "kdj",
        "vwap",
        "sar",
        "roc",
        "mtm",
        "bias",
        "trix",
        "supertrend",
        "aroon",
        "stochastic",
        "stochastic_rsi",
        "donchian",
        "keltner",
        "ichimoku",
        "cmf",
        "cmo",
        "dema",
        "hma",
        "vortex",
        "ultimate_oscillator",
        "fisher",
        "force_index",
        "ease_of_movement",
        "chaikin_oscillator",
        "volume_oscillator",
        "pvt",
        "rvi",
        "choppiness",
        "qqe",
        "rmi_trend",
        "stc",
        "tsi",
        "connors_rsi",
        "coppock",
        "dpo",
        "mass_index",
        "ulcer_index",
        "klinger",
        "ppo",
        "volume_macd",
        "bop",
        "relative_volatility",
        "elder_ray",
        "kama",
        "vidya",
        "half_trend",
        "gaussian_trend",
        "atr_trailing_stop",
        "chandelier_exit",
        "atr_rope",
        "pmax",
        "range_filter",
        "vwap_channel",
        "turtle_channels",
        "nrtr",
        "trend_state",
        "zero_lag_trend",
        "super_bollinger",
        "alpha_trend",
        "optimized_trend_tracker",
        "std_filtered_gaussian",
        "adaptive_trend_filter",
        "vegas_supertrend",
        "dsav",
        "lowess",
        "price_radio",
        "adaptive_trend_trail",
        "spma_trend_nal",
        "powertrend_volume_range_filter",
        "g_channels",
        "wavetrend_oscillator",
        "nadaraya_watson_envelope",
        "dynamic_linear_regression_channel",
        "ut_bot_alerts",
        "twin_range_filter",
        "pivot_point_supertrend",
        "delta_rsi_oscillator",
        "range_filter_signals",
        "know_sure_thing",
        "macd_leader",
        "envelope_rsi_signals",
        "follow_line_indicator",
        "exhaustion_levels",
        "hema_trend_levels",
        "market_structure_oscillator",
        "adaptive_supertrend",
        "elder_impulse_system",
        "swing_failure_pattern",
        "breaks_and_retests",
        "false_breakout",
        "multi_kernel_regression",
        "smart_money_breakouts",
        "swing_highs_lows_candle_patterns",
        "trendlines_with_breaks",
        "rsi_divergence_indicator",
        "two_b_reversal_pattern",
        "alphatrend_screener",
        "macd_bollinger_bands",
        "rmi_trend_sniper",
        "smart_money_breakout_signals",
        "auto_chart_patterns",
        "divergence_many_indicators",
        "trading_abc",
        "pmax_on_rsi_t3",
        "volume_weighted_macd",
        "itg_scalper",
        "machine_learning_rsi",
        "ghost_tangent_crossings",
        "volume_supertrend_ai",
        "chip_distribution",
        "z_score",
        "pvo",
        "nvi",
    ]
    assert all(item["type"] == "backend" for item in catalog)
    assert catalog[15]["defaultParams"] == {"start": 2, "step": 2, "max": 20}
    assert catalog[15]["singleInstance"] is True


def test_each_backend_indicator_implementation_is_file_backed():
    catalog = list_chart_indicators()
    assert catalog

    for item in catalog:
        indicator_id = item["id"]
        definition = get_chart_indicator_definition(indicator_id)
        assert definition is not None
        implementation = get_indicator_compute(indicator_id)
        assert callable(implementation), indicator_id

        if get_chart_indicator_definition(indicator_id).compute is None:
            assert get_indicator_source_code(indicator_id), indicator_id
            continue

        assert definition.compute is not None, indicator_id
        assert implementation is definition.compute, indicator_id
        assert definition.compute.__module__ == (f"app.services.indicator_library.indicators.{indicator_id}"), (
            indicator_id
        )


def test_catalog_schema_covers_every_default_parameter():
    for item in list_chart_indicators():
        schema_keys = {field["key"] for field in item["paramSchema"]}
        assert set(item["defaultParams"]).issubset(schema_keys), item["id"]
        for field in item["paramSchema"]:
            assert field.get("defaultValue") == item["defaultParams"][field["key"]], (item["id"], field["key"])
            assert field.get("type", "number") in {"number", "bool", "boolean", "string", "str", "color"}
            if field.get("type", "number") == "number":
                assert field.get("min") is not None
                assert field.get("max") is not None
                assert field.get("step") is not None
                default_value = item["defaultParams"][field["key"]]
                if isinstance(default_value, float) and not default_value.is_integer():
                    assert field.get("precision", 0) >= max(0, -Decimal(str(default_value)).as_tuple().exponent), (
                        item["id"],
                        field["key"],
                    )


def test_file_backed_chart_indicators_match_their_independent_source_outputs():
    bars = _oscillating_bars()
    catalog = {item["id"]: item for item in list_chart_indicators()}
    source_ids = _source_indicator_ids()
    requests = [{"id": indicator_id} for indicator_id in source_ids]
    actual = {item["id"]: item for item in compute_chart_indicators(bars, requests)}

    for indicator_id in source_ids:
        env = {
            "df": bars.copy(),
            "params": catalog[indicator_id]["defaultParams"].copy(),
            "pd": pd,
            "np": np,
            "output": None,
        }
        source = get_indicator_source_code(indicator_id)
        assert source, indicator_id
        executed = safe_exec_with_validation(source, env, env, timeout=15)
        assert executed["success"], (indicator_id, executed.get("error"))
        expected = env["output"]
        result = actual[indicator_id]
        assert result["success"] is True, (indicator_id, result)
        assert len(result["plots"]) == len(expected["plots"]), indicator_id
        assert len(result["signals"]) == len(expected.get("signals") or []), indicator_id
        for actual_plot, expected_plot in zip(result["plots"], expected["plots"]):
            assert actual_plot["data"] == [
                None if value is None or not math.isfinite(float(value)) else float(value)
                for value in expected_plot["data"]
            ], (indicator_id, expected_plot.get("name"))
        for actual_signal, expected_signal in zip(result["signals"], expected.get("signals") or []):
            assert actual_signal["data"] == [
                None if value is None or not math.isfinite(float(value)) else float(value)
                for value in expected_signal["data"]
            ], (indicator_id, expected_signal.get("type"))


def test_file_backed_indicator_catalog_exposes_every_source_parameter():
    catalog = {item["id"]: item for item in list_chart_indicators()}
    for indicator_id in _source_indicator_ids():
        source = get_indicator_source_code(indicator_id)
        assert source, indicator_id
        source_parameters = set(re.findall(r"^# @param (\w+)", source, re.MULTILINE))
        catalog_parameters = set(catalog[indicator_id]["defaultParams"])
        assert source_parameters == catalog_parameters, indicator_id
        assert all(field.get("defaultValue") is not None for field in catalog[indicator_id]["paramSchema"]), (
            indicator_id
        )


def test_file_backed_indicators_keep_history_when_bars_are_appended():
    bars = _oscillating_bars()
    requests = [{"id": indicator_id} for indicator_id in _source_indicator_ids()]
    requests += [
        {"id": "dsav", "params": {"use_adapt": True}},
        {"id": "g_channels", "params": {"signal_mode": "channel"}},
        {"id": "spma_trend_nal", "params": {"vol_method": "MedianAD", "use_asym_bands": True}},
        {"id": "macd_leader", "params": {"ema_seed": "first", "show_macd": True}},
    ]
    prefix_length = len(bars) - 29
    full = compute_chart_indicators(bars, requests)
    prefix = compute_chart_indicators(bars.iloc[:prefix_length], requests)
    for full_result, prefix_result in zip(full, prefix):
        assert full_result["success"] and prefix_result["success"], full_result["id"]
        for full_signal, prefix_signal in zip(full_result["signals"], prefix_result["signals"]):
            assert full_signal["data"][:prefix_length] == prefix_signal["data"], full_result["id"]
        for full_plot, prefix_plot in zip(full_result["plots"], prefix_result["plots"]):
            # Follow Line extends a color segment to the preceding bar on a
            # reversal; its last rendered endpoint can change after append.
            compared_length = prefix_length - 1 if full_result["id"] == "follow_line_indicator" else prefix_length
            assert full_plot["data"][:compared_length] == prefix_plot["data"][:compared_length], full_result["id"]


def test_source_parameter_types_and_ordering_are_normalized_per_request():
    results = compute_chart_indicators(
        _oscillating_bars(),
        [
            {
                "id": "follow_line_indicator",
                "params": {"hide_labels": "true", "use_atr_filter": "false", "bb_period": "21"},
            },
            {"id": "macd_leader", "params": {"short_length": 30, "long_length": 20}},
            {"id": "know_sure_thing", "params": {"roc1_period": True}},
            {"id": "hema_trend_levels", "params": {"atr_multiplier": float("nan")}},
            {"id": "follow_line_indicator", "params": {"hide_labels": "invalid"}},
            {"id": "exhaustion_levels", "params": {"thickness": 4}},
        ],
    )
    assert results[0]["success"]
    assert results[0]["params"]["hide_labels"] is True
    assert results[0]["params"]["use_atr_filter"] is False
    assert results[0]["params"]["bb_period"] == 21
    assert all(value is None for signal in results[0]["signals"] for value in signal["data"])
    assert all(not result["success"] for result in results[1:5])
    assert results[5]["success"]
    assert all(plot["lineWidth"] == 4 for plot in results[5]["plots"])


def test_file_backed_indicator_options_and_visual_toggles_are_validated_and_applied():
    bars = _sample_bars(180)
    results = compute_chart_indicators(
        bars,
        [
            {"id": "spma_trend_nal", "params": {"vol_method": "MedianAD"}},
            {"id": "macd_leader", "params": {"show_macd": True, "show_macdsignal": True}},
            {"id": "envelope_rsi_signals", "params": {"show_envelope": False}},
            {"id": "envelope_rsi_signals", "params": {"show_envelope": True}},
            {"id": "market_structure_oscillator", "params": {"show_signal": False}},
            {"id": "g_channels", "params": {"signal_mode": "not-a-mode"}},
            {"id": "know_sure_thing", "params": {"roc1_period": 10.5}},
        ],
    )
    assert all(result["success"] for result in results[:5])
    assert results[0]["params"]["vol_method"] == "MedianAD"
    assert all(value is not None for value in results[1]["plots"][1]["data"][-5:])
    assert all(value is not None for value in results[1]["plots"][2]["data"][-5:])
    assert all(value is None for plot in results[2]["plots"][2:] for value in plot["data"])
    assert results[2]["signals"] == results[3]["signals"]
    assert all(value is None for value in results[4]["plots"][1]["data"])
    assert results[5]["success"] is False
    assert results[6]["success"] is False


def test_all_chart_indicators_return_bars_aligned_series():
    bars = _sample_bars()
    requests = [{"id": item["id"], "params": item.get("defaultParams") or {}} for item in list_chart_indicators()]
    results = compute_chart_indicators(bars, requests)
    assert len(results) == len(requests)
    for result in results:
        _assert_aligned_result(result, len(bars))


def test_chart_indicator_history_is_stable_when_future_bars_are_appended():
    bars = _oscillating_bars()
    prefix_length = len(bars) - 29
    requests = [{"id": item["id"]} for item in list_chart_indicators()]
    full_results = compute_chart_indicators(bars, requests)
    prefix_results = compute_chart_indicators(bars.iloc[:prefix_length], requests)

    for full, prefix in zip(full_results, prefix_results):
        assert full["success"] and prefix["success"], full["id"]
        for field in ("plots", "signals"):
            assert len(full.get(field, [])) == len(prefix.get(field, [])), full["id"]
            for full_series, prefix_series in zip(full.get(field, []), prefix.get(field, [])):
                # Follow Line may extend a reversal segment to the preceding bar.
                stable_length = (
                    prefix_length - 1 if full["id"] == "follow_line_indicator" and field == "plots" else prefix_length
                )
                assert full_series["data"][:stable_length] == prefix_series["data"][:stable_length], (
                    full["id"],
                    full_series.get("name") or full_series.get("type"),
                )


def test_core_indicators_match_hand_calculated_reference_values():
    close = [10, 11, 12, 11, 13, 14]
    bars = pd.DataFrame(
        {
            "time": np.arange(len(close)),
            "open": close,
            "high": [value + 1 for value in close],
            "low": [value - 1 for value in close],
            "close": close,
            "volume": [100] * len(close),
        }
    )
    results = {
        result["id"]: result
        for result in compute_chart_indicators(
            bars,
            [
                {"id": "sma", "params": {"length": 3}},
                {"id": "ema", "params": {"length": 3}},
                {"id": "rsi", "params": {"length": 3}},
                {"id": "atr", "params": {"period": 3}},
            ],
        )
    }

    assert results["sma"]["plots"][0]["data"] == pytest.approx(
        [None, None, 11, 11 + 1 / 3, 12, 12 + 2 / 3], nan_ok=True
    )
    assert results["ema"]["plots"][0]["data"] == pytest.approx([None, None, 11, 11, 12, 13], nan_ok=True)
    assert results["rsi"]["plots"][0]["data"] == pytest.approx(
        [None, None, None, 200 / 3, 250 / 3, 100 * 29 / 33], nan_ok=True
    )
    assert results["atr"]["plots"][0]["data"] == pytest.approx([None, None, 2, 2, 7 / 3, 20 / 9], nan_ok=True)


def test_stochastic_rsi_waits_for_complete_rsi_and_stochastic_windows():
    close = [10, 11, 12, 11, 13, 14, 15, 14, 16, 15, 17]
    bars = pd.DataFrame(
        {
            "time": np.arange(len(close)),
            "open": close,
            "high": [value + 1 for value in close],
            "low": [value - 1 for value in close],
            "close": close,
            "volume": [100] * len(close),
        }
    )

    result = compute_chart_indicators(
        bars,
        [
            {
                "id": "stochastic_rsi",
                "params": {"rsi_period": 3, "stochastic_period": 3, "k_period": 2, "d_period": 2},
            }
        ],
    )[0]
    percent_k, percent_d = [plot["data"] for plot in result["plots"]]

    assert percent_k[:6] == [None] * 6
    assert percent_k[6] is not None
    assert percent_d[:7] == [None] * 7
    assert percent_d[7] is not None


def test_borrowed_indicator_reference_values_and_warmup_are_correct():
    close = [10, 12, 14, 16, 18, 20]
    bars = pd.DataFrame(
        {
            "time": np.arange(len(close)),
            "open": close,
            "high": [value + 1 for value in close],
            "low": [value - 1 for value in close],
            "close": close,
            "volume": [10, 20, 10, 20, 10, 20],
        }
    )
    results = {
        result["id"]: result
        for result in compute_chart_indicators(
            bars,
            [
                {"id": "z_score", "params": {"period": 3}},
                {"id": "pvo", "params": {"short_period": 2, "long_period": 3, "signal_period": 2}},
                {"id": "nvi"},
            ],
        )
    }

    z_score = results["z_score"]["plots"][0]["data"]
    assert z_score[:2] == [None, None]
    assert z_score[2:] == pytest.approx([np.sqrt(1.5), np.sqrt(1.5), np.sqrt(1.5), np.sqrt(1.5)])

    pvo, signal, histogram = [plot["data"] for plot in results["pvo"]["plots"]]
    assert pvo[:2] == [None, None]
    assert pvo[2:] == pytest.approx([-12.5, 10 / 3, -125 / 18, 130 / 27])
    assert signal[:3] == [None, None, None]
    assert signal[3:] == pytest.approx([-55 / 12, -665 / 108, 125 / 108])
    assert histogram[:3] == [None, None, None]
    assert histogram[3:] == pytest.approx([95 / 12, -85 / 108, 1975 / 540])

    nvi = results["nvi"]["plots"][0]["data"]
    assert nvi[0] is None
    assert nvi[1:] == pytest.approx([1000, 3500 / 3, 3500 / 3, 2625 / 2, 2625 / 2])


def test_percentage_volume_oscillator_rejects_invalid_period_ordering():
    result = compute_chart_indicators(
        _sample_bars(),
        [
            {
                "id": "pvo",
                "params": {"short_period": 26, "long_period": 12},
            }
        ],
    )[0]
    assert result["success"] is False
    assert result["error"] == "invalid parameter: long_period"


def test_multi_plot_indicator_shapes_are_stable():
    bars = _sample_bars()
    by_id = {
        item["id"]: item
        for item in compute_chart_indicators(
            bars,
            [
                {"id": "macd"},
                {"id": "bb"},
                {"id": "kdj"},
                {"id": "supertrend"},
            ],
        )
    }
    assert [plot["name"] for plot in by_id["macd"]["plots"]] == ["macd", "signal", "histogram"]
    assert [plot["name"] for plot in by_id["bb"]["plots"]] == ["upper", "middle", "lower"]
    assert [plot["name"] for plot in by_id["kdj"]["plots"]] == ["k", "d", "j"]
    assert [plot["name"] for plot in by_id["supertrend"]["plots"]] == ["supertrend_up", "supertrend_down"]
    assert [signal["type"] for signal in by_id["supertrend"]["signals"]] == ["buy", "sell"]
    assert all(plot.get("overlay") for plot in by_id["bb"]["plots"])
    assert all(plot.get("overlay") for plot in by_id["supertrend"]["plots"])


def test_extended_indicator_shapes_and_overlay_contracts():
    bars = _sample_bars()
    results = {
        item["id"]: item
        for item in compute_chart_indicators(
            bars,
            [
                {"id": "aroon"},
                {"id": "stochastic"},
                {"id": "stochastic_rsi"},
                {"id": "donchian"},
                {"id": "keltner"},
                {"id": "ichimoku"},
                {"id": "cmf"},
                {"id": "cmo"},
                {"id": "dema"},
                {"id": "hma"},
            ],
        )
    }
    for result in results.values():
        _assert_aligned_result(result, len(bars))
    assert [plot["name"] for plot in results["aroon"]["plots"]] == ["aroon_up", "aroon_down", "aroon"]
    assert len(results["stochastic"]["plots"]) == 2
    assert len(results["stochastic_rsi"]["plots"]) == 2
    assert all(plot["overlay"] for plot in results["donchian"]["plots"])
    assert all(plot["overlay"] for plot in results["keltner"]["plots"])
    assert all(plot["overlay"] for plot in results["ichimoku"]["plots"])
    assert results["dema"]["plots"][0]["overlay"] is True
    assert results["hma"]["plots"][0]["overlay"] is True


def test_extended_indicator_parameter_validation_is_per_request():
    bars = _sample_bars()
    results = compute_chart_indicators(
        bars,
        [
            {"id": "stochastic", "params": {"length": 2, "smooth_k": 3, "smooth_d": 3}},
            {"id": "keltner", "params": {"multiplier": 20}},
            {"id": "hma", "params": {"period": 12}},
        ],
    )
    assert results[0]["success"] is False
    assert results[1]["success"] is False
    assert results[2]["success"] is True


def test_volume_and_momentum_indicator_results_are_aligned_and_stable():
    bars = _sample_bars()
    ids = [
        "vortex",
        "ultimate_oscillator",
        "fisher",
        "force_index",
        "ease_of_movement",
        "chaikin_oscillator",
        "volume_oscillator",
        "pvt",
        "rvi",
        "choppiness",
    ]
    results = {item["id"]: item for item in compute_chart_indicators(bars, [{"id": item} for item in ids])}
    assert set(results) == set(ids)
    for result in results.values():
        _assert_aligned_result(result, len(bars))
    assert [plot["name"] for plot in results["vortex"]["plots"]] == ["vortex_positive", "vortex_negative"]
    assert len(results["ultimate_oscillator"]["plots"]) == 1
    assert [plot["name"] for plot in results["fisher"]["plots"]] == ["fisher", "fisher_signal"]
    assert [plot["name"] for plot in results["volume_oscillator"]["plots"]] == [
        "volume_oscillator",
        "volume_oscillator_signal",
    ]
    assert [plot["name"] for plot in results["pvt"]["plots"]] == ["pvt", "pvt_signal"]
    assert [plot["name"] for plot in results["rvi"]["plots"]] == ["rvi", "rvi_signal"]


def test_composite_indicator_parameters_reject_invalid_ordering():
    bars = _sample_bars()
    results = compute_chart_indicators(
        bars,
        [
            {"id": "ultimate_oscillator", "params": {"short_period": 14, "medium_period": 14, "long_period": 28}},
            {"id": "chaikin_oscillator", "params": {"fast_period": 12, "slow_period": 10}},
            {"id": "volume_oscillator", "params": {"fast_period": 25, "slow_period": 20}},
        ],
    )
    assert all(item["success"] is False for item in results)


def test_next_momentum_indicator_batch_is_aligned():
    bars = _sample_bars(180)
    ids = ["qqe", "rmi_trend", "stc", "tsi", "connors_rsi", "coppock", "dpo", "mass_index", "ulcer_index", "klinger"]
    results = {item["id"]: item for item in compute_chart_indicators(bars, [{"id": item} for item in ids])}
    for result in results.values():
        _assert_aligned_result(result, len(bars))
    assert len(results["qqe"]["plots"]) == 2
    assert len(results["rmi_trend"]["plots"]) == 6
    assert len(results["stc"]["plots"]) == 1
    assert len(results["tsi"]["plots"]) == 2
    assert len(results["klinger"]["plots"]) == 2


def test_trend_and_volume_indicator_batch_is_aligned():
    bars = _sample_bars(180)
    ids = [
        "ppo",
        "volume_macd",
        "bop",
        "relative_volatility",
        "elder_ray",
        "kama",
        "vidya",
        "half_trend",
        "gaussian_trend",
        "atr_trailing_stop",
    ]
    results = {item["id"]: item for item in compute_chart_indicators(bars, [{"id": item} for item in ids])}
    for result in results.values():
        _assert_aligned_result(result, len(bars))
    assert len(results["ppo"]["plots"]) == 3
    assert len(results["volume_macd"]["plots"]) == 3
    assert all(plot["overlay"] for plot in results["kama"]["plots"])
    assert all(plot["overlay"] for plot in results["vidya"]["plots"])
    assert all(plot["overlay"] for plot in results["half_trend"]["plots"])
    assert all(plot["overlay"] for plot in results["gaussian_trend"]["plots"])
    assert all(plot["overlay"] for plot in results["atr_trailing_stop"]["plots"])
    assert len(results["half_trend"]["signals"]) == 2
    assert len(results["atr_trailing_stop"]["signals"]) == 2


def test_catalog_supports_boolean_and_enum_parameters():
    catalog = {item["id"]: item for item in list_chart_indicators()}
    histogram = next(field for field in catalog["volume_macd"]["paramSchema"] if field["key"] == "histogram")
    source = next(field for field in catalog["atr_trailing_stop"]["paramSchema"] if field["key"] == "source")
    assert histogram["type"] == "bool" and histogram["defaultValue"] is True
    assert source["type"] == "string" and source["options"] == ["close", "hl2"]


def test_latest_file_backed_indicators_are_aligned_and_preserve_plot_line_widths():
    bars = _sample_bars(180)
    ids = [
        "adaptive_supertrend",
        "elder_impulse_system",
        "swing_failure_pattern",
        "breaks_and_retests",
        "false_breakout",
        "multi_kernel_regression",
        "smart_money_breakouts",
    ]
    results = {item["id"]: item for item in compute_chart_indicators(bars, [{"id": item} for item in ids])}
    assert set(results) == set(ids)
    for result in results.values():
        _assert_aligned_result(result, len(bars))

    regression_plots = results["multi_kernel_regression"]["plots"]
    assert regression_plots
    assert any("lineWidth" in plot for plot in regression_plots)
    assert all(plot["lineWidth"] == 3 for plot in regression_plots if "lineWidth" in plot)


def test_latest_source_parameters_validate_colors_enums_and_integer_periods():
    bars = _sample_bars(80)
    results = compute_chart_indicators(
        bars,
        [
            {"id": "swing_failure_pattern", "params": {"bull_color": "#12ABef", "validation": "None"}},
            {"id": "smart_money_breakouts", "params": {"line_style": "Dotted"}},
            {"id": "swing_failure_pattern", "params": {"bull_color": "red"}},
            {"id": "smart_money_breakouts", "params": {"line_style": "dashes"}},
            {"id": "multi_kernel_regression", "params": {"bandwidth": 14.5}},
        ],
    )
    assert results[0]["success"] and results[0]["params"]["bull_color"] == "#12ABef"
    assert results[1]["success"] and results[1]["params"]["line_style"] == "Dotted"
    assert all(not result["success"] for result in results[2:])


def test_next_pattern_and_divergence_indicators_are_aligned():
    bars = _oscillating_bars(240)
    ids = [
        "swing_highs_lows_candle_patterns",
        "trendlines_with_breaks",
        "rsi_divergence_indicator",
        "two_b_reversal_pattern",
    ]
    results = {item["id"]: item for item in compute_chart_indicators(bars, [{"id": item} for item in ids])}
    assert set(results) == set(ids)
    for result in results.values():
        _assert_aligned_result(result, len(bars))
        assert result["success"] is True


def test_next_trend_and_oscillator_indicators_are_aligned_and_settings_apply():
    bars = _oscillating_bars(260)
    ids = ["alphatrend_screener", "macd_bollinger_bands", "rmi_trend_sniper", "smart_money_breakout_signals"]
    results = {
        item["id"]: item
        for item in compute_chart_indicators(
            bars,
            [
                {"id": "alphatrend_screener", "params": {"show_signal": False}},
                {"id": "macd_bollinger_bands"},
                {"id": "rmi_trend_sniper", "params": {"filleshow": False}},
                {"id": "smart_money_breakout_signals", "params": {"show_levels": False}},
            ],
        )
    }
    assert set(results) == set(ids)
    for result in results.values():
        _assert_aligned_result(result, len(bars))
        assert result["success"] is True
    assert all(not plot["overlay"] for plot in results["macd_bollinger_bands"]["plots"])
    assert all(value is None for value in results["alphatrend_screener"]["plots"][1]["data"])
    assert all(value is None for plot in results["rmi_trend_sniper"]["plots"] for value in plot["data"])
    assert all(value is None for plot in results["smart_money_breakout_signals"]["plots"] for value in plot["data"])


def test_macd_bollinger_period_order_is_validated():
    result = compute_chart_indicators(
        _sample_bars(),
        [
            {"id": "macd_bollinger_bands", "params": {"fast_length": 30, "slow_length": 20}},
        ],
    )[0]
    assert result["success"] is False


def test_pattern_and_multi_divergence_sources_are_aligned_and_settings_apply():
    bars = _oscillating_bars(260)
    results = {
        item["id"]: item
        for item in compute_chart_indicators(
            bars,
            [
                {
                    "id": "auto_chart_patterns",
                    "params": {"allow_channels": False, "allow_wedges": False, "allow_triangles": False},
                },
                {"id": "divergence_many_indicators", "params": {"calc_macd": False, "calc_rsi": False}},
                {"id": "trading_abc", "params": {"showabc": False, "showzigzag": False}},
            ],
        )
    }
    assert set(results) == {"auto_chart_patterns", "divergence_many_indicators", "trading_abc"}
    for result in results.values():
        _assert_aligned_result(result, len(bars))
        assert result["success"] is True
    assert all(value is None for plot in results["auto_chart_patterns"]["plots"] for value in plot["data"])
    assert all(value is None for plot in results["trading_abc"]["plots"] for value in plot["data"])


def test_pattern_and_abc_parameter_ordering_is_validated():
    results = compute_chart_indicators(
        _sample_bars(),
        [
            {"id": "auto_chart_patterns", "params": {"min_pivots": 6, "max_pivots": 4}},
            {"id": "trading_abc", "params": {"fibodn": 0.8, "fiboup": 0.6}},
        ],
    )
    assert all(result["success"] is False for result in results)


def test_pmax_rsi_and_volume_weighted_macd_are_aligned_and_settings_apply():
    bars = _oscillating_bars(240)
    results = {
        item["id"]: item
        for item in compute_chart_indicators(
            bars,
            [
                {
                    "id": "pmax_on_rsi_t3",
                    "params": {"show_rsi": False, "show_support": False, "show_signals": False, "highlighting": False},
                },
                {"id": "volume_weighted_macd", "params": {"histogram": False}},
            ],
        )
    }
    assert set(results) == {"pmax_on_rsi_t3", "volume_weighted_macd"}
    for result in results.values():
        _assert_aligned_result(result, len(bars))
        assert result["success"] is True
    pmax_plots = {plot["name"]: plot for plot in results["pmax_on_rsi_t3"]["plots"]}
    assert all(
        value is None
        for name in (
            "RSI",
            "T3 Support",
            "Bull RSI Highlight",
            "Bull PMax Highlight",
            "Bear RSI Highlight",
            "Bear PMax Highlight",
        )
        for value in pmax_plots[name]["data"]
    )
    assert all(value is None for signal in results["pmax_on_rsi_t3"]["signals"] for value in signal["data"])
    assert all(
        value is None
        for plot in results["volume_weighted_macd"]["plots"]
        if "histogram" in plot["name"].lower()
        for value in plot["data"]
    )


def test_itg_scalper_and_machine_learning_rsi_are_aligned_and_settings_apply():
    bars = _oscillating_bars(260)
    results = {
        item["id"]: item
        for item in compute_chart_indicators(
            bars,
            [
                {"id": "itg_scalper", "params": {"show_bands": False}},
                {
                    "id": "machine_learning_rsi",
                    "params": {"use_knn": False, "color_mode": "Impulse", "color_scheme": "Monochrome"},
                },
            ],
        )
    }
    assert set(results) == {"itg_scalper", "machine_learning_rsi"}
    for result in results.values():
        _assert_aligned_result(result, len(bars))
        assert result["success"] is True
    assert all(
        value is None
        for plot in results["itg_scalper"]["plots"]
        if "scalp" in plot["name"].lower()
        for value in plot["data"]
    )
    assert results["machine_learning_rsi"]["params"]["use_knn"] is False
    assert results["machine_learning_rsi"]["params"]["color_mode"] == "Impulse"


def test_machine_learning_rsi_thresholds_and_modes_are_validated():
    results = compute_chart_indicators(
        _sample_bars(),
        [
            {"id": "machine_learning_rsi", "params": {"oversold": 75, "overbought": 70}},
            {"id": "machine_learning_rsi", "params": {"ma_type": "NOT-A-MA"}},
            {"id": "itg_scalper", "params": {"fast_length": 20, "slow_length": 10}},
        ],
    )
    assert all(result["success"] is False for result in results)


def test_ghost_tangent_crossings_are_aligned_and_expose_visual_modes():
    bars = _oscillating_bars(240)
    result = compute_chart_indicators(
        bars,
        [
            {
                "id": "ghost_tangent_crossings",
                "params": {"pivot_type": "Body", "equipoint_style": "Horizontal", "show_break": False},
            }
        ],
    )[0]
    _assert_aligned_result(result, len(bars))
    assert result["success"] is True
    assert result["params"]["pivot_type"] == "Body"
    assert result["params"]["equipoint_style"] == "Horizontal"
    assert all(value is None for signal in result["signals"] for value in signal["data"])
    invalid = compute_chart_indicators(bars, [{"id": "ghost_tangent_crossings", "params": {"pivot_type": "unknown"}}])[
        0
    ]
    assert invalid["success"] is False


def test_volume_supertrend_ai_is_aligned_and_visual_switches_apply():
    bars = _oscillating_bars(240)
    result = compute_chart_indicators(
        bars,
        [
            {
                "id": "volume_supertrend_ai",
                "params": {"ai_signals": False, "show_cloud": False, "cloud_layers": 1},
            }
        ],
    )[0]
    _assert_aligned_result(result, len(bars))
    assert result["success"] is True
    assert all(value is None for plot in result["plots"][3:] for value in plot["data"])
    assert all(value is None for signal in result["signals"][2:] for value in signal["data"])


def test_trend_channel_indicator_batch_is_aligned():
    bars = _sample_bars(220)
    ids = [
        "chandelier_exit",
        "atr_rope",
        "pmax",
        "range_filter",
        "vwap_channel",
        "turtle_channels",
        "nrtr",
        "trend_state",
        "zero_lag_trend",
        "super_bollinger",
    ]
    results = {item["id"]: item for item in compute_chart_indicators(bars, [{"id": item} for item in ids])}
    for result in results.values():
        _assert_aligned_result(result, len(bars))
    assert all(plot["overlay"] for plot in results["chandelier_exit"]["plots"])
    assert len(results["pmax"]["plots"]) == 3
    assert len(results["range_filter"]["plots"]) == 3
    assert len(results["turtle_channels"]["plots"]) == 4
    assert len(results["zero_lag_trend"]["plots"]) == 4
    assert len(results["super_bollinger"]["plots"]) == 3


def test_trend_channel_enum_parameters_are_exposed():
    catalog = {item["id"]: item for item in list_chart_indicators()}
    source = next(field for field in catalog["trend_state"]["paramSchema"] if field["key"] == "src_type")
    signal = next(field for field in catalog["super_bollinger"]["paramSchema"] if field["key"] == "signal")
    assert source["options"] == ["close", "hl2", "hlc3", "ohlc4"]
    assert signal["options"] == ["Signal", "ZigZag"]


def test_chip_distribution_splits_volume_across_price_rows_and_keeps_totals():
    bars = _sample_bars(80)
    result = compute_chart_indicators(
        bars,
        [
            {
                "id": "chip_distribution",
                "params": {"lookback": 40, "rows": 24, "value_area_percent": 70},
            }
        ],
    )[0]

    assert result["success"] is True
    assert result["plots"] == []
    profile = result["profile"]
    assert profile["windowBars"] == 40
    assert len(profile["rows"]) == 24
    assert math.isclose(profile["buyVolume"] + profile["sellVolume"], profile["totalVolume"], rel_tol=1e-12)
    assert math.isclose(sum(row["totalVolume"] for row in profile["rows"]), profile["totalVolume"], rel_tol=1e-12)
    assert math.isclose(sum(row["buyVolume"] for row in profile["rows"]), profile["buyVolume"], rel_tol=1e-12)
    assert math.isclose(sum(row["sellVolume"] for row in profile["rows"]), profile["sellVolume"], rel_tol=1e-12)
    assert profile["method"] == "candle_direction_estimate"
    assert profile["val"] <= profile["poc"] <= profile["vah"]
    assert profile["valueAreaPercent"] == 70
    assert 0 <= profile["estimatedProfitableRatio"] <= 1
    assert all(math.isfinite(value) for row in profile["rows"] for value in row.values())


def test_chip_distribution_classifies_up_down_and_doji_bars_and_limits_lookback():
    bars = pd.DataFrame(
        [
            {"time": i, "open": 100, "high": 105, "low": 95, "close": close, "volume": volume}
            for i, (close, volume) in enumerate(
                [
                    (101, 10),
                    (99, 20),
                    (100, 30),
                    (102, 40),
                    (98, 50),
                    (100, 60),
                    (103, 70),
                    (97, 80),
                    (100, 90),
                    (101, 100),
                    (99, 110),
                    (100, 120),
                ]
            )
        ]
    )
    result = compute_chart_indicators(
        bars,
        [
            {
                "id": "chip_distribution",
                "params": {"lookback": 10, "rows": 8},
            }
        ],
    )[0]

    profile = result["profile"]
    expected_volume = float(bars.tail(10)["volume"].sum())
    assert result["success"] is True
    assert profile["windowBars"] == 10
    assert math.isclose(profile["totalVolume"], expected_volume, rel_tol=1e-12)
    assert profile["buyVolume"] > 0
    assert profile["sellVolume"] > 0
    assert math.isclose(profile["buyVolume"] + profile["sellVolume"], expected_volume, rel_tol=1e-12)


def test_chip_distribution_handles_flat_prices_and_rejects_invalid_parameters():
    bars = pd.DataFrame(
        {
            "time": np.arange(12),
            "open": np.full(12, 5.0),
            "high": np.full(12, 5.0),
            "low": np.full(12, 5.0),
            "close": np.full(12, 5.0),
            "volume": np.ones(12),
        }
    )
    flat_result = compute_chart_indicators(bars, [{"id": "chip_distribution"}])[0]
    assert flat_result["success"] is True
    assert math.isclose(flat_result["profile"]["buyVolume"], 6.0)
    assert math.isclose(flat_result["profile"]["sellVolume"], 6.0)
    assert all(math.isfinite(row["price"]) for row in flat_result["profile"]["rows"])

    invalid_results = compute_chart_indicators(
        bars,
        [
            {"id": "chip_distribution", "params": {"rows": 7}},
            {"id": "chip_distribution", "params": {"value_area_percent": 100}},
        ],
    )
    assert all(result["success"] is False for result in invalid_results)


def test_next_trend_filter_indicator_batch_is_aligned():
    bars = _sample_bars(240)
    ids = [
        "alpha_trend",
        "optimized_trend_tracker",
        "std_filtered_gaussian",
        "adaptive_trend_filter",
        "vegas_supertrend",
        "dsav",
        "lowess",
        "price_radio",
        "adaptive_trend_trail",
        "spma_trend_nal",
    ]
    results = {item["id"]: item for item in compute_chart_indicators(bars, [{"id": item} for item in ids])}
    assert set(results) == set(ids)
    for result in results.values():
        _assert_aligned_result(result, len(bars))
        assert result["success"] is True
    assert results["alpha_trend"]["plots"][0]["overlay"] is True
    assert len(results["optimized_trend_tracker"]["plots"]) == 3
    assert len(results["vegas_supertrend"]["plots"]) == 4
    assert len(results["adaptive_trend_filter"]["plots"]) == 2
    assert len(results["spma_trend_nal"]["plots"]) == 4


def test_next_indicator_parameter_schemas_expose_defaults_and_modes():
    catalog = {item["id"]: item for item in list_chart_indicators()}
    assert catalog["alpha_trend"]["defaultParams"]["confirmation_lag"] == 2
    assert next(field for field in catalog["adaptive_trend_trail"]["paramSchema"] if field["key"] == "overlay_mode")[
        "options"
    ] == ["Trail", "Bands", "None"]
    assert next(field for field in catalog["spma_trend_nal"]["paramSchema"] if field["key"] == "source")["options"] == [
        "close",
        "hl2",
        "hlc3",
        "ohlc4",
    ]


def test_next_channel_and_oscillator_indicator_batch_is_aligned():
    bars = _sample_bars(260)
    ids = [
        "powertrend_volume_range_filter",
        "g_channels",
        "wavetrend_oscillator",
        "nadaraya_watson_envelope",
        "dynamic_linear_regression_channel",
        "ut_bot_alerts",
        "twin_range_filter",
        "pivot_point_supertrend",
        "delta_rsi_oscillator",
        "range_filter_signals",
    ]
    results = {item["id"]: item for item in compute_chart_indicators(bars, [{"id": item} for item in ids])}
    for result in results.values():
        _assert_aligned_result(result, len(bars))
        assert result["success"] is True
    assert len(results["powertrend_volume_range_filter"]["plots"]) == 4
    assert all(plot["overlay"] for plot in results["g_channels"]["plots"])
    assert all(not plot["overlay"] for plot in results["wavetrend_oscillator"]["plots"])
    assert len(results["delta_rsi_oscillator"]["plots"]) == 3
    assert len(results["range_filter_signals"]["plots"]) == 5


def test_momentum_and_trend_indicator_batch_is_aligned():
    bars = _sample_bars(280)
    ids = [
        "know_sure_thing",
        "macd_leader",
        "envelope_rsi_signals",
        "follow_line_indicator",
        "exhaustion_levels",
        "hema_trend_levels",
        "market_structure_oscillator",
    ]
    results = {item["id"]: item for item in compute_chart_indicators(bars, [{"id": item} for item in ids])}
    for result in results.values():
        _assert_aligned_result(result, len(bars))
        assert result["success"] is True
    assert len(results["know_sure_thing"]["plots"]) == 2
    assert len(results["macd_leader"]["plots"]) == 3
    assert len(results["envelope_rsi_signals"]["plots"]) == 4
    assert all(plot["overlay"] for plot in results["hema_trend_levels"]["plots"])


def test_chart_indicator_errors_are_per_request():
    bars = _sample_bars()
    results = compute_chart_indicators(
        bars,
        [
            {"id": "missing", "requestKey": "a"},
            {"id": "macd", "requestKey": "b", "params": {"fast": 30, "slow": 10}},
            {"id": "sma", "requestKey": "c", "params": {"length": 5}},
        ],
    )
    assert results[0] == {"id": "missing", "requestKey": "a", "success": False, "error": "indicator.notFound"}
    assert results[1]["success"] is False
    assert results[1]["requestKey"] == "b"
    assert "invalid parameter" in results[1]["error"]
    assert results[2]["success"] is True
    assert results[2]["requestKey"] == "c"
