# ── CareerOS - Backend ──────────────────────────
FROM python:3.11-slim

# Install system deps (some Python packages need compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/
COPY agent/ ./agent/
COPY data/ ./data/

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create upload temp dir
RUN mkdir -p /app/tmp && chmod 777 /app/tmp

EXPOSE 8000

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
