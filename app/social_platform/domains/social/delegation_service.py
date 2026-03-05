import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.delegation_models import Delegation, MAX_DELEGATION_DEPTH
from app.social_platform.platform.execution_engine import ExecutionEngine


class DelegationService:
    DOMAIN = "delegation"

    def __init__(self, execution_engine: ExecutionEngine, session: Optional[Session] = None):
        self._engine = execution_engine
        self._session = session
        self._engine.register_executor("delegate", self._execute_delegate)
        self._engine.register_executor("revoke_delegation", self._execute_revoke)

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _should_close(self) -> bool:
        return self._session is None

    def delegate(
        self,
        actor_id: uuid.UUID,
        delegate_id: uuid.UUID,
        domain: str,
        scope: str = "full",
        reason: str = "",
    ) -> dict:
        if actor_id == delegate_id:
            raise ValueError("Cannot delegate to yourself")

        if self._would_create_loop(actor_id, delegate_id, domain):
            raise ValueError("Delegation would create a loop")

        current_depth = self._get_delegation_depth(actor_id, domain)
        if current_depth >= MAX_DELEGATION_DEPTH:
            raise ValueError(f"Maximum delegation depth ({MAX_DELEGATION_DEPTH}) exceeded")

        payload = {
            "delegate_id": str(delegate_id),
            "domain": domain,
            "scope": scope,
            "reason": reason,
            "depth": current_depth + 1,
        }
        return self._engine.submit_proposal(
            actor_id=actor_id,
            domain=self.DOMAIN,
            action="delegate",
            payload=payload,
            description=f"Delegate {scope} in {domain} to {delegate_id}",
        )

    def revoke(
        self,
        actor_id: uuid.UUID,
        delegation_id: uuid.UUID,
        reason: str = "",
    ) -> dict:
        payload = {
            "delegation_id": str(delegation_id),
            "reason": reason,
        }
        return self._engine.submit_proposal(
            actor_id=actor_id,
            domain=self.DOMAIN,
            action="revoke_delegation",
            payload=payload,
            description=f"Revoke delegation {delegation_id}",
        )

    def check_delegation_path(
        self,
        delegator_id: uuid.UUID,
        delegate_id: uuid.UUID,
        domain: str,
    ) -> List[dict]:
        session = self._get_session()
        try:
            path = []
            visited = set()
            current = delegator_id

            while current and current not in visited and len(path) <= MAX_DELEGATION_DEPTH:
                visited.add(current)
                delegation = (
                    session.query(Delegation)
                    .filter(
                        Delegation.delegator_id == current,
                        Delegation.domain == domain,
                        Delegation.is_active == True,
                    )
                    .first()
                )
                if delegation:
                    path.append(delegation.to_dict())
                    if delegation.delegate_id == delegate_id:
                        return path
                    current = delegation.delegate_id
                else:
                    break

            return path
        finally:
            if self._should_close():
                session.close()

    def prevent_loops(self, delegator_id: uuid.UUID, delegate_id: uuid.UUID, domain: str) -> bool:
        return self._would_create_loop(delegator_id, delegate_id, domain)

    def _would_create_loop(
        self,
        delegator_id: uuid.UUID,
        delegate_id: uuid.UUID,
        domain: str,
    ) -> bool:
        session = self._get_session()
        try:
            visited = set()
            current = delegate_id

            while current and current not in visited:
                if current == delegator_id:
                    return True
                visited.add(current)

                delegation = (
                    session.query(Delegation)
                    .filter(
                        Delegation.delegator_id == current,
                        Delegation.domain == domain,
                        Delegation.is_active == True,
                    )
                    .first()
                )
                if delegation:
                    current = delegation.delegate_id
                else:
                    break

            return False
        finally:
            if self._should_close():
                session.close()

    def _get_delegation_depth(self, user_id: uuid.UUID, domain: str) -> int:
        session = self._get_session()
        try:
            visited = set()
            current = user_id
            depth = 0

            while current and current not in visited:
                visited.add(current)
                delegation = (
                    session.query(Delegation)
                    .filter(
                        Delegation.delegate_id == current,
                        Delegation.domain == domain,
                        Delegation.is_active == True,
                    )
                    .first()
                )
                if delegation:
                    depth = max(depth, delegation.depth)
                    current = delegation.delegator_id
                else:
                    break

            return depth
        finally:
            if self._should_close():
                session.close()

    def _execute_delegate(self, manifest: dict) -> dict:
        payload = manifest.get("payload", {})
        actor_id = uuid.UUID(manifest.get("actor_id", manifest.get("proposal", {}).get("actor_id", "")))
        delegation_id = uuid.uuid4()

        self._engine._event_store.append_event(
            domain=self.DOMAIN,
            event_type="delegation_created",
            actor_id=actor_id,
            payload={
                "delegation_id": str(delegation_id),
                "delegator_id": str(actor_id),
                "delegate_id": payload.get("delegate_id"),
                "domain": payload.get("domain"),
                "scope": payload.get("scope", "full"),
                "depth": payload.get("depth", 1),
                "reason": payload.get("reason", ""),
            },
            manifest_id=uuid.UUID(manifest.get("manifest_id", str(uuid.uuid4()))),
        )
        return {"delegation_id": str(delegation_id), "status": "created"}

    def _execute_revoke(self, manifest: dict) -> dict:
        payload = manifest.get("payload", {})
        actor_id = uuid.UUID(manifest.get("actor_id", manifest.get("proposal", {}).get("actor_id", "")))

        self._engine._event_store.append_event(
            domain=self.DOMAIN,
            event_type="delegation_revoked",
            actor_id=actor_id,
            payload={
                "delegation_id": payload.get("delegation_id"),
                "reason": payload.get("reason", ""),
                "revoked_by": str(actor_id),
            },
            manifest_id=uuid.UUID(manifest.get("manifest_id", str(uuid.uuid4()))),
        )
        return {"delegation_id": payload.get("delegation_id"), "status": "revoked"}
