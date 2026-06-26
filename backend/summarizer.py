"""
Paper summarization.

The default path is extractive and fast so Docker can process uploads without
downloading transformer weights. Set USE_TRANSFORMER_FALLBACK=true to enable
the optional BART pipeline when transformers/torch are installed.
"""

import re
from typing import Dict, List, Optional

from config import SummarizerConfig

try:
    from transformers import pipeline
except ImportError:
    pipeline = None


class PaperSummarizer:
    """Produces overall and section-level summaries for research papers."""

    KEY_TERMS = {
        "method",
        "model",
        "approach",
        "propose",
        "result",
        "dataset",
        "experiment",
        "accuracy",
        "performance",
        "contribution",
        "limitation",
        "future",
    }

    def __init__(self, config: Optional[SummarizerConfig] = None):
        self.config = config or SummarizerConfig()
        self._pipe = None

    @property
    def summarizer_pipeline(self):
        if not self.config.USE_TRANSFORMER_FALLBACK:
            raise RuntimeError("Transformer fallback is disabled.")
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
        if len(text) <= max_chars:
            return [text] if text.strip() else []
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            if end < len(text):
                break_at = text.rfind(".", start, end)
                if break_at > start:
                    end = break_at + 1
            chunks.append(text[start:end].strip())
            start = end
        return [chunk for chunk in chunks if chunk]

    def summarize_abstract(self, full_text: str) -> str:
        if not full_text or not full_text.strip():
            return ""
        if self.config.USE_TRANSFORMER_FALLBACK:
            transformer_summary = self._try_transformer_abstract(full_text)
            if transformer_summary:
                return transformer_summary
        return self._extractive_summary(full_text, max_sentences=5, max_chars=1100)

    def summarize_sections(self, full_text: str) -> Dict[str, str]:
        sections = self._detect_sections(full_text)
        result = {}
        for i, (title, start) in enumerate(sections[:12]):
            end = sections[i + 1][1] if i + 1 < len(sections) else len(full_text)
            section_text = full_text[start:end].strip()
            if len(section_text.split()) < 30:
                continue
            if self.config.USE_TRANSFORMER_FALLBACK:
                transformer_summary = self._try_transformer_section(section_text)
                if transformer_summary:
                    result[title] = transformer_summary
                    continue
            result[title] = self._extractive_summary(section_text, max_sentences=2, max_chars=450)
        return result

    def summarize(self, full_text: str) -> Dict[str, object]:
        return {
            "abstract": self.summarize_abstract(full_text),
            "sections": self.summarize_sections(full_text),
        }

    def _try_transformer_abstract(self, full_text: str) -> str:
        summaries = []
        for chunk in self._chunk_for_model(full_text)[:3]:
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
                return ""
        return " ".join(summaries).strip()

    def _try_transformer_section(self, section_text: str) -> str:
        try:
            out = self.summarizer_pipeline(
                section_text[:4000],
                max_length=self.config.SECTION_SUMMARY_MAX_LENGTH,
                min_length=20,
                do_sample=False,
            )
            if out and isinstance(out, list) and out[0].get("summary_text"):
                return out[0]["summary_text"]
        except Exception:
            return ""
        return ""

    def _extractive_summary(self, text: str, max_sentences: int, max_chars: int) -> str:
        sentences = self._split_sentences(text)
        if not sentences:
            return text[:max_chars].strip()

        scored = []
        for idx, sentence in enumerate(sentences[:80]):
            words = re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{2,}", sentence.lower())
            if len(words) < 8:
                continue
            keyword_hits = sum(1 for word in words if word in self.KEY_TERMS)
            position_bonus = max(0, 1.0 - (idx / max(1, min(len(sentences), 80))))
            score = keyword_hits * 2 + min(len(words), 35) / 35 + position_bonus
            scored.append((idx, score, sentence))

        if not scored:
            chosen = sentences[:max_sentences]
        else:
            chosen = [
                item[2]
                for item in sorted(
                    sorted(scored, key=lambda item: item[1], reverse=True)[:max_sentences],
                    key=lambda item: item[0],
                )
            ]
        summary = " ".join(chosen).strip()
        return summary[:max_chars].rsplit(" ", 1)[0].strip() + ("..." if len(summary) > max_chars else "")

    def _detect_sections(self, text: str) -> List[tuple]:
        lines = text.split("\n")
        sections = []
        current_pos = 0
        for line in lines:
            stripped = line.strip()
            if stripped:
                if re.match(r"^(\d+[\.\)]\s*)?[A-Z][a-zA-Z&\-\s]{3,70}$", stripped):
                    if len(stripped) < 80 and stripped.upper() not in {"THE", "AND", "FOR"}:
                        sections.append((stripped, current_pos))
            current_pos += len(line) + 1
        if not sections:
            sections = [("Overview", 0)]
        return sections

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text.replace("\r", " ").replace("\n", " "))
            if sentence.strip()
        ]
