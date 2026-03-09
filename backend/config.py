"""
Configuration settings for the AI Research Assistant backend.
Centralizes all configurable parameters for the application.
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR.parent / "uploads"
INDEX_FOLDER = BASE_DIR / "indices"

# Ensure directories exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
INDEX_FOLDER.mkdir(parents=True, exist_ok=True)

# Flask settings
class FlaskConfig:
    """Flask application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max file size
    UPLOAD_EXTENSIONS = {".pdf"}
    ALLOWED_EXTENSIONS = {"pdf"}


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


# Summarization
class SummarizerConfig:
    """Summarization model settings."""
    MODEL_NAME = "facebook/bart-large-cnn"
    MAX_LENGTH = 150
    MIN_LENGTH = 30
    SECTION_SUMMARY_MAX_LENGTH = 100


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
