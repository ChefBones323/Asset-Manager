import uuid
import logging
from typing import Dict, Any, Optional

from app.social_platform.agent_runtime.policy_guard import PolicyGuard, ApprovalLevel
from app.social_platform.agent_runtime.tool_registry import ToolRegistry
from app.social_platform.platform.execution_engine import ExecutionEngine

logger = logging.getLogger("agent_runtime.tool_router")

AGENT_ACTOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
AUTO_APPROVER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


class ToolRouter:
    def __init__(
        self,
        registry: ToolRegistry,
        policy_guard: PolicyGuard,
        execution_engine: ExecutionEngine,
    ):
        self._registry = registry
        self._policy_guard = policy_guard
        self._execution_engine = execution_engine

    def route(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._registry.get(tool_name)
        if not tool:
            return {"status": "error", "error": f"Unknown tool: {tool_name}"}

        permission = self._policy_guard.check_permission(tool_name)
        level = self._policy_guard.get_approval_level(tool_name)

        proposal = self._submit_proposal(tool_name, args, permission)
        if proposal.get("status") == "error":
            return proposal

        proposal_id = proposal["proposal_id"]

        if level == ApprovalLevel.AUTO:
            return self._auto_approve_and_execute(tool_name, proposal_id, permission)
        else:
            return {
                "status": "proposal_created",
                "tool": tool_name,
                "proposal_id": proposal_id,
                "approval_level": permission["approval_level"],
                "requires_human_approval": True,
                "message": f"Tool '{tool_name}' requires {permission['approval_level']} approval. "
                           f"Proposal {proposal_id} submitted for review.",
            }

    def _submit_proposal(
        self, tool_name: str, args: Dict[str, Any], permission: Dict
    ) -> Dict[str, Any]:
        try:
            proposal = self._execution_engine.submit_proposal(
                actor_id=AGENT_ACTOR_ID,
                domain="agent_runtime",
                action=f"tool_{tool_name}",
                payload={
                    "tool_name": tool_name,
                    "arguments": args,
                    "approval_level": permission["approval_level"],
                    "is_destructive": permission["is_destructive"],
                },
                description=f"Agent requests execution of tool '{tool_name}' with args: {list(args.keys())}",
            )
            logger.info(
                f"Proposal {proposal['proposal_id']} created for tool '{tool_name}' "
                f"(approval_level={permission['approval_level']})"
            )
            return proposal
        except Exception as exc:
            logger.error(f"Failed to create proposal for tool '{tool_name}': {exc}")
            return {"status": "error", "tool": tool_name, "error": str(exc)}

    def _auto_approve_and_execute(
        self, tool_name: str, proposal_id: str, permission: Dict
    ) -> Dict[str, Any]:
        try:
            self._execution_engine.approve(
                proposal_id=proposal_id,
                approver_id=AUTO_APPROVER_ID,
                reason=f"Auto-approved: tool '{tool_name}' has approval_level=auto",
            )

            execution_result = self._execution_engine.execute(
                proposal_id=proposal_id,
                worker_id=f"agent_worker_{AGENT_ACTOR_ID.hex[:8]}",
            )

            logger.info(f"Tool '{tool_name}' auto-approved and executed via governance pipeline")
            return {
                "status": "success",
                "tool": tool_name,
                "result": execution_result.get("result", {}),
                "approval": "auto",
                "proposal_id": proposal_id,
                "execution_id": execution_result.get("execution_id"),
            }
        except Exception as exc:
            logger.error(f"Auto-approved execution of '{tool_name}' failed: {exc}")
            return {"status": "error", "tool": tool_name, "error": str(exc)}
