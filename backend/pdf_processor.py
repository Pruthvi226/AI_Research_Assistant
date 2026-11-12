"""
PDF Processor module for extracting and cleaning text from research paper PDFs.
Uses PyMuPDF (fitz) for extraction and applies formatting cleanup.
"""

import re
import shutil
from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from config import PDFConfig, UPLOAD_FOLDER


class PDFProcessor:
    """
    Extracts text from PDF files and cleans formatting.
    Removes references section and normalizes whitespace.
    """

    def __init__(self, upload_folder: Optional[Path] = None):
        """
        Initialize the PDF processor.

        Args:
            upload_folder: Base directory for uploaded files. Defaults to config UPLOAD_FOLDER.
        """
        if fitz is None:
            raise ImportError("PyMuPDF is required. Install with: pip install pymupdf")
        self.upload_folder = Path(upload_folder or UPLOAD_FOLDER)
        self.config = PDFConfig()

    def extract_text(self, pdf_path: str | Path) -> str:
        """
        Extract raw text from a PDF file.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Extracted text from all pages.

        Raises:
            FileNotFoundError: If the PDF file does not exist.
            ValueError: If the file is not a valid PDF or extraction fails.
        """
        path = Path(pdf_path)
        if not path.is_absolute():
            path = self.upload_folder / path
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError("File must be a PDF")

        try:
            return "\n".join(page["text"] for page in self.extract_pages(path))
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {e}") from e

    def extract_pages(self, pdf_path: str | Path) -> list:
        """Extract cleaned text per page with 1-based page numbers."""
        path = Path(pdf_path)
        if not path.is_absolute():
            path = self.upload_folder / path
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError("File must be a PDF")

        try:
            doc = fitz.open(path)
            if doc.needs_pass:
                doc.close()
                raise ValueError("This PDF is password-protected and cannot be processed.")
            metadata = {
                key: value
                for key, value in (doc.metadata or {}).items()
                if key in {"title", "author", "subject", "keywords", "creator", "producer", "creationDate"}
                and isinstance(value, str)
                and value.strip()
            }
            pages = []
            for page_index, page in enumerate(doc, start=1):
                text = self._clean_formatting(page.get_text("text"))
                method = "text"
                ocr_status = "not_needed"
                has_images = bool(page.get_images(full=True))
                if len(text) < 40 and has_images:
                    ocr_status = "unavailable"
                    if self.config.OCR_ENABLED and shutil.which("tesseract"):
                        scanned_before_limit = page_index <= self.config.OCR_MAX_PAGES
                        if scanned_before_limit:
                            try:
                                text_page = page.get_textpage_ocr(
                                    language=self.config.OCR_LANGUAGE,
                                    dpi=self.config.OCR_DPI,
                                    full=True,
                                )
                                ocr_text = self._clean_formatting(
                                    page.get_text("text", textpage=text_page)
                                )
                                if ocr_text:
                                    text = ocr_text
                                    method = "tesseract_ocr"
                                    ocr_status = "completed"
                                else:
                                    ocr_status = "no_text_detected"
                            except Exception:
                                ocr_status = "failed"
                        else:
                            ocr_status = "page_limit"
                    elif not self.config.OCR_ENABLED:
                        ocr_status = "disabled"
                elif not text:
                    ocr_status = "empty_page"
                if text:
                    page_data = {
                        "page": page_index,
                        "text": text,
                        "extraction_method": method,
                        "ocr_status": ocr_status,
                        "headings": self._find_headings(text),
                        "equations": self._find_equations(text, page_index),
                        "captions": self._find_captions(text, page_index),
                    }
                    page_data["document_metadata"] = metadata
                    pages.append(page_data)
                elif ocr_status != "not_needed":
                    page_data = {
                        "page": page_index,
                        "text": "",
                        "extraction_method": "none",
                        "ocr_status": ocr_status,
                        "headings": [],
                        "equations": [],
                        "captions": [],
                    }
                    page_data["document_metadata"] = metadata
                    pages.append(page_data)
            doc.close()
            return pages
        except Exception as e:
            raise ValueError(f"Failed to extract pages from PDF: {e}") from e

    @staticmethod
    def _find_headings(text: str) -> list:
        headings = []
        for line in text.splitlines():
            candidate = line.strip()
            if not candidate or len(candidate) > 100:
                continue
            if re.match(r"^(?:\d+(?:\.\d+)*\.?\s+)?[A-Z][A-Z0-9 ,:&()/-]{2,}$", candidate):
                headings.append(candidate)
        return headings[:30]

    @staticmethod
    def _find_equations(text: str, page_number: int) -> list:
        lines = [line.strip() for line in text.splitlines()]
        equations = []
        for index, line in enumerate(lines):
            if len(line) < 4 or len(line) > 500:
                continue
            math_markers = re.search(r"(?:=|≤|≥|≈|∑|∏|∫|√|→|←|\\frac|\\sum|\\mathbf|_[{A-Za-z0-9]|\\^[{A-Za-z0-9])", line)
            if not math_markers or not re.search(r"[A-Za-z]", line):
                continue
            context = " ".join(
                item for item in lines[max(0, index - 1): index + 2] if item
            )
            equations.append({
                "text": line,
                "latex": PDFProcessor._equation_to_latex(line),
                "page": page_number,
                "context": context[:1200],
                "extraction_method": "text_heuristic",
                "verification_status": "unverified",
            })
        return equations[:20]

    @staticmethod
    def _equation_to_latex(text: str) -> str:
        latex = text.strip().replace("*", r"\cdot ")
        for token, command in {
            "alpha": r"\alpha",
            "beta": r"\beta",
            "gamma": r"\gamma",
            "lambda": r"\lambda",
            "theta": r"\theta",
            "sigma": r"\sigma",
            "mu": r"\mu",
            "sum": r"\sum",
        }.items():
            latex = re.sub(
                rf"\b{token}\b",
                lambda _match, value=command: value,
                latex,
                flags=re.IGNORECASE,
            )
        return latex

    @staticmethod
    def _find_captions(text: str, page_number: int) -> list:
        return [
            {"page": page_number, "text": line.strip(), "verification_status": "unverified"}
            for line in text.splitlines()
            if re.match(r"^\s*(?:figure|fig\.|table)\s*\d+\b", line, re.IGNORECASE)
        ][:20]

    def _clean_formatting(self, text: str) -> str:
        """
        Clean extracted text: normalize whitespace, fix line breaks, remove excess newlines.

        Args:
            text: Raw extracted text.

        Returns:
            Cleaned text.
        """
        if not text or not text.strip():
            return ""
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Replace single newlines within sentences (likely line wraps) with space
        # Heuristic: line ending without period/question/exclamation followed by lowercase
        text = re.sub(r"(?<=[a-z,])\n(?=[a-z])", " ", text)
        # Normalize spaces
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" \n", "\n", text)
        text = re.sub(r"\n ", "\n", text)
        return text.strip()

    def _find_references_start(self, text: str) -> Optional[int]:
        """
        Find the character index where the references section begins.
        Uses common section headers and minimum word count for references.

        Args:
            text: Full document text.

        Returns:
            Character index of references section start, or None if not found.
        """
        text_lower = text.lower()
        lines = text.split("\n")
        current_pos = 0
        best_match_pos = None

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                current_pos += len(line) + 1
                continue
            line_lower = line_stripped.lower()
            # Check if this line looks like a references section header (often alone or with number)
            if any(
                ref in line_lower
                for ref in self.config.REFERENCE_SECTION_PATTERNS
            ):
                # Require it to be a short line (header-like)
                if len(line_stripped) < 80:
                    best_match_pos = current_pos
            current_pos += len(line) + 1

        if best_match_pos is None:
            return None
        # Verify there's enough content after this point to be references
        after = text[best_match_pos:]
        word_count = len(after.split())
        if word_count >= self.config.MIN_REFERENCE_SECTION_WORDS:
            return best_match_pos
        return None

    def remove_references_section(self, text: str) -> str:
        """
        Remove the references/bibliography section from the paper text.

        Args:
            text: Full document text.

        Returns:
            Text with references section removed.
        """
        ref_start = self._find_references_start(text)
        if ref_start is not None and ref_start > 100:
            return text[:ref_start].strip()
        return text

    def extract_references(self, text: str) -> dict:
        """
        Extract bibliography/references from the raw document text.
        Returns a dict mapping the reference key/number to the citation text.
        """
        ref_start = self._find_references_start(text)
        if ref_start is None:
            return {}
        
        ref_text = text[ref_start:]
        # Match brackets like [1], [2], or numbered lines like 1. 2. at the start of paragraphs
        matches = re.finditer(r'(?:\[(\d+)\]|^\s*(\d+)\.\s+)(.*?)(?=\[|\n\s*\d+[\.\)]|\n\n|\Z)', ref_text, re.MULTILINE | re.DOTALL)
        ref_map = {}
        for m in matches:
            num = m.group(1) or m.group(2)
            content = m.group(3).strip()
            # Clean up double spacing and line breaks
            content = re.sub(r'\s+', ' ', content)
            if num and content:
                ref_map[num] = content
        return ref_map

    def process(self, pdf_path: str | Path) -> str:
        """
        Full pipeline: extract text, clean formatting, remove references.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Cleaned full text of the paper (without references).
        """
        raw = self.extract_text(pdf_path)
        cleaned = self._clean_formatting(raw)
        return self.remove_references_section(cleaned)
