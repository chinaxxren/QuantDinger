from __future__ import annotations

import pandas as pd
import pytest

from app.services import indicator_signal_alerts
from app.services.indicator_signal_alerts import IndicatorSignalAlertService, is_indicator_signal_capable
from app.services.indicator_catalog import compute_chart_indicators, list_chart_indicators
from app.services.indicator_signal_evaluation import latest_matching_signal, latest_series_condition


@pytest.mark.parametrize(
    "code, expected",
    [
        ("output = {'signals': [{'type': 'buy', 'data': marks}]}", True),
        ("signals = []\nsignals.append({'type': 'buy'})", True),
        ("output = {'signals': []}", False),
        ("output = {'plots': []}", False),
    ],
)
def test_indicator_signal_capability_matches_output_contract(code, expected):
    assert is_indicator_signal_capable(code) is expected


def _df(count: int = 4) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": list(range(count)),
            "open": [10.0 + i for i in range(count)],
            "high": [10.5 + i for i in range(count)],
            "low": [9.5 + i for i in range(count)],
            "close": [10.2 + i for i in range(count)],
            "volume": [100.0 for _ in range(count)],
        }
    )


def test_signal_alert_static_text_does_not_trigger_every_bar():
    service = IndicatorSignalAlertService()
    output = {
        "signals": [
            {
                "type": "buy",
                "text": "Cross Up",
                "data": [None, 9.9, None, None],
            }
        ]
    }

    assert latest_matching_signal(output, _df(4), ["any"]) is None


def test_signal_alert_uses_closed_signal_bar_on_next_bar_open():
    service = IndicatorSignalAlertService()
    output = {
        "signals": [
            {
                "type": "buy",
                "text": "Cross Up",
                "data": [None, None, 11.9, None],
            }
        ]
    }

    signal = latest_matching_signal(output, _df(4), ["any"])

    assert signal is not None
    assert signal["label"] == "Cross Up"
    assert signal["bar_index"] == 2
    assert signal["bar_time"] == "1970-01-01T00:00:02"
    assert signal["notify_bar_index"] == 3


@pytest.mark.parametrize(
    "marker",
    [False, 0, 0.0, "0", "false", "None", {"active": False, "price": 12.0}],
)
def test_signal_alert_ignores_inactive_marker_values_even_with_text(marker):
    service = IndicatorSignalAlertService()
    output = {
        "signals": [
            {
                "type": "buy",
                "text": "Long Entry",
                "textData": [None, None, "Long Entry", None],
                "data": [None, None, marker, None],
            }
        ]
    }

    assert latest_matching_signal(output, _df(4), ["any"]) is None


def test_signal_alert_boolean_marker_uses_candle_close_as_price():
    service = IndicatorSignalAlertService()
    output = {
        "signals": [
            {
                "type": "buy",
                "text": "Long Entry",
                "data": [False, False, True, False],
            }
        ]
    }

    signal = latest_matching_signal(output, _df(4), ["text:long entry"])

    assert signal is not None
    assert signal["label"] == "Long Entry"
    assert signal["price"] == pytest.approx(12.2)


def test_signal_alert_dense_state_notifies_only_on_transition():
    service = IndicatorSignalAlertService()
    output = {
        "signals": [
            {
                "type": "buy",
                "text": "Long Entry",
                "data": [None, 10.0, 11.0, None],
            }
        ]
    }

    assert latest_matching_signal(output, _df(4), ["any"]) is None


def test_signal_alert_dense_state_transition_still_notifies():
    service = IndicatorSignalAlertService()
    output = {
        "signals": [
            {
                "type": "buy",
                "text": "Long Entry",
                "data": [None, None, 11.0, 12.0],
            }
        ]
    }

    signal = latest_matching_signal(output, _df(4), ["any"])

    assert signal is not None
    assert signal["bar_index"] == 2


def test_signal_alert_points_mode_allows_consecutive_markers():
    service = IndicatorSignalAlertService()
    output = {
        "signals": [
            {
                "type": "buy",
                "text": "Long Entry",
                "renderMode": "points",
                "data": [None, 10.0, 11.0, None],
            }
        ]
    }

    signal = latest_matching_signal(output, _df(4), ["any"])

    assert signal is not None
    assert signal["bar_index"] == 2


def test_signal_alert_events_mode_keeps_dense_events_explicit():
    service = IndicatorSignalAlertService()
    output = {
        "signals": [
            {
                "type": "buy",
                "text": "Long Entry",
                "renderMode": "events",
                "data": [None, 10.0, 11.0, None],
            }
        ]
    }

    signal = latest_matching_signal(output, _df(4), ["any"])

    assert signal is not None
    assert signal["bar_index"] == 2


def test_signal_alert_payload_uses_profile_notification_defaults(monkeypatch):
    monkeypatch.setattr(
        indicator_signal_alerts,
        "get_notification_settings",
        lambda user_id: {
            "default_channels": ["email", "telegram", "webhook"],
            "email": "alerts@example.com",
            "telegram_chat_id": "123456",
            "telegram_bot_token": "profile-token",
            "webhook_url": "https://example.com/hook",
            "webhook_token": "hook-token",
            "webhook_signing_secret": "hook-secret",
        },
    )

    payload = IndicatorSignalAlertService()._sanitize_payload(
        7,
        {
            "indicator_id": 12,
            "symbol": "BTC/USDT",
            "targets": {"email": "task@example.com"},
        },
    )

    assert payload["channels"] == ["email", "telegram", "webhook"]
    assert payload["targets"]["email"] == "task@example.com"
    assert payload["targets"]["telegram_chat_id"] == "123456"
    assert payload["targets"]["telegram_bot_token"] == "profile-token"
    assert payload["targets"]["webhook_url"] == "https://example.com/hook"
    assert payload["targets"]["webhook_token"] == "hook-token"
    assert payload["targets"]["webhook_signing_secret"] == "hook-secret"


def test_builtin_indicator_payload_uses_series_condition(monkeypatch):
    monkeypatch.setattr(indicator_signal_alerts, "get_notification_settings", lambda user_id: {})

    payload = IndicatorSignalAlertService()._sanitize_payload(
        7,
        {
            "indicator_source": "builtin",
            "indicator_key": "cci",
            "symbol": "BTC/USDT",
            "condition": {"mode": "series", "operator": "cross_below", "threshold": -100},
        },
    )

    assert payload["indicator_id"] == 0
    assert payload["indicator_source"] == "builtin"
    assert payload["indicator_key"] == "cci"
    assert payload["condition"] == {
        "mode": "series",
        "operator": "cross_below",
        "threshold": -100.0,
        "series_key": "*",
    }


def test_chart_indicator_catalog_contains_computable_cci():
    catalog = {item["id"]: item for item in list_chart_indicators()}

    assert catalog["cci"]["computeAvailable"] is True
    assert catalog["cci"]["signalMode"] == "series"
    assert catalog["cci"]["defaultAlertCondition"]["threshold"] == 100
    assert catalog["supertrend"]["signalMode"] == "markers"
    assert catalog["chip_distribution"]["signalCapable"] is False
    result = compute_chart_indicators(_df(30), [{"id": "cci"}])
    assert result[0]["success"] is True
    assert result[0]["plots"][0]["name"] == "cci"


def test_signal_catalog_unifies_builtin_and_saved_indicators(monkeypatch):
    class Cursor:
        def execute(self, *_args, **_kwargs):
            return None

        def fetchall(self):
            return [{
                "id": 42,
                "user_id": 7,
                "name": "Saved CCI",
                "code": "my_indicator_name = 'Saved CCI'\noutput = {'plots': []}",
                "description": "Personal version",
                "asset_type": "indicator",
            }]

        def close(self):
            return None

    class Database:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(indicator_signal_alerts, "get_db_connection", Database)

    catalog = IndicatorSignalAlertService().list_indicator_catalog(7)
    by_key = {item["key"]: item for item in catalog}

    assert by_key["builtin:cci"]["display_name"] == "CCI"
    assert by_key["builtin:cci"]["signal_mode"] == "series"
    assert by_key["custom:42"]["display_name"] == "Saved CCI"
    assert by_key["custom:42"]["signal_mode"] == "series"


def _batch_payload(indicators, symbols):
    return {
        "indicator_refs": [
            {"source": "builtin", "indicator_key": indicator}
            for indicator in indicators
        ],
        "symbol_refs": symbols,
        "timeframe": "1D",
    }


def test_batch_alerts_create_one_task_for_each_indicator_symbol_pair(monkeypatch):
    service = IndicatorSignalAlertService()
    created = []

    monkeypatch.setattr(indicator_signal_alerts, "ensure_indicator_signal_alert_schema", lambda: None)
    monkeypatch.setattr(
        service,
        "_load_indicator_reference",
        lambda _user_id, reference: {
            "display_name": str(reference["indicator_key"]).upper(),
            "name": str(reference["indicator_key"]).upper(),
        },
    )
    monkeypatch.setattr(
        service,
        "_sanitize_payload",
        lambda _user_id, payload: {
            "indicator_id": 0,
            "indicator_source": payload["indicator_source"],
            "indicator_key": payload["indicator_key"],
            "market": payload["market"],
            "symbol": payload["symbol"],
            "timeframe": payload["timeframe"],
        },
    )
    monkeypatch.setattr(service, "_find_duplicate_task", lambda *_args: None)
    monkeypatch.setattr(
        service,
        "create_task",
        lambda _user_id, payload: created.append({"indicator_key": payload["indicator_key"], "market": payload["market"], "symbol": payload["symbol"]}) or created[-1],
    )

    result = service.create_batch_tasks(
        7,
        _batch_payload(
            ["cci", "rsi"],
            [
                {"market": "Crypto", "symbol": "BTC/USDT", "symbol_name": "Bitcoin"},
                {"market": "Crypto", "symbol": "ETH/USDT", "symbol_name": "Ethereum"},
            ],
        ),
    )

    assert len(result["created"]) == 4
    assert {(item["indicator_key"], item["symbol"]) for item in created} == {
        ("cci", "BTC/USDT"),
        ("cci", "ETH/USDT"),
        ("rsi", "BTC/USDT"),
        ("rsi", "ETH/USDT"),
    }


def test_batch_alerts_skip_duplicate_per_symbol(monkeypatch):
    service = IndicatorSignalAlertService()
    monkeypatch.setattr(indicator_signal_alerts, "ensure_indicator_signal_alert_schema", lambda: None)
    monkeypatch.setattr(
        service,
        "_load_indicator_reference",
        lambda _user_id, _reference: {"display_name": "CCI", "name": "CCI"},
    )
    monkeypatch.setattr(
        service,
        "_sanitize_payload",
        lambda _user_id, payload: {
            "indicator_id": 0,
            "indicator_source": "builtin",
            "indicator_key": payload["indicator_key"],
            "market": payload["market"],
            "symbol": payload["symbol"],
            "timeframe": payload["timeframe"],
        },
    )
    monkeypatch.setattr(
        service,
        "_find_duplicate_task",
        lambda _user_id, data: {"id": 12} if data["symbol"] == "BTC/USDT" else None,
    )
    monkeypatch.setattr(service, "create_task", lambda _user_id, payload: payload)

    result = service.create_batch_tasks(
        7,
        _batch_payload(
            ["cci"],
            [
                {"market": "Crypto", "symbol": "BTC/USDT"},
                {"market": "Crypto", "symbol": "ETH/USDT"},
            ],
        ),
    )

    assert len(result["created"]) == 1
    assert result["created"][0]["symbol"] == "ETH/USDT"
    assert result["skipped"] == [{
        "indicator_id": 0,
        "indicator_source": "builtin",
        "indicator_key": "cci",
        "indicator_name": "CCI",
        "market": "Crypto",
        "symbol": "BTC/USDT",
        "task_id": 12,
        "reason": "duplicate",
    }]


def test_batch_alerts_reject_empty_symbols_and_too_many_combinations(monkeypatch):
    service = IndicatorSignalAlertService()
    monkeypatch.setattr(indicator_signal_alerts, "ensure_indicator_signal_alert_schema", lambda: None)

    with pytest.raises(ValueError, match="Select at least one symbol"):
        service.create_batch_tasks(7, _batch_payload(["cci"], []))

    with pytest.raises(ValueError, match="100 alert tasks"):
        service.create_batch_tasks(
            7,
            _batch_payload(
                ["cci", "rsi", "macd"],
                [{"market": "Crypto", "symbol": f"COIN{index}/USDT"} for index in range(34)],
            ),
        )


def test_series_threshold_crossing_uses_last_closed_bar():
    service = IndicatorSignalAlertService()
    output = {"plots": [{"name": "cci", "data": [None, -120.0, -90.0, -80.0]}]}

    signal = latest_series_condition(
        output,
        _df(4),
        {"mode": "series", "operator": "cross_above", "threshold": -100, "series_key": "*"},
    )

    assert signal is not None
    assert signal["type"] == "cross_above"
    assert signal["series"] == "cci"
    assert signal["indicator_value"] == pytest.approx(-90.0)
    assert signal["bar_index"] == 2
    assert signal["notify_bar_index"] == 3


def test_builtin_reference_uses_backend_definition_and_rejects_non_alertable_profile():
    service = IndicatorSignalAlertService()

    cci = service._load_indicator_reference(7, {"source": "builtin", "indicator_key": "cci"})
    assert cci["display_name"] == "CCI"
    assert cci["default_params"] == {"length": 20}

    with pytest.raises(ValueError, match="no alertable signal or numeric series"):
        service._load_indicator_reference(7, {"source": "builtin", "indicator_key": "chip_distribution"})
