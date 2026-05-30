FROM python:3.12-slim

WORKDIR /app

# System deps for Chroma, Celery, Redis, build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Production install (includes all hardening deps)
RUN pip install -e . --no-cache-dir

# Production hardening: logging, tracing stubs ready
ENV PYTHONUNBUFFERED=1 \
    CHROMA_TELEMETRY=false \
    REDIS_URL=redis://redis:6379/0

# Default: FastAPI (worker started separately via compose or command)
CMD ["uvicorn", "app.main_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]
