"""
QA Engine.

Retrieval is handled by EmbeddingEngine. Local answers are extractive and fast;
Gemini is used by the RAG agent for richer answers when a valid key is configured.
"""

import logging
import re
from typing import Any, List, Optional, Sequence, Tuple, TYPE_CHECKING

from config import EmbeddingConfig, InsightsConfig

if TYPE_CHECKING:
    from embeddings_engine import EmbeddingEngine

try:
    from transformers import pipeline
except ImportError:
    pipeline = None


logger = logging.getLogger(__name__)


class QAEngine:
    """Answers user questions from retrieved paper chunks."""

    TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_\-]{2,}")
    SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
    STOP_WORDS = {
        "about",
        "does",
        "from",
        "how",
        "that",
        "this",
        "what",
        "when",
        "where",
        "which",
        "with",
    }
    TRANSFORMER_INPUT_CHARS = 4000
    TRANSFORMER_MAX_LENGTH = 150
    TRANSFORMER_MIN_LENGTH = 30
    EXTRACTIVE_SENTENCE_LIMIT = 4
    ANSWER_CHAR_LIMIT = 1200

    def __init__(
        self,
        embedding_engine: "EmbeddingEngine",
        embed_config: Optional[EmbeddingConfig] = None,
        insights_config: Optional[InsightsConfig] = None,
    ):
        self.embedding_engine = embedding_engine
        self.embed_config = embed_config or EmbeddingConfig()
        self.insights_config = insights_config or InsightsConfig()
        self._summarizer: Any = None

    @property
    def summarizer(self):
        if not self.insights_config.USE_TRANSFORMER_FALLBACK:
            raise RuntimeError("Transformer fallback is disabled.")
        if pipeline is None:
            raise ImportError("transformers required. pip install transformers torch")
        if self._summarizer is None:
            self._summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                tokenizer="facebook/bart-large-cnn",
            )
        return self._summarizer

    def get_relevant_chunks(self, question: str, top_k: Optional[int] = None) -> List[str]:
        """Return retrieved chunks ordered by relevance."""
        limit = top_k or self.embed_config.TOP_K_RESULTS
        results = self.embedding_engine.search(question.strip(), top_k=limit)
        return [chunk for chunk, _ in results]

    def answer(self, question: str, top_k: Optional[int] = None) -> Tuple[str, List[str]]:
        """Return an answer and the chunks used to produce it."""
        chunks = self.get_relevant_chunks(question, top_k=top_k)
        if not chunks:
            return (
                "No relevant content found in the paper. Please upload a paper first or rephrase your question.",
                [],
            )

        if self.insights_config.USE_TRANSFORMER_FALLBACK:
            transformer_answer = self._try_transformer_answer(question, chunks)
            if transformer_answer:
                return transformer_answer, chunks

        return self._extractive_answer(question, chunks), chunks

    def _try_transformer_answer(self, question: str, chunks: Sequence[str]) -> str:
        context = "\n\n".join(chunks)
        combined = f"Question: {question}\n\nRelevant text from the paper:\n{context}"
        try:
            output = self.summarizer(
                combined[: self.TRANSFORMER_INPUT_CHARS],
                max_length=self.TRANSFORMER_MAX_LENGTH,
                min_length=self.TRANSFORMER_MIN_LENGTH,
                do_sample=False,
            )
            if output and isinstance(output, list):
                summary_text = output[0].get("summary_text", "")
                return summary_text.strip()
        except Exception as exc:
            logger.debug("Transformer QA fallback failed; using extractive answer.", exc_info=True)
        return ""

    def _extractive_answer(self, question: str, chunks: Sequence[str]) -> str:
        query_terms = set(self._tokenize(question))
        scored_sentences = self._rank_sentences(query_terms, chunks)
        if scored_sentences:
            top_sentences = [sentence for _, sentence in scored_sentences[: self.EXTRACTIVE_SENTENCE_LIMIT]]
            return self._cap_answer(" ".join(self._unique(top_sentences)))

        first_chunk = chunks[0].strip()
        return self._cap_answer(first_chunk)

    def _rank_sentences(self, query_terms: set, chunks: Sequence[str]) -> List[Tuple[float, str]]:
        scored: List[Tuple[float, str]] = []
        if not query_terms:
            return scored

        for chunk_idx, chunk in enumerate(chunks):
            chunk_boost = max(0, 3 - chunk_idx) * 0.25
            for sentence_idx, sentence in enumerate(self._sentences(chunk)):
                terms = set(self._tokenize(sentence))
                if not terms:
                    continue
                overlap = len(query_terms.intersection(terms))
                score = overlap + chunk_boost - sentence_idx * 0.01
                if score > 0:
                    scored.append((score, sentence))

        scored.sort(key=lambda item: item[0], reverse=True)
        return scored

    @classmethod
    def _tokenize(cls, text: str) -> List[str]:
        return [
            token
            for token in cls.TOKEN_RE.findall(text.lower())
            if token not in cls.STOP_WORDS
        ]

    @classmethod
    def _sentences(cls, text: str) -> List[str]:
        normalized = text.replace("\r", " ").replace("\n", " ")
        return [sentence.strip() for sentence in cls.SENTENCE_RE.split(normalized) if sentence.strip()]

    @staticmethod
    def _unique(items: Sequence[str]) -> List[str]:
        seen = set()
        result = []
        for item in items:
            key = item.lower()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    @classmethod
    def _cap_answer(cls, answer: str, limit: Optional[int] = None) -> str:
        max_chars = limit or cls.ANSWER_CHAR_LIMIT
        answer = re.sub(r"\s+", " ", answer).strip()
        if len(answer) <= max_chars:
            return answer
        return answer[:max_chars].rsplit(" ", 1)[0].strip() + "..."