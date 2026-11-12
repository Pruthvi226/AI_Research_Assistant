import json
import unittest
from unittest.mock import patch

from scholarly_service import ScholarlyService


class FakeResponse:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.value).encode()


class ScholarlyServiceTest(unittest.TestCase):
    def test_extracts_reference_title_after_author_year(self):
        raw = (
            "Smith, A. and Jones, B. (2022). "
            "A Study of Evidence-Aware Retrieval. Journal of Research, 4(2)."
        )
        self.assertEqual(
            "A Study of Evidence-Aware Retrieval",
            ScholarlyService.extract_reference_title(raw),
        )

    @patch.object(ScholarlyService, "_lookup_crossref_doi")
    def test_doi_resolution_is_exact_but_does_not_claim_verified_relationship(self, lookup):
        lookup.return_value = {
            "title": "Evidence Aware Retrieval for Research",
            "doi": "10.1234/real",
            "url": "https://doi.org/10.1234/real",
        }
        result = ScholarlyService.resolve_reference(
            "Smith (2024). Evidence Aware Retrieval for Research. doi:10.1234/real"
        )
        self.assertEqual("doi_match", result["resolution_status"])
        self.assertEqual("doi", result["matched_by"])
        self.assertEqual("unverified", result["verification_status"])
        lookup.assert_called_once_with("10.1234/real")

    @patch.object(ScholarlyService, "search_paper_by_title")
    def test_title_resolution_requires_close_metadata_match(self, lookup):
        lookup.return_value = {
            "title": "A Study of Evidence-Aware Retrieval",
            "doi": "10.1234/candidate",
        }
        result = ScholarlyService.resolve_reference(
            "Smith, A. (2022). A Study of Evidence-Aware Retrieval. Journal."
        )
        self.assertEqual("title_candidate", result["resolution_status"])
        self.assertGreaterEqual(result["match_score"], 0.72)

        lookup.return_value = {"title": "Unrelated Clinical Study"}
        mismatch = ScholarlyService.resolve_reference(
            "Smith, A. (2022). A Study of Evidence-Aware Retrieval. Journal."
        )
        self.assertEqual("unresolved", mismatch["resolution_status"])
        self.assertIsNone(mismatch["metadata"])
        self.assertEqual("Unrelated Clinical Study", mismatch["candidate_title"])

    @patch("scholarly_service.urllib.request.urlopen")
    def test_recommendations_have_openalex_provenance(self, open_url):
        open_url.return_value = FakeResponse({
            "results": [{
                "id": "https://openalex.org/W123",
                "title": "Related Evidence Study",
                "publication_year": 2024,
                "doi": "https://doi.org/10.1234/related",
                "cited_by_count": 9,
            }]
        })
        result = ScholarlyService.recommend_related_works([{
            "ref_num": "2",
            "scholarly": {"related_works": ["https://openalex.org/W123"]},
        }])
        self.assertEqual(1, len(result))
        self.assertEqual("2", result[0]["related_to_ref"])
        self.assertEqual("unverified_recommendation", result[0]["verification_status"])
        self.assertIn("related works", result[0]["provenance"])


if __name__ == "__main__":
    unittest.main()
