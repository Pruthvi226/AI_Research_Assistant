import unittest

from agents.citation_agent import CitationAgent


class CitationAgentTest(unittest.TestCase):
    def test_unmatched_and_candidate_references_are_never_marked_verified(self):
        class NoMatch:
            @staticmethod
            def search_paper_by_title(_):
                return None

        result = CitationAgent(NoMatch()).run(
            references={"1": "Unresolved synthetic reference"}
        )

        citation = result["artifacts"]["citations"][0]
        self.assertEqual("unresolved", citation["resolution_status"])
        self.assertEqual("unverified", citation["verification_status"])
        self.assertIn("not verified", result["response"])

    def test_metadata_hit_is_a_candidate_not_an_official_relationship(self):
        class Candidate:
            @staticmethod
            def search_paper_by_title(_):
                return {"title": "Possible title", "abstract": "Candidate metadata"}

        result = CitationAgent(Candidate()).run(
            references={"2": "A synthetic citation"}
        )

        citation = result["artifacts"]["citations"][0]
        self.assertEqual("metadata_candidate", citation["resolution_status"])
        self.assertEqual("unverified", citation["verification_status"])
        self.assertIn("candidate", result["response"])

    def test_graph_keeps_unresolved_edges_and_limits_external_resolution(self):
        class Candidate:
            calls = []

            @classmethod
            def resolve_reference(cls, raw):
                cls.calls.append(raw)
                return {
                    "metadata": None,
                    "resolution_status": "unresolved",
                    "verification_status": "unverified",
                }

            @staticmethod
            def recommend_related_works(_):
                return []

        references = {str(i): f"Reference {i} about a research method and evidence" for i in range(1, 8)}
        result = CitationAgent(Candidate).run(
            document_title="source.pdf", references=references
        )
        artifacts = result["artifacts"]
        self.assertEqual(5, len(Candidate.calls))
        self.assertEqual(7, len(artifacts["graph"]["edges"]))
        self.assertEqual("not_checked", artifacts["citations"][-1]["resolution_status"])
        self.assertEqual("source.pdf", artifacts["graph"]["nodes"][0]["label"])
        self.assertEqual("unresolved_reference", artifacts["graph"]["nodes"][1]["type"])


if __name__ == "__main__":
    unittest.main()
