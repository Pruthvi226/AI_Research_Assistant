import fitz  # PyMuPDF
from docx import Document as DocxDocument
from typing import List, Dict, Any
import os

class DocumentService:
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        doc = DocxDocument(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    @staticmethod
    def process_file(file_path: str) -> str:
        _, ext = os.path.splitext(file_path)
        if ext.lower() == ".pdf":
            return DocumentService.extract_text_from_pdf(file_path)
        elif ext.lower() == ".docx":
            return DocumentService.extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

document_service = DocumentService()
