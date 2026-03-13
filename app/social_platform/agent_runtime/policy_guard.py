from enum import Enum
from typing import Dict


class ApprovalLevel(str, Enum):
    AUTO = "auto"
    CONFIRMATION = "confirmation"
    DESTRUCTIVE = "destructive"


TOOL_POLICIES: Dict[str, ApprovalLevel] = {
    "filesystem_read": ApprovalLevel.AUTO,
    "web_search": ApprovalLevel.AUTO,
    "browser_open": ApprovalLevel.CONFIRMATION,
    "email_send": ApprovalLevel.CONFIRMATION,
    "filesystem_write": ApprovalLevel.DESTRUCTIVE,
    "database_write": ApprovalLevel.DESTRUCTIVE,
    "skill_run": ApprovalLevel.CONFIRMATION,
}


class PolicyGuard:
    def __init__(self, policies: Dict[str, ApprovalLevel] | None = None):
        self._policies = policies or TOOL_POLICIES

    def get_approval_level(self, tool_name: str) -> ApprovalLevel:
        return self._policies.get(tool_name, ApprovalLevel.DESTRUCTIVE)

    def is_auto_approved(self, tool_name: str) -> bool:
        return self.get_approval_level(tool_name) == ApprovalLevel.AUTO

    def requires_confirmation(self, tool_name: str) -> bool:
        return self.get_approval_level(tool_name) == ApprovalLevel.CONFIRMATION

    def requires_destructive_approval(self, tool_name: str) -> bool:
        return self.get_approval_level(tool_name) == ApprovalLevel.DESTRUCTIVE

    def check_permission(self, tool_name: str) -> Dict:
        level = self.get_approval_level(tool_name)
        return {
            "tool": tool_name,
            "approval_level": level.value,
            "auto_approved": level == ApprovalLevel.AUTO,
            "requires_human_approval": level in (ApprovalLevel.CONFIRMATION, ApprovalLevel.DESTRUCTIVE),
            "is_destructive": level == ApprovalLevel.DESTRUCTIVE,
        }

    def list_policies(self) -> Dict[str, str]:
        return {tool: level.value for tool, level in self._policies.items()}
