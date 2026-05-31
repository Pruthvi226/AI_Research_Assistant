import numpy as np
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
from app.core.config import settings

class RAGService:
    def __init__(self):
        # Initialize models
        self.vector_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.bm25 = None
        self.documents = []
        self.embeddings = None

    def fit_bm25(self, texts: List[str]):
        tokenized_corpus = [doc.split(" ") for doc in texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.documents = texts

    def hybrid_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        if not self.bm25:
            return []

        # 1. BM25 Search
        tokenized_query = query.split(" ")
        bm25_scores = self.bm25.get_scores(tokenized_query)
        
        # 2. Vector Search (placeholder for actual vector DB call)
        # In production, this would be a query to ChromaDB/FAISS
        query_embedding = self.vector_model.encode(query)
        # Dummy vector scores for illustration
        vector_scores = np.random.rand(len(self.documents)) 

        # 3. Reciprocal Rank Fusion (RRF) or simple weighted average
        # Here we'll use simple normalization and weighting
        bm25_scores = (bm25_scores - np.min(bm25_scores)) / (np.max(bm25_scores) - np.min(bm25_scores) + 1e-6)
        vector_scores = (vector_scores - np.min(vector_scores)) / (np.max(vector_scores) - np.min(vector_scores) + 1e-6)
        
        hybrid_scores = 0.4 * bm25_scores + 0.6 * vector_scores
        
        top_indices = np.argsort(hybrid_scores)[-top_k * 2:][::-1]
        candidates = [self.documents[i] for i in top_indices]
        
        # 4. Re-ranking with Cross-Encoder
        if candidates:
            pairs = [[query, doc] for doc in candidates]
            rerank_scores = self.cross_encoder.predict(pairs)
            reranked_indices = np.argsort(rerank_scores)[-top_k:][::-1]
            return [candidates[i] for i in reranked_indices]
        
        return []

rag_service = RAGService()
