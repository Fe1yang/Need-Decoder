from __future__ import annotations

from pathlib import Path

from need_decoder.questions import next_question
from need_decoder.retrieval import CatalogSearch
from need_decoder.state import ConversationState


class Agent:
    """Official TechJam adapter for the Need Decoder pipeline."""

    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        self.catalog = CatalogSearch(catalog_path)
        self.sessions: dict[str, ConversationState] = {}

    def reset(self, session_id: str, user_profile: dict) -> None:
        self.sessions[session_id] = ConversationState(profile=user_profile or {})

    def respond(
        self,
        session_id: str,
        user_message: str,
        turn: int,
        top_k: int,
    ) -> dict:
        if session_id not in self.sessions:
            raise RuntimeError("reset must be called before respond")

        state = self.sessions[session_id]
        state.ingest(user_message)
        recommendations = self.catalog.search(state, limit=min(max(top_k, 1), 10))
        if turn < 10:
            ask_attribute, message = next_question(state)
        else:
            ask_attribute, message = None, "These are my best matches based on what you told me."

        return {
            "message": message,
            "ask_attribute": ask_attribute,
            "recommendations": recommendations,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }

    def inspect_session(self, session_id: str) -> dict:
        """Return explainability data for local demos, never for the scorer."""
        if session_id not in self.sessions:
            raise KeyError(session_id)
        return self.sessions[session_id].debug_snapshot()
