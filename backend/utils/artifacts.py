import mimetypes
from pathlib import Path
from typing import Dict

from config import GENERATED_CODE_FOLDER, GENERATED_MARKDOWN_FOLDER


GENERATED_MARKDOWN_FOLDER.mkdir(parents=True, exist_ok=True)
GENERATED_CODE_FOLDER.mkdir(parents=True, exist_ok=True)


def write_text_artifact(folder: Path, filename: str, content: str) -> str:
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in filename)
    path = folder / safe_name
    path.write_text(content or "", encoding="utf-8")
    return str(path)


def artifact_response_headers(path: str) -> Dict[str, str]:
    mime, _ = mimetypes.guess_type(path)
    return {"mimetype": mime or "application/octet-stream"}
