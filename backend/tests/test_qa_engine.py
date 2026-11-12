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

        self.assertEqual(1, len(used_chunks))
        self.assertIn("Dense retrieval improves answer quality", answer)

    def test_get_relevant_chunks_respects_top_k(self):
        chunks = [
            ("method first evidence", 0.1),
            ("method second evidence", 0.2),
            ("method third evidence", 0.3),
        ]
        engine = QAEngine(FakeEmbeddingEngine(chunks))

        self.assertEqual(
            ["method first evidence", "method second evidence"],
            engine.get_relevant_chunks("method", top_k=2),
        )

    def test_unrelated_evidence_is_filtered_and_question_abstains(self):
        engine = QAEngine(FakeEmbeddingEngine([
            ("The paper evaluates a small image classification dataset.", 0.95),
        ]))

        answer, sources = engine.answer("How do galaxies form?")

        self.assertEqual([], sources)
        self.assertEqual(QAEngine.ABSTENTION, answer)

    def test_extractive_answer_links_evidence_to_document_page(self):
        chunk = (
            "[Source 4 | methods.pdf | page 7 | chunk 4]\n"
            "The algorithm uses gradient descent to optimize the model weights."
        )
        engine = QAEngine(FakeEmbeddingEngine([(chunk, 0.1)]))

        answer, sources = engine.answer("How does the algorithm optimize model weights?")

        self.assertEqual([chunk], sources)
        self.assertIn("[Source 4 | methods.pdf | page 7 | chunk 4]", answer)


if __name__ == "__main__":
    unittest.main()