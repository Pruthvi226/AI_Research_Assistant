import unittest

from qa_engine import QAEngine


class FakeEmbeddingEngine:
    def __init__(self, results):
        self.results = results

    def search(self, question, top_k=None):
        limit = top_k or len(self.results)
        return self.results[:limit]


class QAEngineTest(unittest.TestCase):
    def test_answer_returns_empty_state_message_without_chunks(self):
        engine = QAEngine(FakeEmbeddingEngine([]))

        answer, chunks = engine.answer("What is this paper about?")

        self.assertEqual([], chunks)
        self.assertIn("No relevant content", answer)

    def test_extractive_answer_prefers_relevant_sentence(self):
        chunks = [
            ("Background sentence. Dense retrieval improves answer quality for research assistants.", 0.1),
            ("Unrelated implementation notes.", 0.2),
        ]
        engine = QAEngine(FakeEmbeddingEngine(chunks))

        answer, used_chunks = engine.answer("How does dense retrieval improve quality?")

        self.assertEqual(2, len(used_chunks))
        self.assertIn("Dense retrieval improves answer quality", answer)

    def test_get_relevant_chunks_respects_top_k(self):
        chunks = [("first", 0.1), ("second", 0.2), ("third", 0.3)]
        engine = QAEngine(FakeEmbeddingEngine(chunks))

        self.assertEqual(["first", "second"], engine.get_relevant_chunks("query", top_k=2))


if __name__ == "__main__":
    unittest.main()