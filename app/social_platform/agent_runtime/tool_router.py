import uuid
import logging
from typing import Dict, Any, Optional

from app.social_platform.agent_runtime.policy_guard import PolicyGuard, ApprovalLevel
from app.social_platform.agent_runtime.tool_registry import ToolRegistry
from app.social_platform.platform.execution_engine import ExecutionEngine

logger = logging.getLogger("agent_runtime.tool_router")

AGENT_ACTOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


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

        if level == ApprovalLevel.AUTO:
            return self._execute_directly(tool_name, args)
        else:
            return self._route_through_pipeline(tool_name, args, permission)

    def _execute_directly(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._registry.get(tool_name)
        if not tool:
            return {"status": "error", "error": f"Tool not found: {tool_name}"}
        try:
            result = tool.execute(**args)
            logger.info(f"Tool '{tool_name}' executed directly (auto-approved)")
            return {"status": "success", "tool": tool_name, "result": result, "approval": "auto"}
        except Exception as exc:
            logger.error(f"Tool '{tool_name}' failed: {exc}")
            return {"status": "error", "tool": tool_name, "error": str(exc)}

    def _route_through_pipeline(
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

            return {
                "status": "proposal_created",
                "tool": tool_name,
                "proposal_id": proposal["proposal_id"],
                "approval_level": permission["approval_level"],
                "requires_human_approval": True,
                "message": f"Tool '{tool_name}' requires {permission['approval_level']} approval. "
                           f"Proposal {proposal['proposal_id']} submitted for review.",
            }
        except Exception as exc:
            logger.error(f"Failed to create proposal for tool '{tool_name}': {exc}")
            return {"status": "error", "tool": tool_name, "error": str(exc)}
