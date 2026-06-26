from pathlib import Path


PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


def require_query(query: str) -> str:
    cleaned = (query or "").strip()
    if not cleaned:
        raise ValueError("Query cannot be empty.")
    return cleaned


def validate_extension(filename: str, allowed_extensions) -> None:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise ValueError(f"Invalid file type. Allowed extensions: {allowed}")
