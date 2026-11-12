import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from pdf_processor import PDFProcessor


class PDFProcessorTest(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[2] / ".codex-test" / "backend-tests"
        test_root.mkdir(parents=True, exist_ok=True)
        self.workspace = tempfile.TemporaryDirectory(dir=test_root)
        self.root = Path(self.workspace.name)
        self.processor = PDFProcessor(self.root)

    def tearDown(self):
        self.workspace.cleanup()

    def test_extracts_page_headings_math_and_reference_candidates(self):
        document = fitz.open()
        page = document.new_page()
        page.insert_text((50, 50), "METHODS")
        page.insert_text((50, 90), "The paper defines the learning rule and reports its context.")
        page.insert_text((50, 130), "x_i = alpha * w_i")
        path = self.root / "text.pdf"
        document.save(path)
        document.close()

        pages = self.processor.extract_pages(path)

        self.assertEqual(1, pages[0]["page"])
        self.assertIn("METHODS", pages[0]["headings"])
        self.assertEqual("x_i = alpha * w_i", pages[0]["equations"][0]["text"])
        self.assertIn(r"\alpha", pages[0]["equations"][0]["latex"])
        self.assertEqual("text", pages[0]["extraction_method"])

    def test_scanned_page_reports_ocr_unavailable_instead_of_succeeding_empty(self):
        document = fitz.open()
        page = document.new_page()
        pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), 0)
        page.insert_image(fitz.Rect(40, 40, 200, 200), pixmap=pixmap)
        path = self.root / "scan.pdf"
        document.save(path)
        document.close()

        with patch("pdf_processor.shutil.which", return_value=None):
            pages = self.processor.extract_pages(path)

        self.assertEqual("", pages[0]["text"])
        self.assertEqual("unavailable", pages[0]["ocr_status"])
        self.assertEqual("none", pages[0]["extraction_method"])

    @unittest.skipUnless(shutil.which("tesseract"), "Tesseract OCR is not installed")
    def test_scanned_page_uses_tesseract_to_extract_text(self):
        source = fitz.open()
        source_page = source.new_page(width=612, height=792)
        source_page.insert_textbox(
            fitz.Rect(50, 100, 560, 240),
            "SCANNED RESEARCH TEST\nRetrieval precision improves.",
            fontsize=24,
        )
        scanned_image = source_page.get_pixmap(
            matrix=fitz.Matrix(2, 2), alpha=False
        ).tobytes("png")
        source.close()

        document = fitz.open()
        page = document.new_page(width=612, height=792)
        page.insert_image(page.rect, stream=scanned_image)
        path = self.root / "scanned-text.pdf"
        document.save(path)
        document.close()

        with patch.object(self.processor.config, "OCR_ENABLED", True):
            result = self.processor.extract_pages(path)[0]

        self.assertEqual("completed", result["ocr_status"])
        self.assertEqual("tesseract_ocr", result["extraction_method"])
        self.assertIn("SCANNED RESEARCH TEST", result["text"].upper())
        self.assertIn("retrieval precision", result["text"].lower())

    def test_rejects_encrypted_pdf_with_actionable_error(self):
        document = fitz.open()
        document.new_page()
        path = self.root / "locked.pdf"
        document.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret")
        document.close()

        with self.assertRaisesRegex(ValueError, "password-protected"):
            self.processor.extract_pages(path)


if __name__ == "__main__":
    unittest.main()
