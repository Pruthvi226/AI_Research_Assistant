from typing import List, Tuple

from embeddings_engine import EmbeddingEngine


class EmbeddingService:
    def __init__(self, engine: EmbeddingEngine):
        self.engine = engine

    def index_chunks(self, chunks: List[str]) -> None:
        self.engine.create_index(chunks)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        return self.engine.search(query, top_k=top_k)
