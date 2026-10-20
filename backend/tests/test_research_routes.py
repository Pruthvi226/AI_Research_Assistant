import unittest
from unittest.mock import Mock, patch
from flask import Flask
from routes.research_routes import register_research_routes
from services.research_service import normalize, paper_by_doi
from gemini_engine import GeminiProviderError


class ResearchRoutesTest(unittest.TestCase):
    def setUp(self):
        self.engine = Mock(is_available=True)
        self.engine.generate_text.return_value = 'Evidence-backed analysis [1].'
        app = Flask(__name__)
        register_research_routes(app, lambda: self.engine)
        self.client = app.test_client()

    def test_question_validation_rejects_wrong_types_and_excess_history(self):
        for data in ([], {'question': 9}, {'question': 'x'}, {'question': 'a' * 4001}, {'question': 'valid', 'history': [None] * 11}):
            self.assertEqual(400, self.client.post('/api/research/answer', json=data).status_code)
        self.engine.generate_text.assert_not_called()

    def test_no_key_reports_unavailable_without_fake_answer(self):
        self.engine.is_available = False
        response = self.client.post('/api/research/answer', json={'question': 'retrieval augmented generation'})
        self.assertEqual(503, response.status_code)
        self.assertNotIn('response', response.get_json())

    @patch('routes.research_routes.search_papers')
    def test_answer_uses_server_retrieved_sources_and_follow_up_context(self, search):
        search.return_value = [{'title': 'Real metadata', 'url': 'https://doi.org/10.1000/example'}]
        response = self.client.post('/api/research/answer', json={
            'question': 'What are its limitations?', 'papers': [{'title': 'UNTRUSTED CLIENT RESULT'}],
            'history': [{'role': 'user', 'content': 'retrieval augmented generation'}],
        })
        self.assertEqual(200, response.status_code)
        self.assertEqual(search.return_value, response.get_json()['sources'])
        self.assertIn('retrieval augmented generation', search.call_args.args[0])
        self.assertNotIn('UNTRUSTED CLIENT RESULT', self.engine.generate_text.call_args.args[0])

    @patch('routes.research_routes.search_papers', side_effect=RuntimeError('Index unavailable'))
    def test_upstream_failure_is_actionable(self, search):
        self.assertEqual(502, self.client.post('/api/research/answer', json={'question': 'a valid topic'}).status_code)

    def test_review_rejects_invalid_selection(self):
        for ids in ([], ['10.1000/a'], ['10.1000/a'] * 2, [None, 12], ['10.1000/a'] * 9):
            self.assertEqual(400, self.client.post('/api/research/review', json={'paper_ids': ids}).status_code)

    @patch('routes.research_routes.paper_by_doi')
    def test_review_fetches_evidence_and_marks_missing_fields(self, lookup):
        lookup.return_value = {'title': 'A real paper', 'abstract': ''}
        response = self.client.post('/api/research/review', json={'paper_ids': ['10.1000/a', '10.1000/b']})
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, lookup.call_count)
        self.assertIn('Not reported', self.engine.generate_text.call_args.args[0])

    @patch('routes.research_routes.search_papers', return_value=[{'title': 'Real paper'}])
    def test_provider_failure_does_not_leak_internal_details(self, search):
        self.engine.generate_text.side_effect = ValueError('private-provider-secret')
        response = self.client.post('/api/research/answer', json={'question': 'a valid question'})
        self.assertEqual(502, response.status_code)
        self.assertNotIn('private-provider-secret', response.get_data(as_text=True))

    @patch('routes.research_routes.search_papers', return_value=[{'title': 'Real paper'}])
    def test_quota_errors_keep_actionable_public_status_and_code(self, search):
        self.engine.generate_text.side_effect = GeminiProviderError('Gemini quota is exhausted.', 'ai_rate_limited', 429)
        response = self.client.post('/api/research/answer', json={'question': 'a valid question'})
        self.assertEqual(429, response.status_code)
        self.assertEqual('ai_rate_limited', response.get_json()['code'])


class ResearchMetadataTest(unittest.TestCase):
    def test_normalizes_metadata_and_strips_abstract_tags(self):
        work = normalize({'DOI': '10.1000/test', 'title': ['A &amp; B'], 'abstract': '<jats:p>Real evidence</jats:p>', 'author': [{'given': 'Ada', 'family': 'Lovelace'}], 'published': {'date-parts': [[2024]]}})
        self.assertEqual('A & B', work['title'])
        self.assertEqual('Real evidence', work['abstract'])
        self.assertEqual(['Ada Lovelace'], work['authors'])
        self.assertEqual(2024, work['year'])

    def test_doi_validation_prevents_arbitrary_upstream_urls(self):
        for doi in ('https://localhost/secret', '../private', '', 100):
            with self.assertRaises(ValueError):
                paper_by_doi(doi)
