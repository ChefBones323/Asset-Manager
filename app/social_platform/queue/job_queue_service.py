import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import text
from app.social_platform.models.base import SessionLocal
from app.social_platform.models.worker_models import JobQueueEntry, DeadLetterEntry

logger = logging.getLogger("job_queue_service")


class JobQueueService:
    def enqueue_job(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        session = SessionLocal()
        try:
            job = JobQueueEntry(
                proposal_id=proposal.get("proposal_id", str(uuid.uuid4())),
                tool_name=proposal.get("action", proposal.get("tool_name", "unknown")),
                payload=proposal.get("payload", {}),
                status="queued",
                retry_count=0,
                max_retries=proposal.get("max_retries", 3),
            )
            session.add(job)
            session.commit()
            result = job.to_dict()
            logger.info(f"Job {result['id']} enqueued for proposal {result['proposal_id']}")
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def claim_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        session = SessionLocal()
        try:
            job = (
                session.query(JobQueueEntry)
                .filter(JobQueueEntry.status == "queued")
                .order_by(JobQueueEntry.created_at.asc())
                .with_for_update(skip_locked=True)
                .first()
            )
            if not job:
                return None

            job.status = "claimed"
            job.claimed_by_worker = uuid.UUID(worker_id) if isinstance(worker_id, str) else worker_id
            job.updated_at = datetime.now(timezone.utc)
            session.commit()
            result = job.to_dict()
            logger.info(f"Job {result['id']} claimed by worker {worker_id}")
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_job_status(self, job_id: str, status: str) -> Optional[Dict[str, Any]]:
        session = SessionLocal()
        try:
            job = session.query(JobQueueEntry).filter(
                JobQueueEntry.id == uuid.UUID(job_id)
            ).first()
            if not job:
                return None
            job.status = status
            job.updated_at = datetime.now(timezone.utc)
            session.commit()
            return job.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def fail_job(self, job_id: str, error: str) -> Dict[str, Any]:
        session = SessionLocal()
        try:
            job = session.query(JobQueueEntry).filter(
                JobQueueEntry.id == uuid.UUID(job_id)
            ).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            job.retry_count += 1
            job.updated_at = datetime.now(timezone.utc)

            if job.retry_count >= job.max_retries:
                job.status = "dlq"
                dlq_entry = DeadLetterEntry(
                    job_id=job.id,
                    error_message=error,
                )
                session.add(dlq_entry)
                logger.warning(f"Job {job_id} moved to DLQ after {job.retry_count} retries")
            else:
                job.status = "queued"
                job.claimed_by_worker = None
                logger.info(f"Job {job_id} requeued (retry {job.retry_count}/{job.max_retries})")

            session.commit()
            return job.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def retry_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        session = SessionLocal()
        try:
            job = session.query(JobQueueEntry).filter(
                JobQueueEntry.id == uuid.UUID(job_id)
            ).first()
            if not job:
                return None
            if job.status not in ("failed", "dlq"):
                return job.to_dict()
            job.status = "queued"
            job.claimed_by_worker = None
            job.updated_at = datetime.now(timezone.utc)
            session.commit()
            return job.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_queue_depth(self) -> Dict[str, int]:
        session = SessionLocal()
        try:
            rows = (
                session.query(JobQueueEntry.status, text("count(*)"))
                .group_by(JobQueueEntry.status)
                .all()
            )
            counts = {status: count for status, count in rows}
            return {
                "queued": counts.get("queued", 0),
                "claimed": counts.get("claimed", 0),
                "running": counts.get("running", 0),
                "completed": counts.get("completed", 0),
                "failed": counts.get("failed", 0),
                "dlq": counts.get("dlq", 0),
                "total": sum(counts.values()),
            }
        finally:
            session.close()

    def list_jobs(self, limit: int = 50, status: Optional[str] = None) -> List[Dict[str, Any]]:
        session = SessionLocal()
        try:
            query = session.query(JobQueueEntry)
            if status:
                query = query.filter(JobQueueEntry.status == status)
            jobs = query.order_by(JobQueueEntry.created_at.desc()).limit(limit).all()
            return [j.to_dict() for j in jobs]
        finally:
            session.close()

    def list_dlq(self, limit: int = 50) -> List[Dict[str, Any]]:
        session = SessionLocal()
        try:
            entries = (
                session.query(DeadLetterEntry)
                .order_by(DeadLetterEntry.failed_at.desc())
                .limit(limit)
                .all()
            )
            return [e.to_dict() for e in entries]
        finally:
            session.close()

    def get_stats(self) -> Dict[str, Any]:
        session = SessionLocal()
        try:
            total = session.query(JobQueueEntry).count()
            completed = session.query(JobQueueEntry).filter(JobQueueEntry.status == "completed").count()
            failed = session.query(JobQueueEntry).filter(JobQueueEntry.status.in_(["failed", "dlq"])).count()
            dlq_count = session.query(DeadLetterEntry).count()
            retry_total = session.execute(
                text("SELECT COALESCE(SUM(retry_count), 0) FROM job_queue")
            ).scalar()
            retry_rate = (retry_total / total * 100) if total > 0 else 0.0
            return {
                "jobs_processed_total": completed,
                "jobs_failed_total": failed,
                "dlq_count": dlq_count,
                "retry_rate": round(retry_rate, 2),
                "total_jobs": total,
            }
        finally:
            session.close()
