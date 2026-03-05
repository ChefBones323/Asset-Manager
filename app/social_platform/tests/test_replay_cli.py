from unittest.mock import MagicMock, patch
from app.social_platform.tools.replay_social_system import wipe_projection_tables, PROJECTION_TABLES


class TestReplayCLI:
    def test_projection_table_list_complete(self):
        expected = [
            "posts",
            "comments",
            "threads",
            "reaction_summary",
            "feed_index",
            "trust_profiles",
            "delegations",
            "knowledge_artifacts",
            "governance_proposals",
        ]
        assert PROJECTION_TABLES == expected

    def test_wipe_handles_missing_tables(self):
        session = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar.return_value = None
        session.execute.return_value = result_mock

        wiped = wipe_projection_tables(session)
        assert wiped == []
        session.commit.assert_called_once()

    def test_wipe_truncates_existing_tables(self):
        session = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar.return_value = "posts"
        session.execute.return_value = result_mock

        wiped = wipe_projection_tables(session)
        assert len(wiped) == len(PROJECTION_TABLES)
        session.commit.assert_called_once()

    @patch("app.social_platform.tools.replay_social_system.SessionLocal")
    @patch("app.social_platform.tools.replay_social_system.EventStore")
    @patch("app.social_platform.tools.replay_social_system.ProjectionEngine")
    def test_run_replay_returns_summary(self, mock_pe_cls, mock_es_cls, mock_session_cls):
        from app.social_platform.tools.replay_social_system import run_replay

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        result_mock = MagicMock()
        result_mock.scalar.return_value = None
        mock_session.execute.return_value = result_mock

        mock_es = MagicMock()
        mock_es.replay_events.return_value = []
        mock_es_cls.return_value = mock_es

        mock_pe = MagicMock()
        mock_pe_cls.return_value = mock_pe

        result = run_replay()

        assert result["events_processed"] == 0
        assert isinstance(result["projections_rebuilt"], list)
        assert "elapsed_seconds" in result

    @patch("app.social_platform.tools.replay_social_system.SessionLocal")
    @patch("app.social_platform.tools.replay_social_system.EventStore")
    @patch("app.social_platform.tools.replay_social_system.ProjectionEngine")
    def test_run_replay_processes_events(self, mock_pe_cls, mock_es_cls, mock_session_cls):
        from app.social_platform.tools.replay_social_system import run_replay

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        result_mock = MagicMock()
        result_mock.scalar.return_value = None
        mock_session.execute.return_value = result_mock

        fake_event_1 = MagicMock()
        fake_event_1.domain = "content"
        fake_event_1.event_type = "post_created"

        fake_event_2 = MagicMock()
        fake_event_2.domain = "trust"
        fake_event_2.event_type = "trust_updated"

        mock_es = MagicMock()
        mock_es.replay_events.return_value = [fake_event_1, fake_event_2]
        mock_es_cls.return_value = mock_es

        mock_pe = MagicMock()
        mock_pe_cls.return_value = mock_pe

        result = run_replay()

        assert result["events_processed"] == 2
        assert mock_pe.process_event.call_count == 2
        assert "content" in result["domains"]
        assert "trust" in result["domains"]
