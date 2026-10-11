from __future__ import annotations

from pathlib import Path

from app.routes.settings import (
    ADVANCED_KEYS,
    CONFIG_SCHEMA,
    RESTART_REQUIRED_SETTINGS,
    STRATEGY_RUNTIME_SETTINGS,
)


def test_strategy_runtime_settings_are_exposed_and_restart_scoped():
    items = CONFIG_SCHEMA["strategy_runtime"]["items"]
    keys = {item["key"] for item in items}

    assert keys == {
        "STRATEGY_MAX_ACTIVE",
        "STRATEGY_EVALUATOR_THREADS",
        "BAR_CLOSE_EVENT_GRACE_SEC",
    }
    assert keys <= RESTART_REQUIRED_SETTINGS
    assert keys < STRATEGY_RUNTIME_SETTINGS


def test_first_install_keeps_a_single_trading_worker():
    repository_root = Path(__file__).resolve().parents[2]
    env_template = (repository_root / ".env.example").read_text(encoding="utf-8")
    assert "TRADING_WORKER_REPLICAS=1" in env_template
    assert "STRATEGY_DISPATCHER_REPLICAS" not in env_template
    assert "STRATEGY_EVALUATOR_REPLICAS" not in env_template

    for compose_name in ("docker-compose.yml", "docker-compose.ghcr.yml"):
        compose = (repository_root / compose_name).read_text(encoding="utf-8")
        assert "${TRADING_WORKER_REPLICAS:-1}" in compose
        assert "strategy-dispatcher-worker" not in compose
        assert "strategy-evaluator-worker" not in compose
