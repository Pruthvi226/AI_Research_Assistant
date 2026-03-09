"""
Research insights engine: key contributions, limitations, future directions.
Uses prompt-based generation with HuggingFace summarization/generation.
"""

import re
from typing import Any, Dict, List, Optional

from config import InsightsConfig

try:
    from transformers import pipeline
except ImportError:
    pipeline = None


class ResearchInsightsEngine:
    """
    Extracts key contributions, limitations, and future research ideas from paper text.
    Generates research gap detection and suggested paper titles.
    """

    def __init__(self, config: Optional[InsightsConfig] = None):
        """
        Initialize the insights engine.

        Args:
            config: InsightsConfig instance. Uses default if not provided.
        """
        self.config = config or InsightsConfig()
        self._summarizer = None

    @property
    def summarizer(self):
        """Lazy-load summarization pipeline for prompt-based generation."""
        if pipeline is None:
            raise ImportError("transformers required. pip install transformers torch")
        if self._summarizer is None:
            self._summarizer = pipeline(
                "summarization",
                model=self.config.GENERATION_MODEL,
                tokenizer=self.config.GENERATION_MODEL,
            )
        return self._summarizer

    def _extract_with_prompt(self, text: str, prompt_prefix: str, max_len: int = 150) -> str:
        """Use summarization on (prompt + text) to get focused extraction."""
        # BART is summarization-only; we prepend instruction and summarize
        combined = prompt_prefix + "\n\n" + text[:3000]
        try:
            out = self.summarizer(combined, max_length=max_len, min_length=30, do_sample=False)
            if out and isinstance(out, list) and out[0].get("summary_text"):
                return out[0]["summary_text"].strip()
        except Exception:
            pass
        return ""

    def get_key_contributions(self, full_text: str) -> List[str]:
        """
        Extract key contributions from the paper.

        Args:
            full_text: Full paper text.

        Returns:
            List of contribution strings.
        """
        prompt = "Key contributions and main findings of this research paper:"
        summary = self._extract_with_prompt(full_text, prompt, max_len=300)
        if not summary:
            return []
        # Split by numbered items or sentences
        items = re.split(r"\n\s*\d+[\.\)]\s*|\n\s*[-*]\s*", summary)
        items = [s.strip() for s in items if len(s.strip()) > 15]
        if not items:
            items = [s.strip() for s in re.split(r"(?<=[.!])\s+", summary) if len(s.strip()) > 15]
        return items[: self.config.NUM_CONTRIBUTIONS]

    def get_limitations(self, full_text: str) -> List[str]:
        """
        Extract limitations mentioned in the paper.

        Args:
            full_text: Full paper text.

        Returns:
            List of limitation strings.
        """
        prompt = "Limitations and weaknesses of this study:"
        summary = self._extract_with_prompt(full_text, prompt, max_len=200)
        if not summary:
            return []
        items = re.split(r"\n\s*\d+[\.\)]\s*|\n\s*[-*]\s*", summary)
        items = [s.strip() for s in items if len(s.strip()) > 10]
        if not items:
            items = [s.strip() for s in re.split(r"(?<=[.!])\s+", summary) if len(s.strip()) > 10]
        return items[: self.config.NUM_LIMITATIONS]

    def get_future_research_directions(self, full_text: str) -> List[str]:
        """
        Suggest future research directions based on the paper.

        Args:
            full_text: Full paper text.

        Returns:
            List of future research idea strings.
        """
        prompt = "Future research directions and open questions suggested by this paper:"
        summary = self._extract_with_prompt(full_text, prompt, max_len=250)
        if not summary:
            return []
        items = re.split(r"\n\s*\d+[\.\)]\s*|\n\s*[-*]\s*", summary)
        items = [s.strip() for s in items if len(s.strip()) > 15]
        if not items:
            items = [s.strip() for s in re.split(r"(?<=[.!])\s+", summary) if len(s.strip()) > 15]
        return items[: self.config.NUM_FUTURE_IDEAS]

    def get_research_gaps(self, full_text: str) -> List[str]:
        """
        Research gap detection: areas the paper does not address or suggests for future work.

        Args:
            full_text: Full paper text.

        Returns:
            List of research gap descriptions.
        """
        prompt = "Research gaps and unexplored areas in this paper:"
        summary = self._extract_with_prompt(full_text, prompt, max_len=200)
        if not summary:
            return []
        items = [s.strip() for s in re.split(r"(?<=[.!])\s+", summary) if len(s.strip()) > 20]
        return items[:5]

    def get_suggested_paper_titles(self, full_text: str) -> List[str]:
        """
        Suggest new paper titles based on the research and future directions.

        Args:
            full_text: Full paper text.

        Returns:
            List of suggested title strings.
        """
        prompt = "Suggest concise academic paper titles for follow-up research:"
        summary = self._extract_with_prompt(full_text, prompt, max_len=150)
        if not summary:
            return []
        # Split by newlines or numbers
        items = re.split(r"\n\s*\d+[\.\)]\s*|\n", summary)
        items = [s.strip().strip('"\'') for s in items if 10 < len(s.strip()) < 120]
        return items[: self.config.NUM_PAPER_TITLES]

    def get_important_sentences(self, full_text: str, top_n: Optional[int] = None) -> List[str]:
        """
        Highlight important sentences (e.g., for abstract/conclusion). Simple heuristic: longer
        declarative sentences from first and last parts of the paper.

        Args:
            full_text: Full paper text.
            top_n: Max number of sentences. Default from config.

        Returns:
            List of important sentence strings.
        """
        n = top_n or self.config.NUM_HIGHLIGHT_SENTENCES
        sentences = re.split(r"(?<=[.!?])\s+", full_text)
        sentences = [s.strip() for s in sentences if 40 < len(s.strip()) < 300]
        if not sentences:
            return []
        # Take from start and end
        k = max(1, n // 2)
        important = sentences[:k] + sentences[-k:]
        return list(dict.fromkeys(important))[:n]

    def generate_all(
        self, full_text: str
    ) -> Dict[str, Any]:
        """
        Generate all insights: contributions, limitations, future ideas, gaps, titles, highlights.

        Args:
            full_text: Full paper text.

        Returns:
            Dict with keys: key_contributions, limitations, future_research, research_gaps,
            suggested_titles, important_sentences.
        """
        return {
            "key_contributions": self.get_key_contributions(full_text),
            "limitations": self.get_limitations(full_text),
            "future_research": self.get_future_research_directions(full_text),
            "research_gaps": self.get_research_gaps(full_text),
            "suggested_titles": self.get_suggested_paper_titles(full_text),
            "important_sentences": self.get_important_sentences(full_text),
        }
