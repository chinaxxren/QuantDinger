"""Regression coverage for the process-local bar-close runtime path."""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from app.events.bar_clock import BarStreamKey, MarketBarCloseClock
from app.events.bus import InMemoryEventBus
from app.events.protocol import MarketBarClosedV1
from app.services.trading_executor import TradingExecutor


class _RecordingScheduler:
    def __init__(self) -> None:
        self.wakes = []

    def wake_strategy(self, strategy_id, event):
        self.wakes.append((int(strategy_id), event))
        return True


def _stream(venue: str) -> BarStreamKey:
    return BarStreamKey(
        venue=venue,
        market="Crypto",
        market_type="swap",
        instrument_id="BTCUSDT",
        symbol="BTC/USDT",
        timeframe="1m",
    )


def test_local_bar_clock_wakes_only_matching_strategy_stream():
    bus = InMemoryEventBus()
    clock = MarketBarCloseClock(
        bus,
        now=lambda: datetime(2026, 9, 29, 12, 0, 30, tzinfo=timezone.utc),
        autostart=False,
    )
    executor = TradingExecutor.__new__(TradingExecutor)
    executor._scheduler = _RecordingScheduler()
    pending = threading.Event()
    stop_event = threading.Event()

    subscription = clock.subscribe(
        _stream("binance"),
        lambda event: executor._wake_strategy_for_bar_close(
            101,
            pending,
            event,
            stop_event=stop_event,
        ),
    )
    other_subscription = clock.subscribe(_stream("bybit"), lambda _event: None)

    assert clock.publish_due(datetime(2026, 9, 29, 12, 1, 1, tzinfo=timezone.utc)) == 2
    assert pending.is_set()
    assert len(executor._scheduler.wakes) == 1
    strategy_id, event = executor._scheduler.wakes[0]
    assert strategy_id == 101
    assert event.event_type == MarketBarClosedV1.event_type
    assert event.payload["venue"] == "binance"

    subscription.close()
    other_subscription.close()
    clock.close()
    bus.close()


def test_closed_runtime_does_not_requeue_bar_event():
    executor = TradingExecutor.__new__(TradingExecutor)
    executor._scheduler = _RecordingScheduler()
    pending = threading.Event()
    stop_event = threading.Event()
    stop_event.set()

    event = MarketBarClosedV1.create(
        venue="binance",
        market="Crypto",
        market_type="swap",
        instrument_id="BTCUSDT",
        symbol="BTC/USDT",
        timeframe="1m",
        closed_bar_token=1,
        closed_at=datetime(2026, 9, 29, 12, 1, tzinfo=timezone.utc),
    )

    assert not executor._wake_strategy_for_bar_close(
        101,
        pending,
        event,
        stop_event=stop_event,
    )
    assert not pending.is_set()
    assert executor._scheduler.wakes == []
