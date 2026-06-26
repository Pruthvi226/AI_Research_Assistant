"""
Fast research insight extraction.

This module favors deterministic, extractive analysis for the local/offline
path. Cloud Gemini still provides the richer structured output when a real key
is configured.
"""

import re
from collections import Counter
from typing import Any, Dict, List, Optional

from config import InsightsConfig

try:
    from transformers import pipeline
except ImportError:
    pipeline = None


class ResearchInsightsEngine:
    """Extracts contributions, limitations, gaps, future work, and highlights."""

    def __init__(self, config: Optional[InsightsConfig] = None):
        self.config = config or InsightsConfig()
        self._summarizer = None

    @property
    def summarizer(self):
        if not self.config.USE_TRANSFORMER_FALLBACK:
            raise RuntimeError("Transformer fallback is disabled.")
        if pipeline is None:
            raise ImportError("transformers required. pip install transformers torch")
        if self._summarizer is None:
            self._summarizer = pipeline(
                "summarization",
                model=self.config.GENERATION_MODEL,
                tokenizer=self.config.GENERATION_MODEL,
            )
        return self._summarizer

    def get_key_contributions(self, full_text: str) -> List[str]:
        if self.config.USE_TRANSFORMER_FALLBACK:
            generated = self._generated_items(full_text, "Key contributions and main findings:", 300)
            if generated:
                return generated[: self.config.NUM_CONTRIBUTIONS]
        items = self._keyword_sentences(
            full_text,
            ["we propose", "this paper", "contribution", "novel", "improve", "outperform", "achieve"],
            self.config.NUM_CONTRIBUTIONS,
        )
        return items or self.get_important_sentences(full_text, top_n=self.config.NUM_CONTRIBUTIONS)

    def get_limitations(self, full_text: str) -> List[str]:
        if self.config.USE_TRANSFORMER_FALLBACK:
            generated = self._generated_items(full_text, "Limitations and weaknesses:", 200)
            if generated:
                return generated[: self.config.NUM_LIMITATIONS]
        return self._keyword_sentences(
            full_text,
            ["limitation", "limited", "constraint", "however", "challenge", "threat", "future work"],
            self.config.NUM_LIMITATIONS,
        )

    def get_future_research_directions(self, full_text: str) -> List[str]:
        if self.config.USE_TRANSFORMER_FALLBACK:
            generated = self._generated_items(full_text, "Future research directions:", 250)
            if generated:
                return generated[: self.config.NUM_FUTURE_IDEAS]
        return self._keyword_sentences(
            full_text,
            ["future", "further", "extend", "next", "open question", "could", "should"],
            self.config.NUM_FUTURE_IDEAS,
        )

    def get_research_gaps(self, full_text: str) -> List[str]:
        if self.config.USE_TRANSFORMER_FALLBACK:
            generated = self._generated_items(full_text, "Research gaps and unexplored areas:", 200)
            if generated:
                return generated[:5]
        return self._keyword_sentences(
            full_text,
            ["gap", "unexplored", "not address", "lack", "missing", "open", "future"],
            5,
        )

    def get_suggested_paper_titles(self, full_text: str) -> List[str]:
        terms = self._top_terms(full_text, limit=4)
        if not terms:
            return []
        primary = " ".join(term.title() for term in terms[:2])
        secondary = " ".join(term.title() for term in terms[2:4]) or "Research Systems"
        return [
            f"Efficient {primary} for {secondary}",
            f"Benchmarking {primary} Under Real-World Constraints",
            f"Toward Robust {primary}: Methods, Limits, and Future Directions",
        ][: self.config.NUM_PAPER_TITLES]

    def get_important_sentences(self, full_text: str, top_n: Optional[int] = None) -> List[str]:
        n = top_n or self.config.NUM_HIGHLIGHT_SENTENCES
        sentences = [s for s in self._sentences(full_text) if 40 < len(s) < 320]
        if not sentences:
            return []
        candidates = sentences[: max(4, n)] + sentences[-max(4, n):]
        return self._unique(candidates)[:n]

    def generate_all(self, full_text: str) -> Dict[str, Any]:
        return {
            "key_contributions": self.get_key_contributions(full_text),
            "limitations": self.get_limitations(full_text),
            "future_research": self.get_future_research_directions(full_text),
            "research_gaps": self.get_research_gaps(full_text),
            "suggested_titles": self.get_suggested_paper_titles(full_text),
            "important_sentences": self.get_important_sentences(full_text),
        }

    def _generated_items(self, text: str, prompt_prefix: str, max_len: int) -> List[str]:
        try:
            out = self.summarizer(
                prompt_prefix + "\n\n" + text[:3000],
                max_length=max_len,
                min_length=30,
                do_sample=False,
            )
            summary = out[0].get("summary_text", "") if out and isinstance(out, list) else ""
        except Exception:
            return []
        parts = re.split(r"\n\s*\d+[\.\)]\s*|\n\s*[-*]\s*|(?<=[.!])\s+", summary)
        return self._unique([part.strip() for part in parts if len(part.strip()) > 15])

    def _keyword_sentences(self, text: str, keywords: List[str], limit: int) -> List[str]:
        keyword_lowers = [keyword.lower() for keyword in keywords]
        scored = []
        for idx, sentence in enumerate(self._sentences(text)):
            lower = sentence.lower()
            score = sum(1 for keyword in keyword_lowers if keyword in lower)
            if score:
                scored.append((idx, score, sentence))
        scored.sort(key=lambda item: (-item[1], item[0]))
        return self._unique([item[2] for item in scored])[:limit]

    @staticmethod
    def _sentences(text: str) -> List[str]:
        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text.replace("\r", " ").replace("\n", " "))
            if sentence.strip()
        ]

    @staticmethod
    def _unique(items: List[str]) -> List[str]:
        seen = set()
        result = []
        for item in items:
            cleaned = re.sub(r"\s+", " ", item).strip()
            key = cleaned.lower()
            if cleaned and key not in seen:
                seen.add(key)
                result.append(cleaned)
        return result

    @staticmethod
    def _top_terms(text: str, limit: int) -> List[str]:
        stop_words = {
            "this",
            "that",
            "with",
            "from",
            "paper",
            "research",
            "method",
            "model",
            "results",
            "using",
            "based",
            "approach",
            "study",
        }
        words = [
            word
            for word in re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{3,}", text.lower())
            if word not in stop_words
        ]
        return [word for word, _ in Counter(words).most_common(limit)]
