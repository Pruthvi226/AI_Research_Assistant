import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import embeddings_engine
from embeddings_engine import EmbeddingEngine
from qa_engine import QAEngine


class LightweightRetrievalTest(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[2] / ".codex-test" / "backend-tests"
        test_root.mkdir(parents=True, exist_ok=True)
        self.workspace = tempfile.TemporaryDirectory(dir=test_root)
        self.folder = Path(self.workspace.name)
        self.folder_patch = patch.object(embeddings_engine, "INDEX_FOLDER", self.folder)
        self.folder_patch.start()

        class Config:
            USE_SEMANTIC_EMBEDDINGS = False
            MODEL_NAME = "unused"
            TOP_K_RESULTS = 5

        self.engine = EmbeddingEngine(Config())

    def tearDown(self):
        self.folder_patch.stop()
        self.workspace.cleanup()

    def test_bm25_synonym_expansion_retrieves_conceptually_related_research_text(self):
        related = (
            "[Source 1 | study.pdf | page 2 | chunk 1]\n"
            "The evaluation measures precision on a benchmark dataset to assess retrieval quality."
        )
        unrelated = (
            "[Source 2 | study.pdf | page 4 | chunk 2]\n"
            "A survey describes coastal rainfall and river flood warning systems."
        )
        self.engine.create_index([unrelated, related])

        results = self.engine.search("How do they assess the benchmark?", top_k=2)

        self.assertEqual("hybrid_bm25", self.engine.mode)
        self.assertEqual(related, results[0][0])
        self.assertLess(results[0][1], results[1][1])

    def test_empty_or_unrelated_search_does_not_fall_back_to_first_chunk(self):
        self.engine.create_index([
            "The paper studies image classification and neural networks.",
            "The results describe a benchmark dataset.",
        ])
        self.assertEqual([], self.engine.search("the and was"))
        qa = QAEngine(self.engine)
        answer, sources = qa.answer("How do galaxies form?")
        self.assertEqual([], sources)
        self.assertEqual(QAEngine.ABSTENTION, answer)


if __name__ == "__main__":
    unittest.main()
