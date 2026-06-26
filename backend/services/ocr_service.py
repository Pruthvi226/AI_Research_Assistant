from pathlib import Path


class OCRService:
    def extract_text_from_image(self, image_path: str) -> str:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        try:
            from PIL import Image
            import pytesseract
        except ImportError as exc:
            raise RuntimeError("OCR requires Pillow and pytesseract to be installed.") from exc

        try:
            text = pytesseract.image_to_string(Image.open(path))
        except Exception as exc:
            raise ValueError(f"OCR failure: {exc}") from exc

        cleaned = " ".join(text.split())
        if not cleaned:
            raise ValueError("OCR did not detect readable equation text.")
        return cleaned
