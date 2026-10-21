"""Process-local worker shell for indicator signal alerts."""

from __future__ import annotations

import os
import threading
from typing import Optional

from app.services.indicator_signal_alerts import (
    IndicatorSignalAlertService,
    ensure_indicator_signal_alert_schema,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IndicatorSignalAlertWorker:
    """Poll due alert tasks without putting worker lifecycle in the workflow."""

    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._service = IndicatorSignalAlertService()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="IndicatorSignalAlertWorker", daemon=True)
        self._thread.start()
        logger.info("Indicator signal alert worker started")

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._service.run_due_tasks(limit=20)
            except Exception as exc:
                logger.warning("Indicator signal alert worker loop failed: %s", exc)
            self._stop.wait(float(os.getenv("INDICATOR_SIGNAL_ALERT_WORKER_INTERVAL", "15")))


_worker: Optional[IndicatorSignalAlertWorker] = None


def get_indicator_signal_alert_worker() -> IndicatorSignalAlertWorker:
    global _worker
    if _worker is None:
        _worker = IndicatorSignalAlertWorker()
    return _worker


def start_indicator_signal_alert_worker() -> None:
    if os.getenv("ENABLE_INDICATOR_SIGNAL_ALERT_WORKER", "true").lower() not in ("1", "true", "yes", "on"):
        logger.info("Indicator signal alert worker disabled")
        return
    ensure_indicator_signal_alert_schema()
    get_indicator_signal_alert_worker().start()
