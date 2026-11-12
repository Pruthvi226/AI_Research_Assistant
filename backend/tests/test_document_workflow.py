"""Exercise real PDF ingestion, persisted retrieval, chat and artifact generation."""
import io
import tempfile
import unittest
import time
from zipfile import ZipFile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
import fitz
import app as module
from database import DBManager


class DocumentWorkflowTest(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[2] / '.codex-test' / 'backend-tests'
        test_root.mkdir(parents=True, exist_ok=True)
        self.workspace = tempfile.TemporaryDirectory(dir=test_root)
        self.root = Path(self.workspace.name)
        self.db = DBManager(str(self.root / 'research.db'))
        self.patches = [patch.object(module, 'db', self.db), patch.object(module.auth_service, 'database', self.db),
                        patch.object(module.rag_agent, 'db', self.db),
                        patch.object(module.orchestrator_agent, 'db', self.db), patch.object(module, 'UPLOAD_FOLDER', self.root),
                        patch.object(module, 'get_active_gemini_engine', return_value=type('Offline', (), {'is_available': False})()),
                        ]
        for p in self.patches:
            p.start()
        self.client = module.app.test_client()
        with module.auth_rate_limiter._lock:
            module.auth_rate_limiter._hits.clear()
        account = self.client.post('/api/auth/register', json={
            'email': f'test-{self.root.name}@example.test',
            'password': 'research-password-42',
        })
        assert account.status_code == 201, account.get_json()
        self.token = account.get_json()['token']
        self.client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {self.token}'

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        module._active_index_key = None
        # SQLite connections are short lived; collect finalized contexts before Windows cleanup.
        import gc
        gc.collect()
        expected = Path(__file__).resolve().parents[2] / '.codex-test' / 'backend-tests'
        assert self.root.resolve().is_relative_to(expected.resolve())
        self.workspace.cleanup()

    def test_pdf_to_summary_retrieval_history_report_code_and_equation(self):
        pdf = fitz.open()
        pdf.set_metadata({"title": "Retrieval Study"})
        page = pdf.new_page()
        page.insert_textbox(fitz.Rect(40, 40, 550, 800), '\n'.join([
            'Retrieval Study', 'Abstract',
            'We propose a lexical retrieval approach for research assistants. The method ranks document sentences by token overlap.',
            'Methodology', 'Our algorithm indexes paragraphs and retrieves relevant passages. The dataset contains 120 public papers.',
            'Results', 'The evaluation reports precision of 0.82 on the dataset. Retrieval improves evidence selection.',
            'Limitations', 'A limitation is the small evaluation dataset. Future work should evaluate multilingual papers.',
            'Equation: z_i = alpha * x_i',
            'Figure 1: Overview of the retrieval pipeline.',
        ]), fontsize=11)
        content = pdf.tobytes(); pdf.close()
        upload = self.client.post('/api/upload/pdf', data={'file': (io.BytesIO(content), 'retrieval.pdf')})
        self.assertEqual(200, upload.status_code, upload.get_json())
        doc = upload.get_json(); doc_id = doc['session_id']
        self.assertIn('local', doc['performance']['mode'])
        extraction = doc['performance']['pdf_extraction']
        self.assertEqual('Retrieval Study', extraction['document_metadata']['title'])
        self.assertTrue(any('Figure 1:' in item['text'] for item in extraction['caption_candidates']))
        self.assertTrue(doc['summary']['abstract'])
        detail = self.client.get(f'/api/documents/{doc_id}')
        self.assertEqual(200, detail.status_code)
        self.assertEqual(doc['performance']['mode'], detail.get_json()['performance']['mode'])
        self.assertIn('methodology', detail.get_json()['agent_analysis'])
        self.assertTrue(detail.get_json()['summary']['equations'])
        self.assertEqual('hybrid_bm25', detail.get_json()['performance']['retrieval'])
        original = self.client.get(f'/api/documents/{doc_id}/file')
        self.assertEqual(200, original.status_code); original.close()
        chat = self.client.post('/api/chat', json={'question': 'What dataset was evaluated?', 'session_id': doc_id, 'agent': 'rag'}).get_json()
        self.assertIn('120', chat['response'])
        self.assertTrue(chat['sources'])
        self.assertEqual('local_extractive', chat['artifacts']['mode'])
        history = self.client.get('/api/history', query_string={'session_id': doc_id}).get_json()
        self.assertEqual(2, len(history['history']))
        report = self.client.get(f'/api/documents/{doc_id}/export/markdown')
        self.assertEqual(200, report.status_code); report.close()
        analysis = self.client.post('/api/chat', json={'question': 'Analyze this paper', 'session_id': doc_id, 'agent': 'research'}).get_json()
        self.assertIn('methodology', analysis['artifacts']['analysis'])
        code = self.client.post('/api/code', json={'session_id': doc_id, 'query': 'Generate a retrieval scaffold'}).get_json()
        self.assertEqual('local_template', code['artifacts']['mode'])
        compile(code['code'], '<generated-scaffold>', 'exec')
        bundle = self.client.get(code['download_url'])
        self.assertEqual(200, bundle.status_code)
        with ZipFile(io.BytesIO(bundle.data)) as archive:
            self.assertIn('train.py', archive.namelist())
            self.assertIn('evaluate.py', archive.namelist())
            self.assertIn('config.json', archive.namelist())
            self.assertIn('source_map.json', archive.namelist())
        equation = self.client.post('/api/equation', json={'equation': 'y = alpha * x'}).get_json()
        self.assertIn('latex', equation['artifacts'])
        contextual_equation = self.client.post('/api/equation', json={
            'equation': 'z_i = alpha * x_i',
            'context': 'The paper states alpha denotes the regularization weight.',
            'page': 4,
            'filename': 'retrieval.pdf',
        }).get_json()
        self.assertIn('regularization weight', contextual_equation['artifacts']['explanation'])
        briefing_pdf = self.client.get(f'/api/documents/{doc_id}/export/briefing.pdf')
        self.assertEqual(200, briefing_pdf.status_code)
        self.assertEqual('application/pdf', briefing_pdf.mimetype)
        with fitz.open(stream=briefing_pdf.data, filetype='pdf') as rendered:
            self.assertIn('Research briefing', rendered[0].get_text())
        briefing = self.client.post('/api/podcast', json={'session_id': doc_id, 'generate_audio': False}).get_json()
        self.assertTrue(briefing['script']); self.assertFalse(briefing['url'])

    def test_upload_and_payload_failures_return_client_errors(self):
        self.assertEqual(400, self.client.post('/api/upload/pdf', data={}).status_code)
        self.assertEqual(400, self.client.post('/api/upload/pdf', data={'file': (io.BytesIO(b'no'), 'bad.exe')}).status_code)
        invalid_pdf = self.client.post(
            '/api/upload/pdf',
            data={'file': (io.BytesIO(b'not a PDF'), 'fake.pdf')},
        )
        self.assertEqual(400, invalid_pdf.status_code)
        for value in ([], {'question': 42}, {'session_id': ['bad'], 'question': 'hello'}):
            self.assertEqual(400, self.client.post('/api/chat', json=value).status_code)
        self.assertEqual(
            400,
            self.client.post('/api/equation', json={'equation': 'x = y', 'page': True}).status_code,
        )
        self.assertEqual(
            400,
            self.client.post('/api/github', json={'query': 'retrieval', 'doi': 42}).status_code,
        )

    def test_async_jobs_and_concurrent_document_retrieval_keep_sources_separate(self):
        ids = []
        for filename, dataset in [('earth.pdf', '120 earth images'), ('moon.pdf', '900 lunar samples')]:
            pdf = fitz.open()
            page = pdf.new_page()
            page.insert_textbox(fitz.Rect(40, 40, 550, 800),
                                f'Abstract. This study evaluates a retrieval algorithm. The dataset contains {dataset}. '
                                'Methodology. We index the examples using lexical representations. '
                                'Results. Retrieval improves evidence selection. A limitation is limited evaluation.', fontsize=11)
            content = pdf.tobytes(); pdf.close()
            response = self.client.post('/api/upload/pdf?async=true', data={'file': (io.BytesIO(content), filename)})
            self.assertEqual(202, response.status_code)
            job_id = response.get_json()['job_id']
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                job = self.client.get(f'/api/jobs/{job_id}').get_json()['job']
                if job['status'] in {'done', 'failed'}:
                    break
                time.sleep(0.05)
            self.assertEqual('done', job['status'], job)
            ids.append((job['result']['session_id'], filename))

        def ask_document(selection):
            doc_id, filename = selection
            client = module.app.test_client()
            client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {self.token}'
            result = client.post('/api/chat', json={'question': 'What dataset was used?', 'session_id': doc_id, 'agent': 'rag'}).get_json()
            return filename, result['sources']

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(ask_document, ids * 3))
        for filename, sources in results:
            self.assertTrue(sources)
            self.assertTrue(all(filename in source for source in sources), sources)
