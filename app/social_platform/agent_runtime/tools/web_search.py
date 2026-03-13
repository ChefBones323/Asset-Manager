from typing import Dict, Any

from app.social_platform.agent_runtime.tool_registry import ToolSpec


def execute(query: str, **kwargs) -> Dict[str, Any]:
    return {
        "status": "simulated",
        "query": query,
        "results": [
            {
                "title": f"Search result for: {query}",
                "url": f"https://search.example.com/q={query.replace(' ', '+')}",
                "snippet": f"Simulated search result. In production, this would query a real search API for '{query}'.",
            },
        ],
        "total_results": 1,
        "note": "Web search is currently simulated. Wire a real search API for production use.",
    }


tool = ToolSpec(
    name="web_search",
    description="Search the web for information. Auto-approved read-only operation.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query string"},
        },
        "required": ["query"],
    },
    execute_fn=execute,
)
