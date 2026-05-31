# Use a slim Python base image to support pre-compiled wheels for scientific/vector packages
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000

# Set working directory
WORKDIR /app

# Install system dependencies needed for basic text parsing & building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Ensure directory for uploads and vector indices exists
RUN mkdir -p /app/uploads /app/indices

# Expose port
EXPOSE 5000

# Run the Flask server
CMD ["python", "app.py"]
