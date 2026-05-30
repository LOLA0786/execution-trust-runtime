FROM python:3.12-slim

WORKDIR /app

# Install system deps for Celery/Redis/SQLAlchemy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install -e .[test] --no-cache-dir

# Default to FastAPI + Celery worker (override in compose if needed)
CMD ["uvicorn", "app.main_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]
