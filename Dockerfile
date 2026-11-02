FROM python:3.12-slim

WORKDIR /app

# System deps (gcc needed for some torch wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Ensure the data directory exists for SQLite
RUN mkdir -p /app/data

# Expose the FastAPI port
EXPOSE 8000

# Healthcheck used by Docker Compose and Kubernetes
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the chat server (FastAPI + Prometheus metrics on /metrics)
CMD ["uvicorn", "chat_server:app", "--host", "0.0.0.0", "--port", "8000"]
