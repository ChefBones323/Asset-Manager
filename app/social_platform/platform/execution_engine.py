import uuid
from datetime import datetime, timezone
from typing import Optional, Callable, Dict, Any

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.platform.proposal_service import ProposalService
from app.social_platform.platform.approval_service import ApprovalService
from app.social_platform.platform.manifest_compiler import ManifestCompiler
from app.social_platform.platform.lease_manager import LeaseManager
from app.social_platform.platform.audit_logger import AuditLogger


class ExecutionEngine:
    def __init__(self, event_store: EventStore):
        self._event_store = event_store
        self._proposal_service = ProposalService(event_store)
        self._approval_service = ApprovalService(event_store, self._proposal_service)
        self._manifest_compiler = ManifestCompiler()
        self._lease_manager = LeaseManager(event_store)
        self._audit_logger = AuditLogger(event_store)
        self._executors: Dict[str, Callable[[dict], dict]] = {}

    @property
    def proposal_service(self) -> ProposalService:
        return self._proposal_service

    @property
    def approval_service(self) -> ApprovalService:
        return self._approval_service

    @property
    def manifest_compiler(self) -> ManifestCompiler:
        return self._manifest_compiler

    @property
    def lease_manager(self) -> LeaseManager:
        return self._lease_manager

    @property
    def audit_logger(self) -> AuditLogger:
        return self._audit_logger

    def register_executor(self, action: str, executor: Callable[[dict], dict]):
        self._executors[action] = executor

    def submit_proposal(
        self,
        actor_id: uuid.UUID,
        domain: str,
        action: str,
        payload: dict,
        description: str = "",
    ) -> dict:
        proposal = self._proposal_service.create_proposal(
            actor_id=actor_id, domain=domain, action=action, payload=payload, description=description
        )
        self._audit_logger.log_action(
            actor_id=actor_id,
            action="submit_proposal",
            resource_type="proposal",
            resource_id=proposal["proposal_id"],
            details={"domain": domain, "action": action},
        )
        return proposal

    def approve(self, proposal_id: str, approver_id: uuid.UUID, reason: str = "") -> Optional[dict]:
        result = self._approval_service.approve_proposal(proposal_id, approver_id, reason)
        if result:
            self._audit_logger.log_action(
                actor_id=approver_id,
                action="approve_proposal",
                resource_type="proposal",
                resource_id=proposal_id,
                details={"reason": reason},
            )
        return result

    def reject(self, proposal_id: str, rejector_id: uuid.UUID, reason: str = "") -> Optional[dict]:
        result = self._approval_service.reject_proposal(proposal_id, rejector_id, reason)
        if result:
            self._audit_logger.log_action(
                actor_id=rejector_id,
                action="reject_proposal",
                resource_type="proposal",
                resource_id=proposal_id,
                details={"reason": reason},
            )
        return result

    def enqueue(self, proposal_id: str) -> dict:
        proposal = self._proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        if not self._approval_service.is_approved(proposal_id):
            raise ValueError(f"Proposal {proposal_id} is not approved")

        from app.social_platform.queue.job_queue_service import JobQueueService
        queue_service = JobQueueService()
        job = queue_service.enqueue_job({
            "proposal_id": proposal_id,
            "action": proposal.get("action", "unknown"),
            "tool_name": proposal.get("action", "unknown"),
            "payload": proposal.get("payload", {}),
        })

        actor_id = uuid.UUID(proposal["actor_id"])
        self._event_store.append_event(
            domain="platform",
            event_type="job_enqueued",
            actor_id=actor_id,
            payload={"proposal_id": proposal_id, "job_id": job["id"]},
        )
        self._audit_logger.log_action(
            actor_id=actor_id,
            action="enqueue_proposal",
            resource_type="proposal",
            resource_id=proposal_id,
            details={"job_id": job["id"]},
        )
        return {"proposal_id": proposal_id, "job_id": job["id"], "status": "enqueued"}

    def execute(self, proposal_id: str, worker_id: str) -> dict:
        proposal = self._proposal_service.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        if not self._approval_service.is_approved(proposal_id):
            raise ValueError(f"Proposal {proposal_id} is not approved")

        manifest = self._manifest_compiler.compile_manifest(proposal)

        lease = self._lease_manager.acquire_lease(proposal_id, worker_id)
        if not lease:
            raise ValueError(f"Could not acquire lease for proposal {proposal_id}")

        actor_id = uuid.UUID(proposal["actor_id"])
        execution_id = uuid.uuid4()

        self._event_store.append_event(
            domain="platform",
            event_type="execution_started",
            actor_id=actor_id,
            payload={"proposal_id": proposal_id, "manifest_id": manifest["manifest_id"]},
            execution_id=execution_id,
        )

        executor = self._executors.get(proposal["action"])
        result = {}
        outcome = "success"
        try:
            if executor:
                result = executor(manifest)
            else:
                result = {"status": "completed", "message": f"No executor registered for action '{proposal['action']}'"}

            self._proposal_service.update_proposal_status(proposal_id, "executed")

            self._event_store.append_event(
                domain="platform",
                event_type="execution_completed",
                actor_id=actor_id,
                payload={"proposal_id": proposal_id, "result": result},
                execution_id=execution_id,
            )
        except Exception as exc:
            outcome = "failure"
            self._proposal_service.update_proposal_status(proposal_id, "failed")

            self._event_store.append_event(
                domain="platform",
                event_type="execution_failed",
                actor_id=actor_id,
                payload={"proposal_id": proposal_id, "error": str(exc)},
                execution_id=execution_id,
            )
            raise
        finally:
            self._lease_manager.release_lease(proposal_id, worker_id)
            self._audit_logger.log_action(
                actor_id=actor_id,
                action="execute_proposal",
                resource_type="proposal",
                resource_id=proposal_id,
                details={"manifest_id": manifest["manifest_id"], "outcome": outcome},
                outcome=outcome,
            )

        return {"manifest": manifest, "result": result, "execution_id": str(execution_id)}
