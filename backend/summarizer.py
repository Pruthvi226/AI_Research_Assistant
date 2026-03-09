"""
Paper summarizer using HuggingFace BART model.
Generates abstract and section-wise summaries.
"""

import re
from typing import Dict, List, Optional

from config import SummarizerConfig

try:
    from transformers import pipeline
except ImportError:
    pipeline = None


class PaperSummarizer:
    """
    Summarizes research paper text using facebook/bart-large-cnn.
    Produces overall abstract summary and optional section summaries.
    """

    def __init__(self, config: Optional[SummarizerConfig] = None):
        """
        Initialize summarizer. Model is loaded on first use.

        Args:
            config: SummarizerConfig instance. Uses default if not provided.
        """
        self.config = config or SummarizerConfig()
        self._pipe = None

    @property
    def summarizer_pipeline(self):
        """Lazy-load the HuggingFace summarization pipeline."""
        if pipeline is None:
            raise ImportError("transformers required. pip install transformers torch")
        if self._pipe is None:
            self._pipe = pipeline(
                "summarization",
                model=self.config.MODEL_NAME,
                tokenizer=self.config.MODEL_NAME,
            )
        return self._pipe

    def _chunk_for_model(self, text: str, max_chars: int = 4000) -> List[str]:
        """Split long text into chunks under max_chars for model input."""
        if len(text) <= max_chars:
            return [text] if text.strip() else []
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            if end < len(text):
                # Break at sentence boundary
                break_at = text.rfind(".", start, end)
                if break_at > start:
                    end = break_at + 1
            chunks.append(text[start:end].strip())
            start = end
        return [c for c in chunks if c]

    def summarize_abstract(self, full_text: str) -> str:
        """
        Generate a short abstract-style summary of the full paper.

        Args:
            full_text: Full paper text (after removing references).

        Returns:
            Summary string.
        """
        if not full_text or not full_text.strip():
            return ""
        chunks = self._chunk_for_model(full_text)
        summaries = []
        for chunk in chunks[:3]:  # Limit to first 3 chunks to avoid token limit
            try:
                out = self.summarizer_pipeline(
                    chunk,
                    max_length=self.config.MAX_LENGTH,
                    min_length=self.config.MIN_LENGTH,
                    do_sample=False,
                )
                if out and isinstance(out, list) and out[0].get("summary_text"):
                    summaries.append(out[0]["summary_text"])
            except Exception:
                continue
        return " ".join(summaries).strip() if summaries else full_text[:500] + "..."

    def _detect_sections(self, text: str) -> List[tuple]:
        """Heuristic: find section headers (numbered or all-caps short lines)."""
        lines = text.split("\n")
        sections = []  # (title, start_index in full text)
        current_pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                current_pos += len(line) + 1
                continue
            # Common patterns: "1. Introduction", "2. Related Work", "ABSTRACT", "1 Introduction"
            if re.match(r"^(\d+[\.\)]\s*)?[A-Z][a-zA-Z\s]{3,60}$", stripped):
                if len(stripped) < 80 and stripped.upper() not in ("THE", "AND", "FOR"):
                    sections.append((stripped, current_pos))
            current_pos += len(line) + 1
        return sections

    def summarize_sections(self, full_text: str) -> Dict[str, str]:
        """
        Generate a short summary per detected section.

        Args:
            full_text: Full paper text.

        Returns:
            Dict mapping section title to summary.
        """
        sections = self._detect_sections(full_text)
        result = {}
        for i, (title, start) in enumerate(sections):
            end = sections[i + 1][1] if i + 1 < len(sections) else len(full_text)
            section_text = full_text[start:end].strip()
            if len(section_text.split()) < 30:
                continue
            try:
                out = self.summarizer_pipeline(
                    section_text[:4000],
                    max_length=self.config.SECTION_SUMMARY_MAX_LENGTH,
                    min_length=20,
                    do_sample=False,
                )
                if out and isinstance(out, list) and out[0].get("summary_text"):
                    result[title] = out[0]["summary_text"]
            except Exception:
                result[title] = section_text[:200] + "..."
        return result

    def summarize(self, full_text: str) -> Dict[str, str]:
        """
        Produce both abstract and section summaries.

        Args:
            full_text: Full paper text.

        Returns:
            Dict with keys "abstract" and "sections" (dict of section -> summary).
        """
        abstract = self.summarize_abstract(full_text)
        sections = self.summarize_sections(full_text)
        return {"abstract": abstract, "sections": sections}
