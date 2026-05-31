"""
PDF Processor module for extracting and cleaning text from research paper PDFs.
Uses PyMuPDF (fitz) for extraction and applies formatting cleanup.
"""

import re
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
            doc = fitz.open(path)
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            return "\n".join(text_parts)
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {e}") from e

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

