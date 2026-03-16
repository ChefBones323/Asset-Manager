#!/usr/bin/env python3
import os
import sys
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("run_worker")


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Worker Entrypoint")
    parser.add_argument(
        "--capabilities",
        type=str,
        default="filesystem,web,skills",
        help="Comma-separated list of capabilities",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Queue poll interval in seconds",
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=float,
        default=10.0,
        help="Heartbeat interval in seconds",
    )
    args = parser.parse_args()

    worker_token = os.environ.get("WORKER_TOKEN")
    if not worker_token:
        logger.error("WORKER_TOKEN environment variable is required")
        sys.exit(1)

    import socket
    hostname = socket.gethostname()
    capabilities = [c.strip() for c in args.capabilities.split(",") if c.strip()]

    from app.social_platform.workers.worker_registry import WorkerRegistry
    from app.social_platform.workers.worker_executor import WorkerExecutor
    from app.social_platform.workers.heartbeat_monitor import HeartbeatMonitor
    from app.social_platform.queue.job_queue_service import JobQueueService
    from app.social_platform.infrastructure.event_store import EventStore
    from app.social_platform.agent_runtime.agent_runtime import AgentRuntime

    event_store = EventStore()
    runtime = AgentRuntime(event_store=event_store)
    runtime.scheduler.stop()

    registry = WorkerRegistry()
    queue_service = JobQueueService()

    worker_data = registry.register_worker(hostname, capabilities)
    worker_id = worker_data["id"]
    logger.info(f"Worker registered: {worker_id} ({hostname}) capabilities={capabilities}")

    monitor = HeartbeatMonitor(registry, event_store)
    monitor.start()

    from app.social_platform.agent_runtime.tool_router import ToolRouter
    tool_router = ToolRouter(runtime.tool_registry, runtime.policy_guard, runtime.execution_engine)

    executor = WorkerExecutor(
        worker_id=worker_id,
        queue_service=queue_service,
        registry=registry,
        event_store=event_store,
        tool_router=tool_router,
        execution_engine=runtime.execution_engine,
        poll_interval=args.poll_interval,
        heartbeat_interval=args.heartbeat_interval,
    )

    try:
        executor.run()
    except KeyboardInterrupt:
        logger.info("Shutting down worker...")
    finally:
        monitor.stop()
        registry.update_status(worker_id, "idle")
        logger.info("Worker shut down cleanly")


if __name__ == "__main__":
    main()
