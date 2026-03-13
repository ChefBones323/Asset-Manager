import uuid
import logging
from typing import Dict, Any, Optional

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.agent_runtime.prompt_loader import load_system_prompt, load_agent_config
from app.social_platform.agent_runtime.tool_registry import build_default_registry, ToolRegistry
from app.social_platform.agent_runtime.tool_router import ToolRouter, AUTO_APPROVER_ID
from app.social_platform.agent_runtime.policy_guard import PolicyGuard
from app.social_platform.agent_runtime.memory_service import MemoryService
from app.social_platform.agent_runtime.runtime_context import RuntimeContext
from app.social_platform.agent_runtime.scheduler_service import SchedulerService
from app.social_platform.platform.execution_engine import ExecutionEngine

logger = logging.getLogger("agent_runtime")

AGENT_ACTOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

TASK_PATTERNS = {
    "analyze_system": {
        "plan": ["Gather system metrics", "Query recent events", "Analyze patterns", "Report findings"],
        "tools": [
            {"tool": "filesystem_read", "args": {"path": "data/worker_status.json"}, "description": "Check system health"},
        ],
    },
    "diagnose_feed": {
        "plan": ["Read feed configuration", "Check recent content events", "Analyze ranking weights", "Identify issues"],
        "tools": [
            {"tool": "web_search", "args": {"query": "feed ranking analysis"}, "description": "Research feed patterns"},
        ],
    },
    "trace_event": {
        "plan": ["Identify target event", "Trace causal chain", "Map related events", "Build event graph"],
        "tools": [
            {"tool": "filesystem_read", "args": {"path": "data/events.json"}, "description": "Read event data"},
        ],
    },
    "default": {
        "plan": ["Parse user request", "Select appropriate tools", "Execute plan", "Verify results"],
        "tools": [],
    },
}


def _match_pattern(user_input: str) -> Dict[str, Any]:
    lower = user_input.lower()
    if "system" in lower or "health" in lower or "status" in lower:
        return TASK_PATTERNS["analyze_system"]
    if "feed" in lower or "ranking" in lower or "content" in lower:
        return TASK_PATTERNS["diagnose_feed"]
    if "event" in lower or "trace" in lower or "chain" in lower:
        return TASK_PATTERNS["trace_event"]
    return TASK_PATTERNS["default"]


class AgentRuntime:
    def __init__(self, event_store: Optional[EventStore] = None):
        self._event_store = event_store or EventStore()
        self._execution_engine = ExecutionEngine(self._event_store)
        self._config = load_agent_config()
        self._system_prompt = load_system_prompt()
        self._policy_guard = PolicyGuard()
        self._memory_service = MemoryService()
        self._registry = build_default_registry()
        self._tool_router = ToolRouter(self._registry, self._policy_guard, self._execution_engine)
        self._scheduler = SchedulerService()
        self._setup_default_scheduled_tasks()

        self._register_executors()

        if self._config.get("scheduler_enabled"):
            self._scheduler.start()

        logger.info("AgentRuntime initialized (max_iterations=%d)", self._config["max_iterations"])

    def _register_executors(self):
        def execute_store_memory(manifest: dict) -> dict:
            payload = manifest.get("payload", {})
            category = payload.get("category", "operational")
            key = payload.get("key", "")
            value = payload.get("value", "")
            result = self._memory_service.store(category=category, key=key, value=value)
            return {"status": "stored", "memory": result}

        def execute_delete_memory(manifest: dict) -> dict:
            payload = manifest.get("payload", {})
            memory_id = payload.get("memory_id", "")
            deleted = self._memory_service.delete(memory_id)
            return {"status": "deleted" if deleted else "not_found", "memory_id": memory_id}

        def _make_tool_executor(tool_name: str):
            def executor(manifest: dict) -> dict:
                payload = manifest.get("payload", {})
                args = payload.get("arguments", {})
                tool = self._registry.get(tool_name)
                if not tool:
                    return {"status": "error", "error": f"Tool '{tool_name}' not found"}
                return tool.execute(**args)
            return executor

        self._execution_engine.register_executor("store_memory", execute_store_memory)
        self._execution_engine.register_executor("delete_memory", execute_delete_memory)

        for tool_spec in self._registry.list_tools():
            action_name = f"tool_{tool_spec['name']}"
            self._execution_engine.register_executor(
                action_name, _make_tool_executor(tool_spec["name"])
            )

    def _setup_default_scheduled_tasks(self):
        scheduled_tasks = self._config.get("scheduled_tasks", {})
        worker_health_interval = scheduled_tasks.get("monitor_worker_health_interval", 300)
        governance_report_interval = scheduled_tasks.get("generate_governance_report_interval", 86400)

        self._scheduler.register_task(
            task_id="monitor_worker_health",
            name="Monitor Worker Health",
            handler=self._check_worker_health,
            interval_seconds=worker_health_interval,
            description=f"Check worker heartbeats and active leases every {worker_health_interval}s",
        )
        self._scheduler.register_task(
            task_id="generate_governance_report",
            name="Generate Governance Report",
            handler=self._generate_governance_summary,
            interval_seconds=governance_report_interval,
            description=f"Generate governance report summary every {governance_report_interval}s",
        )

    def _check_worker_health(self) -> Dict[str, Any]:
        try:
            events = self._event_store.get_events_by_domain("workers", limit=10)
            return {
                "status": "healthy",
                "recent_worker_events": len(events),
                "checked_at": "now",
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _generate_governance_summary(self) -> Dict[str, Any]:
        try:
            events = self._event_store.get_events_by_domain("governance", limit=50)
            proposals = [e for e in events if e.event_type == "proposal_created"]
            return {
                "total_governance_events": len(events),
                "proposals_created": len(proposals),
                "generated_at": "now",
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def run_task(self, user_input: str) -> Dict[str, Any]:
        context = RuntimeContext(user_input, self._event_store, self._memory_service)
        pattern = _match_pattern(user_input)
        context.plan = list(pattern["plan"])
        max_iterations = self._config["max_iterations"]

        self._event_store.append_event(
            domain="agent_runtime",
            event_type="task_started",
            actor_id=AGENT_ACTOR_ID,
            payload={"user_input": user_input, "plan": context.plan},
        )

        for step in range(min(len(pattern["tools"]), max_iterations)):
            tool_spec = pattern["tools"][step]
            tool_call = {
                "step": step + 1,
                "tool": tool_spec["tool"],
                "args": tool_spec["args"],
                "description": tool_spec.get("description", ""),
            }

            result = self._tool_router.route(tool_spec["tool"], tool_spec["args"])
            context.update(tool_call, result)

            if result.get("status") == "error":
                context.mark_error(result.get("error", "Unknown error"))
                break

        if not context.completed:
            context.mark_complete()

        if self._config.get("memory_enabled"):
            memory_key = f"task_{uuid.uuid4().hex[:8]}"
            memory_value = f"Task: {user_input[:100]} | Steps: {context.iteration} | Status: {'error' if context.error else 'complete'}"
            try:
                proposal = self._execution_engine.submit_proposal(
                    actor_id=AGENT_ACTOR_ID,
                    domain="agent_runtime",
                    action="store_memory",
                    payload={
                        "category": "operational",
                        "key": memory_key,
                        "value": memory_value,
                    },
                    description=f"Agent stores operational memory for task: {user_input[:60]}",
                )
                proposal_id = proposal["proposal_id"]

                self._execution_engine.approve(
                    proposal_id=proposal_id,
                    approver_id=AUTO_APPROVER_ID,
                    reason="Auto-approved: operational memory write for task result",
                )

                execution_result = self._execution_engine.execute(
                    proposal_id=proposal_id,
                    worker_id=f"agent_worker_{AGENT_ACTOR_ID.hex[:8]}",
                )

                context.tool_calls.append({
                    "step": context.iteration + 1,
                    "tool": "memory_store",
                    "args": {"category": "operational", "key": memory_key},
                    "description": "Store task result in agent memory",
                })
                context.results.append({
                    "status": "success",
                    "proposal_id": proposal_id,
                    "execution_id": execution_result.get("execution_id"),
                    "approval": "auto",
                    "message": "Memory stored via governed pipeline (proposal → approve → execute).",
                })
            except Exception as exc:
                logger.warning(f"Failed to store memory via governance pipeline: {exc}")

        self._event_store.append_event(
            domain="agent_runtime",
            event_type="task_completed",
            actor_id=AGENT_ACTOR_ID,
            payload={
                "user_input": user_input,
                "steps": context.iteration,
                "error": context.error,
            },
        )

        confidence = self._compute_confidence(context)

        return {
            "status": "error" if context.error else "completed",
            "user_input": user_input,
            "plan": context.plan,
            "tool_calls": context.tool_calls,
            "results": context.results,
            "steps_executed": context.iteration,
            "confidence": confidence,
            "error": context.error,
            "system_prompt": self._system_prompt[:100],
        }

    @staticmethod
    def _compute_confidence(context: RuntimeContext) -> float:
        base = float(load_agent_config().get("default_confidence", 0.75))
        error_count = sum(1 for r in context.results if r.get("status") == "error")
        success_count = sum(1 for r in context.results if r.get("status") == "success")
        proposal_count = sum(1 for r in context.results if r.get("status") == "proposal_created")

        if context.error:
            base -= 0.3
        if error_count > 0:
            base -= 0.1 * error_count
        if success_count > 0:
            base += 0.05 * min(success_count, 3)
        if proposal_count > 0:
            base -= 0.05 * proposal_count

        return round(max(0.0, min(1.0, base)), 2)

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._registry

    @property
    def policy_guard(self) -> PolicyGuard:
        return self._policy_guard

    @property
    def memory_service(self) -> MemoryService:
        return self._memory_service

    @property
    def scheduler(self) -> SchedulerService:
        return self._scheduler

    @property
    def execution_engine(self) -> ExecutionEngine:
        return self._execution_engine
