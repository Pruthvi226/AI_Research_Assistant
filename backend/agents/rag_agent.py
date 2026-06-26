from typing import Any, Callable, Dict, List, Optional


class RAGRetrievalAgent:
    name = "RAG Retrieval Agent"

    def __init__(
        self,
        qa_engine,
        gemini_provider: Callable[[], Any],
        ensure_search_index: Callable[[List[str]], int],
        bounded_context: Callable[[List[str]], str],
        db=None,
    ):
        self.qa_engine = qa_engine
        self.gemini_provider = gemini_provider
        self.ensure_search_index = ensure_search_index
        self.bounded_context = bounded_context
        self.db = db

    def run(self, query: str, session_id: str = "", **_: Any) -> Dict[str, Any]:
        if not session_id:
            return {
                "selected_agent": self.name,
                "intent": "source_grounded_qa",
                "response": "Please upload or select a document before asking a source-grounded question.",
                "sources": [],
                "artifacts": {},
            }

        session_ids = [part.strip() for part in session_id.split(",") if part.strip()]
        indexed_count = self.ensure_search_index(session_ids)
        relevant_chunks = self.qa_engine.get_relevant_chunks(query)
        context = self.bounded_context(relevant_chunks)
        history = self.db.get_chat_history(session_id) if self.db else []

        gemini = self.gemini_provider()
        if gemini and gemini.is_available:
            try:
                answer = gemini.answer_question(query, context, history)
                mode = "gemini"
            except Exception:
                answer, relevant_chunks = self.qa_engine.answer(query)
                mode = "local_extractive_after_gemini_error"
        else:
            answer, relevant_chunks = self.qa_engine.answer(query)
            mode = "local_extractive"

        return {
            "selected_agent": self.name,
            "intent": "source_grounded_qa",
            "response": answer,
            "sources": relevant_chunks[:5],
            "artifacts": {
                "indexed_chunks": indexed_count,
                "retrieved_chunks": len(relevant_chunks),
                "mode": mode,
            },
        }
