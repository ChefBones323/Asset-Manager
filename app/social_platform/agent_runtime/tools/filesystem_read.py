import os
from typing import Dict, Any

from app.social_platform.agent_runtime.tool_registry import ToolSpec


def execute(path: str, **kwargs) -> Dict[str, Any]:
    safe_path = os.path.normpath(path)
    if safe_path.startswith("..") or safe_path.startswith("/"):
        return {"status": "error", "error": "Path traversal not allowed"}

    if not os.path.exists(safe_path):
        return {
            "status": "simulated",
            "path": safe_path,
            "content": f"[Simulated read of '{safe_path}' — file not found in sandbox]",
            "exists": False,
        }

    try:
        with open(safe_path, "r") as f:
            content = f.read(10000)
        return {
            "status": "success",
            "path": safe_path,
            "content": content,
            "size": len(content),
            "exists": True,
        }
    except Exception as exc:
        return {"status": "error", "path": safe_path, "error": str(exc)}


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
