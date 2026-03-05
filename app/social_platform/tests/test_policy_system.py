import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.social_platform.policies.policy_validator import validate_policy, validate_policy_strict, PolicyValidationError
from app.social_platform.policies.policy_registry import PolicyRegistry, PolicyAlreadyPublishedError, PolicyNotFoundError
from app.social_platform.policies.feed_policy_manifest import FeedPolicyManifest, SYSTEM_DEFAULT_POLICY


class TestPolicyValidator:
    def test_valid_policy_passes(self):
        policy = {
            "policy_id": "test_policy",
            "timestamp_weight": 0.40,
            "reaction_weight": 0.25,
            "trust_weight": 0.20,
            "policy_weight": 0.15,
            "max_age_hours": 72,
            "min_trust_threshold": -20,
        }
        errors = validate_policy(policy)
        assert errors == []

    def test_weights_must_sum_to_one(self):
        policy = {
            "policy_id": "bad_weights",
            "timestamp_weight": 0.50,
            "reaction_weight": 0.50,
            "trust_weight": 0.50,
            "policy_weight": 0.50,
        }
        errors = validate_policy(policy)
        assert any("sum to 1.0" in e for e in errors)

    def test_negative_weights_rejected(self):
        policy = {
            "policy_id": "neg_weight",
            "timestamp_weight": -0.1,
            "reaction_weight": 0.5,
            "trust_weight": 0.3,
            "policy_weight": 0.3,
        }
        errors = validate_policy(policy)
        assert any("non-negative" in e for e in errors)

    def test_missing_policy_id(self):
        policy = {
            "timestamp_weight": 0.25,
            "reaction_weight": 0.25,
            "trust_weight": 0.25,
            "policy_weight": 0.25,
        }
        errors = validate_policy(policy)
        assert any("policy_id" in e for e in errors)

    def test_duplicate_policy_id_rejected(self):
        policy = {
            "policy_id": "existing",
            "timestamp_weight": 0.25,
            "reaction_weight": 0.25,
            "trust_weight": 0.25,
            "policy_weight": 0.25,
        }
        errors = validate_policy(policy, existing_ids={"existing"})
        assert any("already exists" in e for e in errors)

    def test_max_age_must_be_positive(self):
        policy = {
            "policy_id": "bad_age",
            "timestamp_weight": 0.25,
            "reaction_weight": 0.25,
            "trust_weight": 0.25,
            "policy_weight": 0.25,
            "max_age_hours": -1,
        }
        errors = validate_policy(policy)
        assert any("positive" in e for e in errors)

    def test_strict_raises_exception(self):
        policy = {"policy_id": "", "timestamp_weight": 2.0, "reaction_weight": 0, "trust_weight": 0, "policy_weight": 0}
        with pytest.raises(PolicyValidationError) as exc_info:
            validate_policy_strict(policy)
        assert len(exc_info.value.errors) > 0


class TestPolicyRegistry:
    def test_default_policy_exists(self):
        registry = PolicyRegistry()
        policy = registry.get_policy("system_default")
        assert policy is not None
        assert policy["policy_id"] == "system_default"
        assert policy["approved"] is True

    def test_register_and_get_policy(self):
        registry = PolicyRegistry()
        policy = {
            "policy_id": "test_reg",
            "timestamp_weight": 0.25,
            "reaction_weight": 0.25,
            "trust_weight": 0.25,
            "policy_weight": 0.25,
        }
        result = registry.register_policy(policy, approved=True)
        assert result["policy_id"] == "test_reg"
        assert result["approved"] is True

        retrieved = registry.get_policy("test_reg")
        assert retrieved is not None

    def test_list_policies(self):
        registry = PolicyRegistry()
        policies = registry.list_policies()
        assert len(policies) >= 1
        assert any(p["policy_id"] == "system_default" for p in policies)

    def test_immutable_after_publish(self):
        registry = PolicyRegistry()
        policy = {
            "policy_id": "immutable_test",
            "timestamp_weight": 0.25,
            "reaction_weight": 0.25,
            "trust_weight": 0.25,
            "policy_weight": 0.25,
        }
        registry.register_policy(policy, approved=True)

        with pytest.raises(PolicyAlreadyPublishedError):
            registry.register_policy(policy, approved=True)

    def test_approve_policy(self):
        registry = PolicyRegistry()
        policy = {
            "policy_id": "pending_pol",
            "timestamp_weight": 0.25,
            "reaction_weight": 0.25,
            "trust_weight": 0.25,
            "policy_weight": 0.25,
        }
        registry.register_policy(policy, approved=False)

        assert registry.get_active_policy("pending_pol") is None

        result = registry.approve_policy("pending_pol")
        assert result["approved"] is True

        assert registry.get_active_policy("pending_pol") is not None

    def test_approve_nonexistent_raises(self):
        registry = PolicyRegistry()
        with pytest.raises(PolicyNotFoundError):
            registry.approve_policy("nonexistent")

    def test_resolve_defaults_to_system(self):
        registry = PolicyRegistry()
        policy = registry.resolve_policy()
        assert policy["policy_id"] == "system_default"

    def test_resolve_community_policy(self):
        registry = PolicyRegistry()
        policy = {
            "policy_id": "community_abc",
            "timestamp_weight": 0.30,
            "reaction_weight": 0.30,
            "trust_weight": 0.20,
            "policy_weight": 0.20,
        }
        registry.register_policy(policy, approved=True)

        resolved = registry.resolve_policy(community_id="abc")
        assert resolved["policy_id"] == "community_abc"


class TestFeedPolicyManifest:
    def test_manifest_creation(self):
        manifest = FeedPolicyManifest(
            policy_id="test_manifest",
            timestamp_weight=0.40,
            reaction_weight=0.25,
            trust_weight=0.20,
            policy_weight=0.15,
        )
        assert manifest.policy_id == "test_manifest"
        assert manifest.version is not None
        assert len(manifest.version) == 16

    def test_to_dict(self):
        manifest = FeedPolicyManifest(policy_id="dict_test")
        d = manifest.to_dict()
        assert "policy_id" in d
        assert "version" in d
        assert "created_at" in d

    def test_to_ranking_manifest(self):
        manifest = FeedPolicyManifest(
            policy_id="rank_test",
            timestamp_weight=0.40,
            reaction_weight=0.25,
            trust_weight=0.20,
            policy_weight=0.15,
        )
        rm = manifest.to_ranking_manifest()
        assert rm["policy_weight_factor"] == 0.15
        assert rm["manifest_id"] == manifest.version

    def test_from_dict_roundtrip(self):
        original = FeedPolicyManifest(
            policy_id="roundtrip",
            timestamp_weight=0.30,
            reaction_weight=0.30,
            trust_weight=0.20,
            policy_weight=0.20,
        )
        d = original.to_dict()
        restored = FeedPolicyManifest.from_dict(d)
        assert restored.policy_id == original.policy_id
        assert restored.version == original.version

    def test_deterministic_version(self):
        m1 = FeedPolicyManifest(policy_id="det", timestamp_weight=0.5, reaction_weight=0.2, trust_weight=0.2, policy_weight=0.1)
        m2 = FeedPolicyManifest(policy_id="det", timestamp_weight=0.5, reaction_weight=0.2, trust_weight=0.2, policy_weight=0.1)
        assert m1.version == m2.version

    def test_system_default_exists(self):
        assert SYSTEM_DEFAULT_POLICY.policy_id == "system_default"
        assert SYSTEM_DEFAULT_POLICY.version is not None


class TestPolicyAwareFeedGeneration:
    def test_worker_resolves_registry_policy(self):
        from app.social_platform.workers.feed_generate_worker import FeedGenerateWorker
        worker = FeedGenerateWorker.__new__(FeedGenerateWorker)
        from app.social_platform.policies.feed_policy_engine import FeedPolicyEngine
        worker._policy_engine = FeedPolicyEngine()
        worker._session = None

        manifest = worker._resolve_policy_manifest()
        assert manifest is not None
        assert "timestamp_weight" in manifest
        assert "policy_weight_factor" in manifest

    def test_worker_uses_explicit_manifest_over_registry(self):
        from app.social_platform.workers.feed_generate_worker import FeedGenerateWorker
        worker = FeedGenerateWorker.__new__(FeedGenerateWorker)
        from app.social_platform.policies.feed_policy_engine import FeedPolicyEngine
        worker._policy_engine = FeedPolicyEngine()
        worker._session = None

        explicit = {"timestamp_weight": 0.99, "reaction_weight": 0.01, "trust_weight": 0.0, "policy_weight_factor": 0.0}
        result = worker._resolve_policy_manifest(policy_manifest=explicit)
        assert result is explicit


class TestPolicyExplainIntegration:
    def test_explain_includes_policy_metadata(self):
        user_id = uuid.uuid4()
        cid = uuid.uuid4()

        entry = MagicMock()
        entry.content_id = cid
        entry.feed_owner = user_id
        entry.reaction_count = 5
        entry.trust_score = 0.5
        entry.policy_weight = 1.0
        entry.distribution_time = datetime(2024, 7, 1, tzinfo=timezone.utc)
        entry.policy_scope = "default"

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [entry]
        mock_session.query.return_value = mock_query
        mock_session.execute.return_value = None

        from app.social_platform.domains.social.feed_explain_service import FeedExplainService
        service = FeedExplainService(session=mock_session)
        result = service.explain(user_id, cid)

        assert "policy_id" in result
        assert "policy_version" in result
        assert result["policy_id"] is not None

    def test_explain_never_mutates(self):
        user_id = uuid.uuid4()
        cid = uuid.uuid4()

        entry = MagicMock()
        entry.content_id = cid
        entry.feed_owner = user_id
        entry.reaction_count = 5
        entry.trust_score = 0.5
        entry.policy_weight = 1.0
        entry.distribution_time = datetime(2024, 7, 1, tzinfo=timezone.utc)
        entry.policy_scope = "default"

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [entry]
        mock_session.query.return_value = mock_query
        mock_session.execute.return_value = None

        from app.social_platform.domains.social.feed_explain_service import FeedExplainService
        service = FeedExplainService(session=mock_session)
        service.explain(user_id, cid)

        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()


class TestPolicyGovernanceFlow:
    def test_propose_route_uses_governance_service(self):
        from app.social_platform.admin.feed_policies import propose_feed_policy, CreatePolicyProposalRequest
        import asyncio

        actor_id = str(uuid.uuid4())
        request = CreatePolicyProposalRequest(
            actor_id=actor_id,
            policy_id="gov_test_pol",
            timestamp_weight=0.25,
            reaction_weight=0.25,
            trust_weight=0.25,
            policy_weight=0.25,
            description="Test governance flow",
        )

        with patch("app.social_platform.admin.feed_policies._get_execution_engine") as mock_engine_fn:
            mock_engine = MagicMock()
            mock_engine.submit_proposal.return_value = {
                "proposal_id": str(uuid.uuid4()),
                "status": "pending",
            }
            mock_engine_fn.return_value = mock_engine

            mock_gov = MagicMock()
            mock_gov.create_governance_proposal.return_value = {
                "governance_proposal_id": str(uuid.uuid4()),
                "status": "created",
            }

            with patch("app.social_platform.admin.feed_policies.GovernanceService", return_value=mock_gov):
                result = asyncio.get_event_loop().run_until_complete(propose_feed_policy(request))

            assert result["status"] == "proposed"
            mock_gov.create_governance_proposal.assert_called_once()
            call_kwargs = mock_gov.create_governance_proposal.call_args
            assert call_kwargs[1]["proposal_type"] == "create_feed_policy"
            assert call_kwargs[1]["domain"] == "feed_policy"

    def test_approve_route_emits_event_via_event_store(self):
        from app.social_platform.admin.feed_policies import approve_feed_policy
        import asyncio

        actor_id = str(uuid.uuid4())
        policy_id = "test_approve_pol"

        mock_registry = MagicMock()
        mock_registry.get_policy.return_value = {
            "policy_id": policy_id,
            "status": "pending_approval",
        }

        with patch("app.social_platform.admin.feed_policies.get_global_registry", return_value=mock_registry):
            with patch("app.social_platform.admin.feed_policies._get_execution_engine") as mock_engine_fn:
                mock_engine = MagicMock()
                mock_event_store = MagicMock()
                mock_engine._event_store = mock_event_store
                mock_engine_fn.return_value = mock_engine

                with patch("app.social_platform.admin.feed_policies.GovernanceService"):
                    result = asyncio.get_event_loop().run_until_complete(
                        approve_feed_policy(policy_id, actor_id)
                    )

        assert result["status"] == "approved"
        mock_event_store.append_event.assert_called_once()
        call_kwargs = mock_event_store.append_event.call_args
        assert call_kwargs[1]["event_type"] == "feed_policy_approved"
        assert call_kwargs[1]["domain"] == "feed_policy"

    def test_policy_worker_handles_feed_policy_proposed(self):
        from app.social_platform.workers.policy_worker import PolicyWorker

        mock_projection_engine = MagicMock()
        worker = PolicyWorker(mock_projection_engine)

        mock_event = MagicMock()
        mock_event.payload = {
            "proposal_type": "create_feed_policy",
            "policy": {
                "policy_id": "worker_handled_pol",
                "timestamp_weight": 0.25,
                "reaction_weight": 0.25,
                "trust_weight": 0.25,
                "policy_weight": 0.25,
            },
        }

        worker._handle_feed_policy_proposed(mock_event)

        from app.social_platform.policies.policy_registry import get_global_registry
        registry = get_global_registry()
        policy = registry.get_policy("worker_handled_pol")
        assert policy is not None
        assert policy["approved"] is False

    def test_policy_worker_handles_feed_policy_approved(self):
        from app.social_platform.workers.policy_worker import PolicyWorker
        from app.social_platform.policies.policy_registry import get_global_registry

        registry = get_global_registry()
        registry.register_policy({
            "policy_id": "to_approve_pol",
            "timestamp_weight": 0.25,
            "reaction_weight": 0.25,
            "trust_weight": 0.25,
            "policy_weight": 0.25,
        }, approved=False)

        assert registry.get_active_policy("to_approve_pol") is None

        mock_projection_engine = MagicMock()
        worker = PolicyWorker(mock_projection_engine)

        mock_event = MagicMock()
        mock_event.payload = {
            "policy_id": "to_approve_pol",
            "approved_by": str(uuid.uuid4()),
        }

        worker._handle_feed_policy_approved(mock_event)

        policy = registry.get_active_policy("to_approve_pol")
        assert policy is not None
        assert policy["approved"] is True

    def test_policy_worker_registers_both_handlers(self):
        from app.social_platform.workers.policy_worker import PolicyWorker

        mock_projection_engine = MagicMock()
        PolicyWorker(mock_projection_engine)

        registered_event_types = [
            call[0][0] for call in mock_projection_engine.register_handler.call_args_list
        ]
        assert "feed_policy_proposed" in registered_event_types
        assert "feed_policy_approved" in registered_event_types
