"""Trading worker ownership and command boundary tests."""

from __future__ import annotations

import pytest

from app.services.strategy_command_repository import StrategyCommand
from app.workers.trading import TradingWorker


class FakeExecutor:
    def __init__(self, *, stop_result: bool = True) -> None:
        self.running_strategies = {}
        self.lock = __import__("threading").Lock()
        self.stopped = []
        self.policy_stops = []
        self.stop_result = stop_result
        self.handoffs = []

    def start_strategy(self, strategy_id):
        self.running_strategies[int(strategy_id)] = object()
        return True

    def wait_strategy_running(self, strategy_id, timeout=0):
        del timeout
        return int(strategy_id) in self.running_strategies, ""

    def set_runtime_fencing_token(self, strategy_id, fencing_token):
        del strategy_id, fencing_token

    def clear_runtime_fencing_token(self, strategy_id):
        del strategy_id

    def stop_strategy(self, strategy_id, persist_status=False, preserve_run=False):
        del persist_status
        self.stopped.append(int(strategy_id))
        if preserve_run:
            self.handoffs.append(int(strategy_id))
        if self.stop_result:
            self.running_strategies.pop(int(strategy_id), None)
        return self.stop_result

    def stop_strategy_with_policy(self, strategy_id, *, close_positions):
        self.policy_stops.append((int(strategy_id), bool(close_positions)))
        stopped = self.stop_strategy(strategy_id)
        return {
            "strategy_id": strategy_id,
            "success": stopped,
            "status": "stopped" if stopped else "running",
            "close_requested": bool(close_positions),
            "close_positions_found": 0,
            "message": "runtime stop timeout" if not stopped else "",
        }


class FakeRepository:
    def __init__(self) -> None:
        self.completed = []
        self.failed = []
        self.released = []
        self.revoked = []
        self.active_leases = set()

    def complete(self, command_id, result=None):
        self.completed.append((command_id, result))

    def fail(self, command_id, error, retry_delay_seconds=None):
        self.failed.append((command_id, error, retry_delay_seconds))

    def release_strategy_lease(self, *, strategy_id, owner_id):
        self.released.append((strategy_id, owner_id))

    def revoke_strategy_lease(self, *, strategy_id):
        self.revoked.append(int(strategy_id))
        return True

    @staticmethod
    def has_pending_stop(_strategy_id):
        return False

    def has_active_strategy_lease(self, strategy_id):
        return int(strategy_id) in self.active_leases


def _command(command_type: str) -> StrategyCommand:
    return StrategyCommand(
        id=1,
        strategy_id=55,
        user_id=1,
        command_type=command_type,
        status="processing",
        idempotency_key="test-command",
        payload={},
        attempts=1,
    )


def test_stop_command_is_executed_by_trading_worker():
    repository = FakeRepository()
    executor = FakeExecutor()
    worker = TradingWorker(executor, repository)

    worker._execute(_command("stop"))

    assert executor.stopped == [55]
    assert repository.released == [(55, worker.worker_id)]
    assert repository.revoked == [55]
    assert repository.completed[0][1]["status"] == "stopped"


def test_failed_command_is_retried_with_backoff(monkeypatch):
    repository = FakeRepository()
    worker = TradingWorker(FakeExecutor(), repository)
    monkeypatch.setattr(worker, "_start", lambda _strategy_id: (_ for _ in ()).throw(RuntimeError("boom")))

    worker._execute(_command("start"))

    assert repository.failed == [(1, "boom", 1)]


@pytest.mark.parametrize("close_positions", [False, True])
def test_stop_timeout_retains_runtime_lease(monkeypatch, close_positions):
    repository = FakeRepository()
    executor = FakeExecutor(stop_result=False)
    executor.running_strategies[55] = object()
    worker = TradingWorker(executor, repository)
    monkeypatch.setattr("app.workers.trading.append_strategy_log", lambda *_args, **_kwargs: None)

    with pytest.raises(RuntimeError, match="stop"):
        worker._stop_strategy(55, close_positions=close_positions)

    assert repository.released == []
    assert repository.revoked == []
    assert 55 in executor.running_strategies


def test_worker_shutdown_retains_lease_when_runtime_does_not_stop(monkeypatch):
    repository = FakeRepository()
    executor = FakeExecutor(stop_result=False)
    executor.running_strategies[55] = object()
    worker = TradingWorker(executor, repository)
    monkeypatch.setattr("app.workers.trading.append_strategy_log", lambda *_args, **_kwargs: None)

    worker._shutdown_local_runtimes()

    assert repository.released == []
    assert 55 in executor.running_strategies


def test_worker_shutdown_releases_watched_lease_after_runtime_already_exited():
    repository = FakeRepository()
    executor = FakeExecutor()
    worker = TradingWorker(executor, repository)
    worker._lease_heartbeat.watch_strategy(55)

    worker._shutdown_local_runtimes()

    assert repository.released == [(55, worker.worker_id)]
    assert worker._lease_heartbeat.strategy_ids() == []


def test_start_succeeds_when_another_pool_worker_already_owns_runtime(monkeypatch):
    from app.services.strategy import StrategyService

    monkeypatch.setattr(
        StrategyService,
        "get_strategy",
        lambda _self, strategy_id: {"id": strategy_id, "status": "running"},
    )
    repository = FakeRepository()
    repository.active_leases.add(55)
    worker = TradingWorker(FakeExecutor(), repository)
    monkeypatch.setattr(worker, "_acquire_runtime", lambda _strategy_id: False)

    result = worker._start(55)

    assert result == {
        "strategy_id": 55,
        "runtime_owner": "trading-worker-pool",
        "status": "running",
    }


def test_grid_runtime_can_be_owned_by_nonleader_pool_worker(monkeypatch):
    from app.services.strategy import StrategyService

    monkeypatch.setattr(
        StrategyService,
        "get_strategy",
        lambda _self, strategy_id: {
            "id": strategy_id,
            "status": "running",
            "trading_config": {"executor_type": "grid"},
        },
    )
    monkeypatch.setattr(
        "app.services.trading_executor.TradingExecutor._load_source",
        lambda _strategy: (0, ""),
    )
    worker = TradingWorker(FakeExecutor(), FakeRepository())
    monkeypatch.setattr(worker, "_acquire_runtime", lambda _strategy_id: True)

    result = worker._start(55, wait_ready=False)

    assert result == {
        "strategy_id": 55,
        "runtime_owner": worker.worker_id,
        "status": "running",
    }


def test_worker_shutdown_handoffs_runtime_without_business_stop():
    repository = FakeRepository()
    executor = FakeExecutor()
    executor.running_strategies[55] = object()
    worker = TradingWorker(executor, repository)

    worker._shutdown_local_runtimes()

    assert executor.handoffs == [55]
    assert repository.released == [(55, worker.worker_id)]


def test_worker_stop_does_not_end_runtime_before_handoff():
    worker = TradingWorker(FakeExecutor(), FakeRepository())
    worker._lease_heartbeat.watch_strategy(55)

    worker.stop()

    assert worker.executor.runtime_guard(55) is True


def test_command_polling_survives_temporary_database_failure():
    repository = FakeRepository()
    repository.claim_next = lambda **_kwargs: (_ for _ in ()).throw(
        RuntimeError("database unavailable")
    )
    worker = TradingWorker(FakeExecutor(), repository)

    assert worker._claim_next_command() is None
