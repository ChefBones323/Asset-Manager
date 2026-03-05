import uuid
from typing import Optional

from app.social_platform.platform.execution_engine import ExecutionEngine


class ContentService:
    DOMAIN = "content"

    def __init__(self, execution_engine: ExecutionEngine):
        self._engine = execution_engine
        self._engine.register_executor("create_post", self._execute_create_post)
        self._engine.register_executor("create_comment", self._execute_create_comment)
        self._engine.register_executor("add_reaction", self._execute_add_reaction)
        self._engine.register_executor("share_post", self._execute_share_post)

    def create_post(
        self,
        actor_id: uuid.UUID,
        content: str,
        content_type: str = "text",
        metadata: Optional[dict] = None,
    ) -> dict:
        payload = {
            "content": content,
            "content_type": content_type,
            "metadata": metadata or {},
        }
        return self._engine.submit_proposal(
            actor_id=actor_id,
            domain=self.DOMAIN,
            action="create_post",
            payload=payload,
            description=f"Create {content_type} post",
        )

    def create_comment(
        self,
        actor_id: uuid.UUID,
        post_id: uuid.UUID,
        content: str,
        parent_comment_id: Optional[uuid.UUID] = None,
    ) -> dict:
        payload = {
            "post_id": str(post_id),
            "content": content,
            "parent_comment_id": str(parent_comment_id) if parent_comment_id else None,
        }
        return self._engine.submit_proposal(
            actor_id=actor_id,
            domain=self.DOMAIN,
            action="create_comment",
            payload=payload,
            description=f"Comment on post {post_id}",
        )

    def add_reaction(
        self,
        actor_id: uuid.UUID,
        target_id: uuid.UUID,
        target_type: str,
        reaction_type: str,
    ) -> dict:
        payload = {
            "target_id": str(target_id),
            "target_type": target_type,
            "reaction_type": reaction_type,
        }
        return self._engine.submit_proposal(
            actor_id=actor_id,
            domain=self.DOMAIN,
            action="add_reaction",
            payload=payload,
            description=f"React ({reaction_type}) to {target_type} {target_id}",
        )

    def share_post(
        self,
        actor_id: uuid.UUID,
        post_id: uuid.UUID,
        comment: str = "",
    ) -> dict:
        payload = {
            "post_id": str(post_id),
            "comment": comment,
        }
        return self._engine.submit_proposal(
            actor_id=actor_id,
            domain=self.DOMAIN,
            action="share_post",
            payload=payload,
            description=f"Share post {post_id}",
        )

    def _execute_create_post(self, manifest: dict) -> dict:
        payload = manifest.get("payload", {})
        post_id = uuid.uuid4()
        actor_id = uuid.UUID(manifest.get("actor_id", manifest.get("proposal", {}).get("actor_id", "")))

        self._engine._event_store.append_event(
            domain=self.DOMAIN,
            event_type="content_created",
            actor_id=actor_id,
            payload={
                "post_id": str(post_id),
                "content": payload.get("content", ""),
                "content_type": payload.get("content_type", "text"),
                "metadata": payload.get("metadata", {}),
                "author_id": str(actor_id),
            },
            manifest_id=uuid.UUID(manifest.get("manifest_id", str(uuid.uuid4()))),
        )
        return {"post_id": str(post_id), "status": "created"}

    def _execute_create_comment(self, manifest: dict) -> dict:
        payload = manifest.get("payload", {})
        comment_id = uuid.uuid4()
        actor_id = uuid.UUID(manifest.get("actor_id", manifest.get("proposal", {}).get("actor_id", "")))

        self._engine._event_store.append_event(
            domain=self.DOMAIN,
            event_type="comment_created",
            actor_id=actor_id,
            payload={
                "comment_id": str(comment_id),
                "post_id": payload.get("post_id"),
                "content": payload.get("content", ""),
                "parent_comment_id": payload.get("parent_comment_id"),
                "author_id": str(actor_id),
            },
            manifest_id=uuid.UUID(manifest.get("manifest_id", str(uuid.uuid4()))),
        )
        return {"comment_id": str(comment_id), "status": "created"}

    def _execute_add_reaction(self, manifest: dict) -> dict:
        payload = manifest.get("payload", {})
        actor_id = uuid.UUID(manifest.get("actor_id", manifest.get("proposal", {}).get("actor_id", "")))

        self._engine._event_store.append_event(
            domain=self.DOMAIN,
            event_type="reaction_added",
            actor_id=actor_id,
            payload={
                "target_id": payload.get("target_id"),
                "target_type": payload.get("target_type"),
                "reaction_type": payload.get("reaction_type"),
                "reactor_id": str(actor_id),
            },
            manifest_id=uuid.UUID(manifest.get("manifest_id", str(uuid.uuid4()))),
        )
        return {"status": "reaction_added"}

    def _execute_share_post(self, manifest: dict) -> dict:
        payload = manifest.get("payload", {})
        share_id = uuid.uuid4()
        actor_id = uuid.UUID(manifest.get("actor_id", manifest.get("proposal", {}).get("actor_id", "")))

        self._engine._event_store.append_event(
            domain=self.DOMAIN,
            event_type="post_shared",
            actor_id=actor_id,
            payload={
                "share_id": str(share_id),
                "post_id": payload.get("post_id"),
                "comment": payload.get("comment", ""),
                "sharer_id": str(actor_id),
            },
            manifest_id=uuid.UUID(manifest.get("manifest_id", str(uuid.uuid4()))),
        )
        return {"share_id": str(share_id), "status": "shared"}
