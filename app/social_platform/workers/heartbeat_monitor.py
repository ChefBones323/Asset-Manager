import time
import logging
import threading
from typing import Optional

from app.social_platform.workers.worker_registry import WorkerRegistry
from app.social_platform.infrastructure.event_store import EventStore

logger = logging.getLogger("heartbeat_monitor")


class HeartbeatMonitor:
    def __init__(
        self,
        registry: WorkerRegistry,
        event_store: Optional[EventStore] = None,
        sweep_interval: float = 15.0,
    ):
        self._registry = registry
        self._event_store = event_store
        self._sweep_interval = sweep_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._sweep_loop, daemon=True)
        self._thread.start()
        logger.info("Heartbeat monitor started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Heartbeat monitor stopped")

    def _sweep_loop(self):
        while self._running:
            try:
                marked = self._registry.sweep_unhealthy()
                if marked and self._event_store:
                    import uuid
                    for wid in marked:
                        self._event_store.append_event(
                            domain="worker",
                            event_type="worker_unhealthy",
                            actor_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
                            payload={"worker_id": wid, "reason": "heartbeat_timeout"},
                        )
            except Exception as exc:
                logger.error(f"Heartbeat sweep error: {exc}")
            time.sleep(self._sweep_interval)
