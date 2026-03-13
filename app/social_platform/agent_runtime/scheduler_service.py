import logging
import threading
import time
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger("agent_runtime.scheduler")


class ScheduledTask:
    def __init__(
        self,
        task_id: str,
        name: str,
        handler: Callable[[], Dict[str, Any]],
        interval_seconds: int,
        description: str = "",
    ):
        self.task_id = task_id
        self.name = name
        self.handler = handler
        self.interval_seconds = interval_seconds
        self.description = description
        self.last_run: Optional[str] = None
        self.run_count = 0
        self.enabled = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "interval_seconds": self.interval_seconds,
            "last_run": self.last_run,
            "run_count": self.run_count,
            "enabled": self.enabled,
        }


class SchedulerService:
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register_task(
        self,
        task_id: str,
        name: str,
        handler: Callable[[], Dict[str, Any]],
        interval_seconds: int,
        description: str = "",
    ) -> ScheduledTask:
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            handler=handler,
            interval_seconds=interval_seconds,
            description=description,
        )
        self._tasks[task_id] = task
        logger.info(f"Registered scheduled task: {name} (every {interval_seconds}s)")
        return task

    def unregister_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def list_tasks(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._tasks.values()]

    def run_task_now(self, task_id: str) -> Dict[str, Any]:
        task = self._tasks.get(task_id)
        if not task:
            return {"status": "error", "error": f"Task '{task_id}' not found"}
        try:
            result = task.handler()
            task.last_run = datetime.now(timezone.utc).isoformat()
            task.run_count += 1
            logger.info(f"Executed task '{task.name}' (run #{task.run_count})")
            return {"status": "success", "task": task.name, "result": result}
        except Exception as exc:
            logger.error(f"Scheduled task '{task.name}' failed: {exc}")
            return {"status": "error", "task": task.name, "error": str(exc)}

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler stopped")

    def _loop(self) -> None:
        tick = 0
        while self._running:
            time.sleep(1)
            tick += 1
            for task in self._tasks.values():
                if not task.enabled:
                    continue
                if tick % task.interval_seconds == 0:
                    self.run_task_now(task.task_id)

    @property
    def is_running(self) -> bool:
        return self._running
