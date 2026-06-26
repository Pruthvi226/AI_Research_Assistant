from pathlib import Path
from typing import Dict, Tuple

from pdf_processor import PDFProcessor


class PDFService:
    def __init__(self):
        self.processor = PDFProcessor()

    def extract_text(self, path: str | Path) -> str:
        raw = self.processor.extract_text(path)
        cleaned = self.processor._clean_formatting(raw)
        return self.processor.remove_references_section(cleaned)

    def extract_text_and_references(self, path: str | Path) -> Tuple[str, Dict[str, str]]:
        raw = self.processor.extract_text(path)
        cleaned = self.processor._clean_formatting(raw)
        references = self.processor.extract_references(cleaned)
        return self.processor.remove_references_section(cleaned), references
