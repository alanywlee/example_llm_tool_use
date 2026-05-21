from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationState:
    """
    Persistent conversation history for a CLI session.

    We intentionally persist only user and final assistant messages.

    Tool-call intermediate messages are used inside one turn but are not
    stored permanently. This keeps the next request compatible with stricter
    chat templates and avoids carrying stale tool-call state forever.
    """
    history: list[dict[str, Any]] = field(default_factory=list)
    max_history_messages: int = 20

    def reset(self) -> None:
        self.history.clear()

    def add_user_message(self, content: str) -> None:
        self.history.append({"role": "user", "content": content})
        self.trim()

    def add_assistant_message(self, content: str) -> None:
        self.history.append({"role": "assistant", "content": content})
        self.trim()

    def get_history(self) -> list[dict[str, Any]]:
        return list(self.history)

    def trim(self) -> None:
        if self.max_history_messages <= 0:
            self.history.clear()
            return

        if len(self.history) > self.max_history_messages:
            self.history = self.history[-self.max_history_messages:]
