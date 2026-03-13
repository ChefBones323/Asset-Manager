import os
from typing import Dict, Any

from app.social_platform.agent_runtime.tool_registry import ToolSpec


SANDBOX_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

VIRTUAL_PATHS = {
    "data/worker_status.json",
    "data/governance_proposals.json",
    "data/feed_config.json",
    "data/events.json",
}


def _resolve_safe_path(path: str) -> tuple[str, bool]:
    normalized = os.path.normpath(path.lstrip("/"))
    if ".." in normalized.split(os.sep):
        return "", False
    abs_path = os.path.abspath(os.path.join(SANDBOX_ROOT, normalized))
    if not abs_path.startswith(SANDBOX_ROOT):
        return "", False
    return abs_path, True


def execute(path: str, **kwargs) -> Dict[str, Any]:
    resolved, is_safe = _resolve_safe_path(path)
    if not is_safe:
        return {"status": "error", "error": "Path traversal not allowed", "path": path}

    if not os.path.exists(resolved):
        return {
            "status": "simulated",
            "path": path,
            "content": f"[Simulated read of '{path}' — file not found in sandbox]",
            "exists": False,
        }

    try:
        with open(resolved, "r") as f:
            content = f.read(10000)
        return {
            "status": "success",
            "path": path,
            "content": content,
            "size": len(content),
            "exists": True,
        }
    except Exception as exc:
        return {"status": "error", "path": path, "error": str(exc)}


tool = ToolSpec(
    name="filesystem_read",
    description="Read a file from the local filesystem. Safe, read-only operation.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative file path to read"},
        },
        "required": ["path"],
    },
    execute_fn=execute,
)
