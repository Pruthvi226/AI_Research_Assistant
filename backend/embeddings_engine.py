"""
Fast retrieval engine for paper chunks.

By default this uses a lightweight lexical index that has no model download
or GPU dependency. Set USE_SEMANTIC_EMBEDDINGS=true to use
sentence-transformers + FAISS when those optional packages are installed.
"""

import json
import math
import re
from collections import Counter
from typing import List, Optional, Tuple

from config import EmbeddingConfig, INDEX_FOLDER

try:
    import numpy as np
except ImportError:
    np = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import faiss
except ImportError:
    faiss = None


class EmbeddingEngine:
    """Creates and searches an in-memory index over document chunks."""

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self.use_semantic = bool(
            self.config.USE_SEMANTIC_EMBEDDINGS and SentenceTransformer and faiss and np is not None
        )
        self._model = None
        self._index = None
        self._chunks: List[str] = []
        self._lexical_vectors: List[Counter] = []
        self._lexical_norms: List[float] = []
        self._chunks_path = INDEX_FOLDER / "chunks.txt"

    @property
    def model(self) -> "SentenceTransformer":
        """Lazy-load the Sentence Transformer model only when semantic mode is enabled."""
        if not self.use_semantic:
            raise RuntimeError("Semantic embeddings are disabled. Set USE_SEMANTIC_EMBEDDINGS=true.")
        if self._model is None:
            self._model = SentenceTransformer(self.config.MODEL_NAME)
        return self._model

    def encode(self, texts: List[str]):
        if not self.use_semantic:
            raise RuntimeError("Semantic embeddings are disabled.")
        if not texts:
            return np.array([]).reshape(0, 384)
        return self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    def create_index(self, chunks: List[str]) -> None:
        """Build a searchable index from text chunks."""
        self._chunks = [chunk for chunk in chunks if chunk and chunk.strip()]
        self._index = None
        self._lexical_vectors = []
        self._lexical_norms = []

        if not self._chunks:
            return

        if self.use_semantic:
            try:
                vectors = self.encode(self._chunks)
                dim = vectors.shape[1]
                index = faiss.IndexFlatIP(dim)
                index.add(vectors.astype(np.float32))
                self._index = index
            except Exception:
                self.use_semantic = False
                self._index = None

        if not self.use_semantic:
            self._lexical_vectors = [self._vectorize(chunk) for chunk in self._chunks]
            self._lexical_norms = [self._norm(vector) for vector in self._lexical_vectors]

        INDEX_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(self._chunks_path, "w", encoding="utf-8") as f:
            for chunk in self._chunks:
                f.write(chunk.replace("\n", " ").strip() + "\n")

    def save_index(self, doc_id: str, metadata: Optional[List[dict]] = None) -> str:
        """Persist the current index/chunks for faster document reloads."""
        if not self._chunks:
            return ""
        INDEX_FOLDER.mkdir(parents=True, exist_ok=True)
        base = INDEX_FOLDER / doc_id
        manifest_path = base.with_suffix(".json")
        payload = {
            "doc_id": doc_id,
            "mode": "semantic" if self.use_semantic and self._index is not None else "lexical",
            "chunks": self._chunks,
            "metadata": metadata or [],
            "model": self.config.MODEL_NAME if self.use_semantic else "lexical",
        }
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        if self.use_semantic and self._index is not None and faiss is not None:
            faiss.write_index(self._index, str(base.with_suffix(".faiss")))
        return str(manifest_path)

    def load_index(self, doc_id: str) -> bool:
        """Load a previously persisted index. Returns False if unavailable."""
        manifest_path = (INDEX_FOLDER / doc_id).with_suffix(".json")
        if not manifest_path.exists():
            return False
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            chunks = [chunk for chunk in payload.get("chunks", []) if chunk and chunk.strip()]
            if not chunks:
                return False
            self._chunks = chunks
            self._index = None
            self._lexical_vectors = []
            self._lexical_norms = []
            mode = payload.get("mode")
            faiss_path = (INDEX_FOLDER / doc_id).with_suffix(".faiss")
            if mode == "semantic" and self.use_semantic and faiss is not None and faiss_path.exists():
                self._index = faiss.read_index(str(faiss_path))
            else:
                self._lexical_vectors = [self._vectorize(chunk) for chunk in self._chunks]
                self._lexical_norms = [self._norm(vector) for vector in self._lexical_vectors]
            return self.has_index
        except Exception:
            return False

    def search(self, query: str, top_k: Optional[int] = None) -> List[Tuple[str, float]]:
        """Return matching chunks as (chunk, distance). Lower distance is better."""
        k = top_k or self.config.TOP_K_RESULTS
        if not query or not self._chunks:
            return []

        if self.use_semantic and self._index is not None:
            query_vector = self.encode([query])
            scores, indices = self._index.search(query_vector.astype(np.float32), min(k, len(self._chunks)))
            results = []
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(self._chunks):
                    results.append((self._chunks[idx], float(1 - scores[0][i])))
            return results

        query_vector = self._vectorize(query)
        query_norm = self._norm(query_vector)
        if query_norm == 0:
            return self._chunks[:k]

        scored = []
        lowered_query = query.lower()
        for idx, chunk_vector in enumerate(self._lexical_vectors):
            norm = self._lexical_norms[idx]
            if norm == 0:
                score = 0.0
            else:
                shared = set(query_vector).intersection(chunk_vector)
                dot = sum(query_vector[token] * chunk_vector[token] for token in shared)
                score = dot / (query_norm * norm)
            if lowered_query and lowered_query in self._chunks[idx].lower():
                score += 0.15
            scored.append((idx, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return [(self._chunks[idx], float(1 - score)) for idx, score in scored[:k]]

    def set_chunks_and_index(self, chunks: List[str], index) -> None:
        self._chunks = chunks
        self._index = index

    @property
    def has_index(self) -> bool:
        return bool(self._chunks) and (self._index is not None or bool(self._lexical_vectors))

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{2,}", text.lower())
            if token not in {"the", "and", "for", "with", "that", "this", "from", "are", "was", "were"}
        ]

    @classmethod
    def _vectorize(cls, text: str) -> Counter:
        return Counter(cls._tokenize(text))

    @staticmethod
    def _norm(vector: Counter) -> float:
        return math.sqrt(sum(value * value for value in vector.values()))
