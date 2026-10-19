import json
import threading
from typing import Any, Callable, Dict, Optional


class LLMService:
    """Thin wrapper around the active Gemini engine with safe fallbacks."""

    def __init__(self, engine_provider: Callable[[], Any]):
        self.engine_provider = engine_provider
        self._state = threading.local()

    @property
    def last_mode(self):
        return getattr(self._state, 'mode', 'local_fallback')

    @property
    def engine(self):
        return self.engine_provider()

    @property
    def is_available(self) -> bool:
        engine = self.engine
        return bool(engine and engine.is_available)

    def generate_text(self, prompt: str, fallback: str = "") -> str:
        self._state.mode = 'local_fallback'
        if not self.is_available:
            return fallback
        try:
            result = self.engine.generate_text(prompt)
            self._state.mode = 'gemini'
            return result
        except Exception:
            return fallback

    def generate_json(self, prompt: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._state.mode = 'local_fallback'
        fallback = fallback or {}
        if not self.is_available:
            return fallback
        try:
            result = self.engine.generate_json(prompt)
            self._state.mode = 'gemini'
            return result
        except Exception:
            return fallback
