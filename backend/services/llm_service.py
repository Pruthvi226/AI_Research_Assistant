import json
from typing import Any, Callable, Dict, Optional


class LLMService:
    """Thin wrapper around the active Gemini engine with safe fallbacks."""

    def __init__(self, engine_provider: Callable[[], Any]):
        self.engine_provider = engine_provider

    @property
    def engine(self):
        return self.engine_provider()

    @property
    def is_available(self) -> bool:
        engine = self.engine
        return bool(engine and engine.is_available)

    def generate_text(self, prompt: str, fallback: str = "") -> str:
        if not self.is_available:
            return fallback
        try:
            return self.engine.generate_text(prompt)
        except Exception:
            return fallback

    def generate_json(self, prompt: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        fallback = fallback or {}
        if not self.is_available:
            return fallback
        try:
            return self.engine.generate_json(prompt)
        except Exception:
            text = self.generate_text(prompt, fallback="")
            try:
                return json.loads(text)
            except Exception:
                return fallback
