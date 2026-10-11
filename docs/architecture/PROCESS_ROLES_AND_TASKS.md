# Backend Process Roles and Durable Tasks

The local deployment uses one backend image with independent process roles. No
Kafka service, topic initializer, dispatcher worker, evaluator worker, or audit
worker is required.

| Role | Command | Responsibility |
| --- | --- | --- |
| API | `gunicorn -c gunicorn_config.py run:app` | HTTP, authentication, validation, durable command submission |
| Migration | `python -m app.commands.migrate` | Fail-fast schema application before services start |
| Trading | `python -m app.commands.trading_worker` | Control/realtime runtimes, local closed-bar strategy runtimes, pending-order execution, private streams, reconciliation, durable grid actors |
| Scheduler | `python -m app.commands.scheduler` | Portfolio monitoring, deployment schedules, payment scans, signal alerts, and notifications |
| Celery Worker | `celery -A app.celery_app:celery_app worker` | AI, backtests, reports, and maintenance jobs |
| Celery Beat | `celery -A app.celery_app:celery_app beat` | Periodic maintenance dispatch |

## Ownership rules

- HTTP processes never start trading or scheduler threads.
- Strategy start, stop, restart, and reconcile requests use `qd_strategy_commands`.
- The trading worker claims commands with PostgreSQL `SKIP LOCKED` semantics.
- A strategy runtime requires a renewable row in `qd_strategy_runtime_leases`.
- Fencing tokens increase when an expired runtime is taken over by another worker.
- `TradingExecutor` owns local strategy runtimes. It publishes closed-bar
  notifications to an in-process event bus and schedules each strategy through
  the bounded cooperative runtime scheduler.
- Grid, martingale, DCA, tick-driven, and session-driven strategies remain on
  the trading-worker path.
- Exchange order submission remains behind the pending-order gateway. Runtime
  fencing tokens are validated before an order can be claimed and sent.
- Global exchange pollers and scheduler loops use `qd_process_leases` leader ownership.
- Worker health is recorded in `qd_worker_heartbeats`.

## Celery boundary

Celery owns finite jobs that can be serialized, retried, and observed independently:

- fast AI analysis;
- agent backtests;
- reflection and AI calibration;
- market catalog synchronization;
- runtime metadata cleanup.

Celery must not own long-lived strategy loops, exchange polling, broker sessions,
or grid runtime state. Those remain in the trading process because they require
renewable ownership, reconciliation, and controlled shutdown.

## Redis separation

The cache Redis instance may use an eviction policy. Celery uses `redis-jobs`,
which enables AOF persistence and `noeviction`. Queue state must never share an
evictable Redis memory policy.

## Deployment sequence

1. PostgreSQL and both Redis instances become healthy.
2. Database migration exits successfully.
3. API, trading, scheduler, Celery Worker, and Celery Beat start.
4. Health checks require fresh worker heartbeats and the runtime owner exposes
   its role-specific health state.

For a single host, keep `TRADING_WORKER_REPLICAS=1`. Multiple trading workers
can coordinate durable leases, but the local event bus is process-local, so a
strategy must remain owned by the worker that runs its runtime. Kafka and the
old dispatcher/evaluator replica settings are intentionally not part of the
local deployment.

Use these endpoints for operations:

- `/api/health` for liveness;
- `/api/health/ready` for PostgreSQL and Celery Broker readiness;
- `/api/health/workers` for trading, scheduler, and Celery heartbeat summaries.
