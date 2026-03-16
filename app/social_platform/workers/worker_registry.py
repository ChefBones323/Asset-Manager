import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.worker_models import WorkerNode

logger = logging.getLogger("worker_registry")

HEARTBEAT_TIMEOUT_SECONDS = 30


class WorkerRegistry:
    def register_worker(
        self, hostname: str, capabilities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        session = SessionLocal()
        try:
            worker = WorkerNode(
                hostname=hostname,
                status="idle",
                capabilities=capabilities or [],
                last_heartbeat=datetime.now(timezone.utc),
            )
            session.add(worker)
            session.commit()
            result = worker.to_dict()
            logger.info(f"Worker {result['id']} registered: {hostname}")
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def heartbeat(self, worker_id: str) -> Optional[Dict[str, Any]]:
        session = SessionLocal()
        try:
            worker = session.query(WorkerNode).filter(
                WorkerNode.id == uuid.UUID(worker_id)
            ).first()
            if not worker:
                return None
            worker.last_heartbeat = datetime.now(timezone.utc)
            if worker.status == "unhealthy":
                worker.status = "idle"
            session.commit()
            return worker.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_status(self, worker_id: str, status: str) -> Optional[Dict[str, Any]]:
        session = SessionLocal()
        try:
            worker = session.query(WorkerNode).filter(
                WorkerNode.id == uuid.UUID(worker_id)
            ).first()
            if not worker:
                return None
            worker.status = status
            session.commit()
            return worker.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def assign_job(self, worker_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        session = SessionLocal()
        try:
            worker = session.query(WorkerNode).filter(
                WorkerNode.id == uuid.UUID(worker_id)
            ).first()
            if not worker:
                return None
            worker.current_job_id = uuid.UUID(job_id)
            worker.status = "busy"
            session.commit()
            return worker.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def release_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        session = SessionLocal()
        try:
            worker = session.query(WorkerNode).filter(
                WorkerNode.id == uuid.UUID(worker_id)
            ).first()
            if not worker:
                return None
            worker.current_job_id = None
            worker.status = "idle"
            session.commit()
            return worker.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def mark_worker_unhealthy(self, worker_id: str) -> Optional[Dict[str, Any]]:
        session = SessionLocal()
        try:
            worker = session.query(WorkerNode).filter(
                WorkerNode.id == uuid.UUID(worker_id)
            ).first()
            if not worker:
                return None
            worker.status = "unhealthy"
            worker.current_job_id = None
            session.commit()
            logger.warning(f"Worker {worker_id} marked unhealthy")
            return worker.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_workers(self) -> List[Dict[str, Any]]:
        session = SessionLocal()
        try:
            workers = session.query(WorkerNode).order_by(WorkerNode.created_at.desc()).all()
            return [w.to_dict() for w in workers]
        finally:
            session.close()

    def get_worker(self, worker_id: str) -> Optional[Dict[str, Any]]:
        session = SessionLocal()
        try:
            worker = session.query(WorkerNode).filter(
                WorkerNode.id == uuid.UUID(worker_id)
            ).first()
            return worker.to_dict() if worker else None
        finally:
            session.close()

    def sweep_unhealthy(self) -> List[str]:
        session = SessionLocal()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)
            stale = (
                session.query(WorkerNode)
                .filter(
                    WorkerNode.status.in_(["idle", "busy"]),
                    WorkerNode.last_heartbeat < cutoff,
                )
                .all()
            )
            marked = []
            for w in stale:
                w.status = "unhealthy"
                w.current_job_id = None
                marked.append(str(w.id))
                logger.warning(f"Sweep: worker {w.id} marked unhealthy (last heartbeat: {w.last_heartbeat})")
            if marked:
                session.commit()
            return marked
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_counts(self) -> Dict[str, int]:
        session = SessionLocal()
        try:
            workers = session.query(WorkerNode).all()
            counts = {"total": 0, "idle": 0, "busy": 0, "unhealthy": 0}
            for w in workers:
                counts["total"] += 1
                if w.status in counts:
                    counts[w.status] += 1
            return counts
        finally:
            session.close()
