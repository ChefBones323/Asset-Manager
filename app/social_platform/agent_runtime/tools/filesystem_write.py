from typing import Dict, Any

from app.social_platform.agent_runtime.tool_registry import ToolSpec


def execute(path: str, content: str = "", **kwargs) -> Dict[str, Any]:
    return {
        "status": "requires_proposal",
        "message": "filesystem_write is a destructive operation. "
                   "A proposal has been submitted through the execution engine. "
                   "The write will execute only after human approval.",
        "path": path,
        "content_length": len(content),
    }


tool = ToolSpec(
    name="filesystem_write",
    description="Write content to a file. Requires destructive approval through the governance pipeline.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to write to"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    },
    execute_fn=execute,
)
