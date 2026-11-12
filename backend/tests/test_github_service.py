import json
import urllib.error
import unittest
from unittest.mock import patch

from services.github_service import GitHubService


class GitHubServiceTest(unittest.TestCase):
    def test_search_candidates_are_never_claimed_as_official(self):
        repository = GitHubService._normalize_repo(
            {
                "id": 17,
                "name": "graph-learning",
                "full_name": "researcher/graph-learning",
                "html_url": "https://github.com/researcher/graph-learning",
                "description": "Graph learning experiments",
                "stargazers_count": 200,
            },
            "graph learning",
        )

        self.assertEqual("related_unverified", repository["relationship_status"])
        self.assertIn("graph, learning", repository["match_evidence"])
        self.assertNotEqual("official", repository["relationship_status"])
        self.assertEqual("github_repository_search", repository["provenance"])

    def test_user_supplied_repository_link_is_labeled_unverified(self):
        service = GitHubService()
        with patch.object(
            service,
            "_get_json",
            return_value={
                "id": 17,
                "name": "paper-code",
                "full_name": "authors/paper-code",
                "html_url": "https://github.com/authors/paper-code",
                "description": "Model implementation",
                "stargazers_count": 10,
            },
        ):
            result = service.summarize_repository_link(
                "https://github.com/authors/paper-code"
            )

        self.assertEqual("user_provided_unverified", result["relationship_status"])
        self.assertIn("not verified", result["match_evidence"])
        self.assertEqual("user_provided", result["provenance"])

    def test_paper_link_and_readme_evidence_are_recorded_without_official_claim(self):
        service = GitHubService()
        with patch.object(
            service,
            "_get_json",
            return_value={
                "id": 18,
                "name": "evidence-retrieval",
                "full_name": "lab/evidence-retrieval",
                "html_url": "https://github.com/lab/evidence-retrieval",
                "description": "Code release",
                "stargazers_count": 1,
            },
        ):
            repository = service.summarize_repository_link(
                "https://github.com/lab/evidence-retrieval", provenance="paper_text"
            )
        GitHubService._add_readme_evidence(
            repository,
            "Implementation of Evidence Aware Retrieval for Research.",
            "Evidence Aware Retrieval for Research",
            "",
        )
        self.assertEqual("paper_document_link_unverified", repository["relationship_status"])
        self.assertEqual("github_readme_text_match", repository["provenance"])
        self.assertEqual(
            ["aware", "evidence", "research", "retrieval"],
            repository["readme_evidence"]["matched_title_terms"],
        )
        self.assertNotEqual("official", repository["relationship_status"])

    def test_repository_link_parser_rejects_non_github_hosts(self):
        service = GitHubService()
        self.assertIsNone(
            service.summarize_repository_link(
                "https://evil.example/github.com/owner/repository"
            )
        )

    def test_rate_limit_has_actionable_status(self):
        service = GitHubService()
        service._record_api_error(
            urllib.error.HTTPError(
                "https://api.github.com/search/repositories",
                403,
                "rate limited",
                {},
                None,
            )
        )
        self.assertEqual("rate_limited", service.last_search_status)
        self.assertIn("Retry later", service.last_search_error)

    @patch("urllib.request.urlopen")
    def test_configured_github_token_uses_bearer_auth(self, open_url):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return json.dumps({"items": []}).encode()

        open_url.return_value = FakeResponse()
        service = GitHubService(token="synthetic-test-token")
        service._get_json("https://api.github.com/search/repositories?q=graph")

        request = open_url.call_args.args[0]
        authorization = request.get_header("Authorization")
        self.assertTrue(authorization.startswith("Bearer "))
        self.assertTrue(authorization.endswith("synthetic-test-token"))


if __name__ == "__main__":
    unittest.main()
