"""
QA Engine: answers user questions using semantic search over paper chunks and summarization.
User question -> embedding -> FAISS search -> top chunks -> generate answer.
"""

from typing import List, Optional, TYPE_CHECKING

from config import EmbeddingConfig, InsightsConfig

if TYPE_CHECKING:
    from embeddings_engine import EmbeddingEngine

try:
    from transformers import pipeline
except ImportError:
    pipeline = None


class QAEngine:
    """
    Generates answers to user questions by retrieving relevant chunks via FAISS
    and summarizing them into a coherent answer.
    """

    def __init__(
        self,
        embedding_engine: "EmbeddingEngine",
        embed_config: Optional[EmbeddingConfig] = None,
        insights_config: Optional[InsightsConfig] = None,
    ):
        """
        Initialize QA engine with an embedding engine (which holds FAISS index and chunks).

        Args:
            embedding_engine: EmbeddingEngine instance with create_index already called.
            embed_config: Optional config for top_k.
            insights_config: Optional config (unused but for consistency).
        """
        self.embedding_engine = embedding_engine
        self.embed_config = embed_config or EmbeddingConfig()
        self._summarizer = None

    @property
    def summarizer(self):
        """Lazy-load summarization pipeline for generating answers from context."""
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
        """
        Retrieve top-k most relevant chunks for the question.

        Args:
            question: User question.
            top_k: Number of chunks. Default from config.

        Returns:
            List of chunk texts (no distances).
        """
        results = self.embedding_engine.search(question, top_k=top_k or self.embed_config.TOP_K_RESULTS)
        return [chunk for chunk, _ in results]

    def answer(self, question: str, top_k: Optional[int] = None) -> tuple:
        """
        Generate an answer from the paper context using semantic search + summarization.

        Args:
            question: User question.
            top_k: Number of chunks to use for context.

        Returns:
            Tuple of (answer_text, list_of_relevant_chunk_texts).
        """
        chunks = self.get_relevant_chunks(question, top_k=top_k)
        if not chunks:
            return (
                "No relevant content found in the paper. Please upload a paper first or rephrase your question.",
                [],
            )
        context = "\n\n".join(chunks)
        # Build prompt: question + context, then summarize as "answer"
        combined = f"Question: {question}\n\nRelevant text from the paper:\n{context}"
        if len(combined) > 4000:
            combined = combined[:4000] + "..."
        try:
            out = self.summarizer(combined, max_length=150, min_length=30, do_sample=False)
            if out and isinstance(out, list) and out[0].get("summary_text"):
                answer = out[0]["summary_text"].strip()
                return answer, chunks
        except Exception:
            pass
        # Fallback: return first chunk as answer
        return chunks[0][:500] + ("..." if len(chunks[0]) > 500 else ""), chunks
