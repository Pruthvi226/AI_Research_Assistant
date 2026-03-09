"""
Chat memory: stores conversation history (questions and answers) per session.
In-memory store with optional persistence; keyed by session_id.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, List, Optional


@dataclass
class Turn:
    """Single Q&A turn."""
    question: str
    answer: str
    relevant_sections: List[str] = field(default_factory=list)


class ChatMemory:
    """
    In-memory conversation history per session.
    Each session has a list of Turn (question, answer, relevant_sections).
    """

    def __init__(self):
        """Initialize empty per-session storage."""
        self._sessions: DefaultDict[str, List[Turn]] = defaultdict(list)

    def add(self, session_id: str, question: str, answer: str, relevant_sections: Optional[List[str]] = None) -> None:
        """
        Add a Q&A turn to the session.

        Args:
            session_id: Session identifier (e.g., upload filename or user id).
            question: User question.
            answer: Generated answer.
            relevant_sections: Optional list of chunk texts used for the answer.
        """
        self._sessions[session_id].append(
            Turn(
                question=question,
                answer=answer,
                relevant_sections=relevant_sections or [],
            )
        )

    def get_history(self, session_id: str) -> List[Turn]:
        """
        Get full conversation history for a session.

        Args:
            session_id: Session identifier.

        Returns:
            List of Turn objects in order.
        """
        return list(self._sessions[session_id])

    def get_history_as_dicts(self, session_id: str) -> List[dict]:
        """
        Get history as list of dicts for JSON serialization.

        Args:
            session_id: Session identifier.

        Returns:
            List of {"question", "answer", "relevant_sections"} dicts.
        """
        return [
            {
                "question": t.question,
                "answer": t.answer,
                "relevant_sections": t.relevant_sections,
            }
            for t in self._sessions[session_id]
        ]

    def clear(self, session_id: str) -> None:
        """
        Clear conversation history for a session.

        Args:
            session_id: Session identifier.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]

    def has_session(self, session_id: str) -> bool:
        """Return True if session has at least one turn."""
        return len(self._sessions[session_id]) > 0
