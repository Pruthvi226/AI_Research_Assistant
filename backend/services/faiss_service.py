from typing import List, Tuple

from embeddings_engine import EmbeddingEngine


class FaissService:
    """FAISS-compatible vector store wrapper.

    The underlying EmbeddingEngine uses FAISS when available and a lexical
    fallback when optional vector dependencies are not installed.
    """

    def __init__(self, engine: EmbeddingEngine):
        self.engine = engine

    def build_index(self, chunks: List[str]) -> int:
        self.engine.create_index(chunks)
        return len(chunks)

    def retrieve(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        return self.engine.search(query, top_k=top_k)

    @property
    def has_index(self) -> bool:
        return self.engine.has_index
