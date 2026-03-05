import uuid
from unittest.mock import MagicMock, patch, call

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.models.event_models import Event, AuditLog


class TestEventStoreTransaction:
    def test_append_event_adds_both_event_and_audit_log(self):
        session = MagicMock()
        store = EventStore(session=session)

        store.append_event(
            domain="test",
            event_type="something_happened",
            actor_id=uuid.uuid4(),
            payload={"resource_type": "post", "resource_id": "abc"},
        )

        add_calls = session.add.call_args_list
        assert len(add_calls) == 2

        added_types = [type(c[0][0]) for c in add_calls]
        assert Event in added_types
        assert AuditLog in added_types

        session.commit.assert_called_once()

    def test_append_event_rollbacks_on_failure(self):
        session = MagicMock()
        session.commit.side_effect = Exception("db error")
        store = EventStore(session=session)

        try:
            store.append_event(
                domain="test",
                event_type="fail_event",
                actor_id=uuid.uuid4(),
                payload={},
            )
        except Exception:
            pass

        session.rollback.assert_called_once()

    def test_audit_log_references_same_event_id(self):
        session = MagicMock()
        store = EventStore(session=session)

        store.append_event(
            domain="content",
            event_type="post_created",
            actor_id=uuid.uuid4(),
            payload={"resource_id": "post-123"},
        )

        add_calls = session.add.call_args_list
        event_obj = add_calls[0][0][0]
        audit_obj = add_calls[1][0][0]

        assert event_obj.event_id == audit_obj.event_id

    def test_audit_log_extracts_resource_fields_from_payload(self):
        session = MagicMock()
        store = EventStore(session=session)

        store.append_event(
            domain="content",
            event_type="post_created",
            actor_id=uuid.uuid4(),
            payload={"resource_type": "post", "resource_id": "post-456"},
        )

        audit_obj = session.add.call_args_list[1][0][0]
        assert audit_obj.resource_type == "post"
        assert audit_obj.resource_id == "post-456"

    def test_single_commit_for_both_records(self):
        session = MagicMock()
        store = EventStore(session=session)

        store.append_event(
            domain="test",
            event_type="test_event",
            actor_id=uuid.uuid4(),
            payload={},
        )

        assert session.commit.call_count == 1
        assert session.add.call_count == 2
