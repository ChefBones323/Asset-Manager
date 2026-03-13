from typing import Dict, Any, Callable, Optional


class ToolSpec:
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        execute_fn: Callable[..., Dict[str, Any]],
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.execute_fn = execute_fn

    def execute(self, **kwargs) -> Dict[str, Any]:
        return self.execute_fn(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def list_tools(self) -> list[Dict[str, Any]]:
        return [t.to_dict() for t in self._tools.values()]

    def has(self, name: str) -> bool:
        return name in self._tools


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    from app.social_platform.agent_runtime.tools.filesystem_read import tool as fs_read
    from app.social_platform.agent_runtime.tools.filesystem_write import tool as fs_write
    from app.social_platform.agent_runtime.tools.web_search import tool as web_search
    from app.social_platform.agent_runtime.tools.browser_open import tool as browser_open
    from app.social_platform.agent_runtime.tools.skill_run import tool as skill_run

    for t in [fs_read, fs_write, web_search, browser_open, skill_run]:
        registry.register(t)

    return registry
