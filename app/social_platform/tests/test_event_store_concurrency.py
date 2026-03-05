import uuid
from unittest.mock import MagicMock, patch, PropertyMock
from sqlalchemy.exc import OperationalError

from app.social_platform.infrastructure.event_store import (
    EventStore,
    SerializationConflictError,
    SERIALIZATION_RETRY_LIMIT,
)
from app.social_platform.models.event_models import Event, AuditLog


class FakeOrigError:
    def __init__(self, msg):
        self._msg = msg

    def __str__(self):
        return self._msg


class TestEventStoreConcurrency:
    def test_sets_serializable_isolation(self):
        session = MagicMock()
        store = EventStore(session=session)

        store.append_event(
            domain="test",
            event_type="test_event",
            actor_id=uuid.uuid4(),
            payload={},
        )

        execute_calls = session.execute.call_args_list
        isolation_set = any(
            "SERIALIZABLE" in str(call[0][0].text if hasattr(call[0][0], "text") else call[0][0])
            for call in execute_calls
            if call[0]
        )
        assert isolation_set, "SERIALIZABLE isolation level not set"

    def test_retries_on_serialization_failure(self):
        session = MagicMock()
        store = EventStore(session=session)

        orig_error = FakeOrigError("could not serialize access")
        fail_exc = OperationalError("stmt", {}, orig_error)

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise fail_exc

        session.commit.side_effect = side_effect

        store.append_event(
            domain="test",
            event_type="retry_test",
            actor_id=uuid.uuid4(),
            payload={},
        )

        assert session.commit.call_count == 2
        assert session.rollback.call_count == 1

    def test_raises_after_max_retries(self):
        session = MagicMock()
        store = EventStore(session=session)

        orig_error = FakeOrigError("could not serialize access")
        fail_exc = OperationalError("stmt", {}, orig_error)
        session.commit.side_effect = fail_exc

        try:
            store.append_event(
                domain="test",
                event_type="fail_test",
                actor_id=uuid.uuid4(),
                payload={},
            )
            assert False, "Should have raised"
        except SerializationConflictError as exc:
            assert "serialize" in str(exc).lower()

        assert session.commit.call_count == SERIALIZATION_RETRY_LIMIT
        assert session.rollback.call_count == SERIALIZATION_RETRY_LIMIT

    def test_non_serialization_error_raises_immediately(self):
        session = MagicMock()
        store = EventStore(session=session)

        session.commit.side_effect = ValueError("unrelated error")

        try:
            store.append_event(
                domain="test",
                event_type="other_fail",
                actor_id=uuid.uuid4(),
                payload={},
            )
            assert False, "Should have raised"
        except ValueError as exc:
            assert "unrelated" in str(exc)

        assert session.commit.call_count == 1

    def test_dual_write_preserved_with_serializable(self):
        session = MagicMock()
        store = EventStore(session=session)

        store.append_event(
            domain="test",
            event_type="dual_write",
            actor_id=uuid.uuid4(),
            payload={"resource_id": "abc"},
        )

        add_calls = session.add.call_args_list
        assert len(add_calls) == 2
        types = [type(c[0][0]) for c in add_calls]
        assert Event in types
        assert AuditLog in types
        session.commit.assert_called_once()
