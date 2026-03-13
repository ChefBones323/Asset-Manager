import os
import yaml
from typing import Dict, Any

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")


def load_yaml(filename: str) -> Dict[str, Any]:
    path = os.path.join(CONFIG_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def load_system_prompt() -> str:
    data = load_yaml("system_prompt.yaml")
    return data.get("assistant_role", "You are a deterministic execution assistant.")


def load_developer_prompt() -> Dict[str, Any]:
    return load_yaml("developer_prompt.yaml")


def load_agent_config() -> Dict[str, Any]:
    defaults = {
        "max_iterations": 20,
        "memory_enabled": True,
        "scheduler_enabled": True,
    }
    loaded = load_yaml("agent_config.yaml")
    defaults.update(loaded)
    return defaults
