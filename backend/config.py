"""
Configuration settings for the AI Research Assistant backend.
Centralizes all configurable parameters for the application.
"""

import os
from pathlib import Path


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _csv_env(name: str, default: list) -> list:
    value = os.environ.get(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_FOLDER = Path(os.environ.get("DATA_FOLDER", BASE_DIR / "data")).resolve()
UPLOAD_FOLDER = Path(os.environ.get("UPLOAD_FOLDER", DATA_FOLDER / "uploads")).resolve()
INDEX_FOLDER = Path(os.environ.get("INDEX_FOLDER", DATA_FOLDER / "faiss_index")).resolve()
AUDIO_FOLDER = Path(os.environ.get("AUDIO_FOLDER", DATA_FOLDER / "generated_audio")).resolve()
GENERATED_CODE_FOLDER = Path(os.environ.get("GENERATED_CODE_FOLDER", DATA_FOLDER / "generated_code")).resolve()
GENERATED_MARKDOWN_FOLDER = Path(os.environ.get("GENERATED_MARKDOWN_FOLDER", DATA_FOLDER / "generated_markdown")).resolve()


def _sqlite_path_from_url(value: str) -> str:
    if not value:
        return ""
    if value.startswith("sqlite:///"):
        path_value = value.replace("sqlite:///", "", 1)
        path = Path(path_value)
        if not path.is_absolute():
            path = BASE_DIR / path
        return str(path.resolve())
    return value

# Ensure directories exist
DATA_FOLDER.mkdir(parents=True, exist_ok=True)
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
INDEX_FOLDER.mkdir(parents=True, exist_ok=True)
AUDIO_FOLDER.mkdir(parents=True, exist_ok=True)
GENERATED_CODE_FOLDER.mkdir(parents=True, exist_ok=True)
GENERATED_MARKDOWN_FOLDER.mkdir(parents=True, exist_ok=True)

# Flask settings
class FlaskConfig:
    """Flask application configuration."""
    APP_NAME = os.environ.get("APP_NAME", "Scientia.ai")
    APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "local")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    MAX_UPLOAD_MB = _int_env("MAX_UPLOAD_MB", 50)
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
    CORS_ORIGINS = _csv_env(
        "CORS_ORIGINS",
        ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"],
    )
    REQUEST_ID_HEADER = os.environ.get("REQUEST_ID_HEADER", "X-Request-ID")
    UPLOAD_EXTENSIONS = {".pdf"}
    ALLOWED_EXTENSIONS = {"pdf"}
    DATABASE_URI = _sqlite_path_from_url(
        os.environ.get("DATABASE_URL", os.environ.get("DATABASE_URI", str(DATA_FOLDER / "scientia.db")))
    )
    DEBUG = _bool_env("FLASK_DEBUG", False)
    MAX_ANALYSIS_CHARS = _int_env("MAX_ANALYSIS_CHARS", 300000)
    MAX_QA_CONTEXT_CHARS = _int_env("MAX_QA_CONTEXT_CHARS", 12000)
    RATE_LIMIT_PER_MINUTE = _int_env("RATE_LIMIT_PER_MINUTE", 120)
    RATE_LIMIT_WINDOW_SECONDS = _int_env("RATE_LIMIT_WINDOW_SECONDS", 60)
    JOB_WORKERS = _int_env("JOB_WORKERS", 3)
    JOB_RETENTION_LIMIT = _int_env("JOB_RETENTION_LIMIT", 500)
    JOB_MAX_IN_FLIGHT = _int_env("JOB_MAX_IN_FLIGHT", 50)


def validate_runtime_environment() -> list:
    """Return warnings for missing optional runtime dependencies or config."""
    warnings = []
    if FlaskConfig.SECRET_KEY == "dev-secret-key-change-in-production":
        warnings.append("SECRET_KEY uses the development default; set a strong value before production deployment.")
    if not AIConfig.GEMINI_API_KEY:
        warnings.append("GEMINI_API_KEY is not set; cloud LLM features will use local fallbacks.")
    if not os.environ.get("GITHUB_TOKEN"):
        warnings.append("GITHUB_TOKEN is not set; GitHub API rate limits may be lower.")
    for folder_name, folder in {
        "DATA_FOLDER": DATA_FOLDER,
        "UPLOAD_FOLDER": UPLOAD_FOLDER,
        "INDEX_FOLDER": INDEX_FOLDER,
        "AUDIO_FOLDER": AUDIO_FOLDER,
    }.items():
        if not folder.exists():
            warnings.append(f"{folder_name} does not exist: {folder}")
    return warnings


# PDF processing
class PDFConfig:
    """PDF extraction and processing settings."""
    # Section headers that typically precede references (case-insensitive patterns)
    REFERENCE_SECTION_PATTERNS = [
        "references",
        "bibliography",
        "works cited",
        "reference list",
    ]
    # Minimum words to consider as main content (skip references)
    MIN_REFERENCE_SECTION_WORDS = 50


# Text chunking
class ChunkerConfig:
    """Text chunking configuration for semantic splitting."""
    TARGET_CHUNK_WORDS = 500
    OVERLAP_WORDS = 50
    MIN_CHUNK_WORDS = 100
    MAX_CHUNK_WORDS = 700


# Embeddings & FAISS
class EmbeddingConfig:
    """Embedding model and FAISS index settings."""
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    FAISS_INDEX_TYPE = "flat"  # "flat" for exact search, "ivf" for approximate
    TOP_K_RESULTS = 5  # Default number of chunks to retrieve for QA
    USE_SEMANTIC_EMBEDDINGS = _bool_env("USE_SEMANTIC_EMBEDDINGS", False)


# Summarization
class SummarizerConfig:
    """Summarization model settings."""
    MODEL_NAME = "facebook/bart-large-cnn"
    MAX_LENGTH = 150
    MIN_LENGTH = 30
    SECTION_SUMMARY_MAX_LENGTH = 100
    USE_TRANSFORMER_FALLBACK = _bool_env("USE_TRANSFORMER_FALLBACK", False)


# Research insights & QA
class InsightsConfig:
    """Research insights and QA generation settings."""
    # Model for prompt-based generation (smaller for speed; can use same as summarizer)
    GENERATION_MODEL = "facebook/bart-large-cnn"
    MAX_NEW_TOKENS = 200
    NUM_CONTRIBUTIONS = 5
    NUM_LIMITATIONS = 3
    NUM_FUTURE_IDEAS = 5
    NUM_PAPER_TITLES = 3
    NUM_HIGHLIGHT_SENTENCES = 5
    USE_TRANSFORMER_FALLBACK = _bool_env("USE_TRANSFORMER_FALLBACK", False)


# Advanced AI & LLM settings
class AIConfig:
    """Configuration for cloud LLM APIs."""
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    PROVIDER = os.environ.get("AI_PROVIDER", "gemini")  # "gemini", "openai", "local"
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

