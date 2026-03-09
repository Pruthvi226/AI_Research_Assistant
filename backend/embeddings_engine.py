"""
Embeddings engine using Sentence Transformers and FAISS for vector search.
Creates and queries semantic index over paper chunks.
"""

from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from config import EmbeddingConfig, INDEX_FOLDER

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import faiss
except ImportError:
    faiss = None


class EmbeddingEngine:
    """
    Creates embeddings from text chunks and provides FAISS-based similarity search.
    Uses all-MiniLM-L6-v2 for encoding.
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        Initialize the embedding model. Loads sentence-transformers model on first use.

        Args:
            config: EmbeddingConfig instance. Uses default if not provided.
        """
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers required. pip install sentence-transformers")
        if faiss is None:
            raise ImportError("faiss-cpu required. pip install faiss-cpu")
        self.config = config or EmbeddingConfig()
        self._model = None
        self._index = None
        self._chunks: List[str] = []
        self._index_path = INDEX_FOLDER / "faiss.index"
        self._chunks_path = INDEX_FOLDER / "chunks.txt"

    @property
    def model(self) -> "SentenceTransformer":
        """Lazy-load the Sentence Transformer model."""
        if self._model is None:
            self._model = SentenceTransformer(self.config.MODEL_NAME)
        return self._model

    def encode(self, texts: List[str]) -> np.ndarray:
        """
        Encode a list of texts into embedding vectors.

        Args:
            texts: List of text strings.

        Returns:
            numpy array of shape (len(texts), embedding_dim).
        """
        if not texts:
            return np.array([]).reshape(0, 384)
        return self.model.encode(texts, convert_to_numpy=True)

    def create_index(self, chunks: List[str]) -> None:
        """
        Build FAISS index from text chunks. Stores chunks for later retrieval.

        Args:
            chunks: List of text chunks (e.g., from TextChunker).
        """
        if not chunks:
            self._index = None
            self._chunks = []
            return
        self._chunks = chunks
        vectors = self.encode(chunks)
        dim = vectors.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(vectors.astype(np.float32))
        self._index = index
        # Persist chunks for server restarts (optional: persist index too)
        INDEX_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(self._chunks_path, "w", encoding="utf-8") as f:
            for c in chunks:
                f.write(c.replace("\n", " ").strip() + "\n")

    def search(self, query: str, top_k: Optional[int] = None) -> List[Tuple[str, float]]:
        """
        Search for most similar chunks to the query.

        Args:
            query: Search query string.
            top_k: Number of results to return. Default from config.

        Returns:
            List of (chunk_text, distance) tuples, sorted by similarity (lower distance = more similar).
        """
        k = top_k or self.config.TOP_K_RESULTS
        if self._index is None or not self._chunks:
            return []
        query_vector = self.encode([query])
        distances, indices = self._index.search(query_vector.astype(np.float32), min(k, len(self._chunks)))
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self._chunks):
                results.append((self._chunks[idx], float(distances[0][i])))
        return results

    def set_chunks_and_index(self, chunks: List[str], index: "faiss.Index") -> None:
        """
        Set chunks and FAISS index (e.g., after loading from disk or from upload pipeline).

        Args:
            chunks: List of text chunks.
            index: FAISS index with same dimension as model.
        """
        self._chunks = chunks
        self._index = index

    @property
    def has_index(self) -> bool:
        """Return True if index is built and has chunks."""
        return self._index is not None and len(self._chunks) > 0
