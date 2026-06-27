# Use a slim Python base image to support pre-compiled wheels for scientific/vector packages
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000 \
    APP_NAME=Scientia.ai \
    APP_VERSION=1.0.0 \
    ENVIRONMENT=production \
    REQUEST_ID_HEADER=X-Request-ID \
    MAX_UPLOAD_MB=50 \
    DATA_FOLDER=/app/data \
    UPLOAD_FOLDER=/app/data/uploads \
    INDEX_FOLDER=/app/data/faiss_index \
    AUDIO_FOLDER=/app/data/generated_audio \
    GENERATED_CODE_FOLDER=/app/data/generated_code \
    GENERATED_MARKDOWN_FOLDER=/app/data/generated_markdown \
    DATABASE_URL=sqlite:////app/data/scientia.db \
    RATE_LIMIT_PER_MINUTE=120 \
    RATE_LIMIT_WINDOW_SECONDS=60 \
    JOB_WORKERS=3 \
    JOB_MAX_IN_FLIGHT=50 \
    JOB_RETENTION_LIMIT=500 \
    USE_SEMANTIC_EMBEDDINGS=false \
    USE_TRANSFORMER_FALLBACK=false \
    FLASK_DEBUG=false

# Set working directory
WORKDIR /app

# System runtime libraries for OCR and vector/search packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends tesseract-ocr libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements_docker.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements_docker.txt

# Copy source code
COPY . .

# Ensure directory for uploads, vector indices, generated outputs, and SQLite exists
RUN mkdir -p /app/data/uploads /app/data/faiss_index /app/data/generated_audio /app/data/generated_code /app/data/generated_markdown

# Expose port
EXPOSE 5000

# Run the Flask server behind a lightweight WSGI server
CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "app:app"]
