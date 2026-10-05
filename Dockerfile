# Backend Dockerfile for MinePulse AI FastAPI Application
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PostgreSQL driver (psycopg2) and compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code and scripts
COPY backend /app/backend
COPY scripts /app/scripts
COPY data /app/data

# Environment variables defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PORT=8000

# Expose port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# Start Uvicorn ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
