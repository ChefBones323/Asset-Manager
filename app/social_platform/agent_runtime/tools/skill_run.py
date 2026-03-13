import os
import yaml
from typing import Dict, Any

from app.social_platform.agent_runtime.tool_registry import ToolSpec

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent_runtime", "skills")


def execute(skill_name: str, **kwargs) -> Dict[str, Any]:
    skill_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "skills", f"{skill_name}.yaml"
    )
    if not os.path.exists(skill_path):
        return {
            "status": "error",
            "error": f"Skill '{skill_name}' not found at {skill_path}",
            "available_skills": _list_available_skills(),
        }

    try:
        with open(skill_path, "r") as f:
            skill_def = yaml.safe_load(f)
    except Exception as exc:
        return {"status": "error", "error": f"Failed to parse skill: {exc}"}

    steps = skill_def.get("steps", [])
    return {
        "status": "simulated",
        "skill": skill_name,
        "definition": skill_def.get("name", skill_name),
        "steps_count": len(steps),
        "steps": steps,
        "note": "Skill execution is simulated. Each step would be routed through the tool_router in production.",
    }


def _list_available_skills():
    skills_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")
    if not os.path.exists(skills_dir):
        return []
    return [f.replace(".yaml", "") for f in os.listdir(skills_dir) if f.endswith(".yaml")]


tool = ToolSpec(
    name="skill_run",
    description="Execute a predefined skill (multi-step tool sequence). Requires confirmation approval.",
    input_schema={
        "type": "object",
        "properties": {
            "skill_name": {"type": "string", "description": "Name of the skill to run (without .yaml extension)"},
        },
        "required": ["skill_name"],
    },
    execute_fn=execute,
)
