"""In-memory session manager for client interfaces."""

from __future__ import annotations

from typing import Dict, Optional

from ..llm.llm_operator import LLMOperator
from .chat_session import ChatSession


class SessionManager:
    """Stores ChatSession objects in memory."""

    def __init__(self, *, llm_operator: Optional[LLMOperator] = None) -> None:
        self._sessions: Dict[str, ChatSession] = {}
        self._llm_operator = llm_operator

    def get(self, client_id: str) -> ChatSession:
        session = self._sessions.get(client_id)
        if session is None:
            session = ChatSession(active_storage_id=None, llm_operator=self._llm_operator)
            self._sessions[client_id] = session
        return session
