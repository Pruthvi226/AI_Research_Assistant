import json
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
from gemini_engine import GeminiEngine


class GeminiTransportTest(unittest.TestCase):
    @patch('gemini_engine.urlopen')
    def test_key_is_in_header_timeout_is_bounded_and_json_mode_is_supported(self, transport):
        response = MagicMock()
        response.read.return_value = json.dumps({'candidates': [{'content': {'parts': [{'text': '{"summary":"ok"}'}]}}]}).encode()
        transport.return_value.__enter__.return_value = response
        engine = GeminiEngine('private-test-credential')
        self.assertEqual({'summary': 'ok'}, engine.generate_json('Summarize the evidence'))
        request = transport.call_args.args[0]
        self.assertNotIn('private-test-credential', request.full_url)
        self.assertEqual('private-test-credential', request.get_header('X-goog-api-key'))
        self.assertEqual(35, transport.call_args.kwargs['timeout'])
        self.assertEqual('application/json', json.loads(request.data)['generationConfig']['responseMimeType'])

    @patch('gemini_engine.urlopen', side_effect=HTTPError('secret-url', 429, 'private detail', {}, None))
    def test_provider_errors_are_sanitized(self, transport):
        with self.assertRaisesRegex(ValueError, 'AI provider request failed'):
            GeminiEngine('private-test-credential').generate_text('test')
