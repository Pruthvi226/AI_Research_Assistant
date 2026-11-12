"""
Fast retrieval engine for paper chunks.

By default this uses a lightweight BM25 index with small research-domain
synonym expansion. It requires no model download, GPU, or heavyweight runtime.
Dense sentence embeddings remain an explicit opt-in for larger deployments.
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

SentenceTransformer = None

try:
    import faiss
except ImportError:
    faiss = None


class EmbeddingEngine:
    """Creates and searches an in-memory index over document chunks."""

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        global SentenceTransformer
        self.config = config or EmbeddingConfig()
        if self.config.USE_SEMANTIC_EMBEDDINGS and SentenceTransformer is None:
            try:
                from sentence_transformers import SentenceTransformer as encoder
                SentenceTransformer = encoder
            except ImportError:
                pass
        self.use_semantic = bool(
            self.config.USE_SEMANTIC_EMBEDDINGS and SentenceTransformer and faiss and np is not None
        )
        self._model = None
        self._index = None
        self._chunks: List[str] = []
        self._lexical_vectors: List[Counter] = []
        self._lexical_norms: List[float] = []
        self._doc_lengths: List[int] = []
        self._document_frequency: Counter = Counter()
        self._chunks_path = INDEX_FOLDER / "chunks.txt"

    @property
    def mode(self) -> str:
        if self.use_semantic and self._index is not None:
            return "semantic_embeddings"
        return "hybrid_bm25"

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
        self._doc_lengths = []
        self._document_frequency = Counter()

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
            self._doc_lengths = [sum(vector.values()) for vector in self._lexical_vectors]
            for vector in self._lexical_vectors:
                self._document_frequency.update(vector.keys())

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
            self._doc_lengths = []
            self._document_frequency = Counter()
            mode = payload.get("mode")
            faiss_path = (INDEX_FOLDER / doc_id).with_suffix(".faiss")
            if mode == "semantic" and self.use_semantic and faiss is not None and faiss_path.exists():
                self._index = faiss.read_index(str(faiss_path))
            else:
                self._lexical_vectors = [self._vectorize(chunk) for chunk in self._chunks]
                self._lexical_norms = [self._norm(vector) for vector in self._lexical_vectors]
                self._doc_lengths = [sum(vector.values()) for vector in self._lexical_vectors]
                for vector in self._lexical_vectors:
                    self._document_frequency.update(vector.keys())
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

        original_terms = set(self._tokenize(query))
        query_terms = self._expand_query(query)
        if not query_terms:
            return []

        count = len(self._chunks)
        average_length = sum(self._doc_lengths) / max(count, 1)
        scored = []
        normalized_query = " ".join(self._tokenize(query))
        for idx, vector in enumerate(self._lexical_vectors):
            doc_length = self._doc_lengths[idx]
            score = 0.0
            for token, query_weight in query_terms.items():
                frequency = vector.get(token, 0)
                if not frequency:
                    continue
                document_frequency = self._document_frequency.get(token, 0)
                inverse_frequency = math.log(
                    1 + (count - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                denominator = frequency + 1.5 * (
                    1 - 0.75 + 0.75 * doc_length / max(average_length, 1)
                )
                score += query_weight * inverse_frequency * frequency * 2.5 / denominator
            matched_original = original_terms.intersection(vector)
            score += 1.8 * len(matched_original) / max(len(original_terms), 1)
            matched_expansions = set(query_terms).difference(original_terms).intersection(vector)
            score += 0.8 * min(
                1.0, len(matched_expansions) / max(len(original_terms), 1)
            )
            lowered = self._chunks[idx].lower()
            if normalized_query and normalized_query in " ".join(self._tokenize(lowered)):
                score += 1.0
            scored.append((idx, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return [
            (self._chunks[idx], float(1 - score / (score + 1.5)))
            for idx, score in scored[:k]
        ]

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
    def _expand_query(cls, text: str) -> Counter:
        weights = Counter()
        for token in cls._tokenize(text):
            weights[token] = 1.0
            for synonym in cls.QUERY_SYNONYMS.get(token, ()):
                weights[synonym] = max(weights[synonym], 0.55)
        return weights

    @classmethod
    def expanded_query_terms(cls, text: str) -> set:
        return set(cls._expand_query(text))

    QUERY_SYNONYMS = {
        "approach": ("method", "technique"),
        "method": ("approach", "technique", "procedure"),
        "methodology": ("method", "approach"),
        "technique": ("method", "approach"),
        "evaluate": ("assess", "measure", "benchmark"),
        "evaluation": ("assess", "measure", "benchmark"),
        "assess": ("evaluate", "measure"),
        "measure": ("evaluate", "metric"),
        "dataset": ("corpus", "benchmark", "data"),
        "corpus": ("dataset", "data"),
        "benchmark": ("dataset", "evaluation", "metric"),
        "result": ("finding", "outcome"),
        "results": ("finding", "outcome", "performance"),
        "finding": ("result", "outcome"),
        "limitation": ("weakness", "constraint", "caveat"),
        "limitations": ("weakness", "constraint", "caveat"),
        "weakness": ("limitation", "constraint"),
        "improve": ("enhance", "increase"),
        "improves": ("enhance", "increase"),
        "performance": ("accuracy", "metric", "score"),
        "accuracy": ("performance", "precision", "score"),
        "precision": ("accuracy", "metric"),
        "retrieval": ("search", "ranking", "matching"),
        "search": ("retrieval", "matching", "ranking"),
        "explain": ("describe", "interpret"),
        "describe": ("explain", "interpret"),
    }

    @classmethod
    def _vectorize(cls, text: str) -> Counter:
        return Counter(cls._tokenize(text))

    @staticmethod
    def _norm(vector: Counter) -> float:
        return math.sqrt(sum(value * value for value in vector.values()))
