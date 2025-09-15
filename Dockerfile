# File: Dockerfile
# Purpose: Container image for demo-webhook-handle FastAPI service.
# Why: Enables reproducible deploys on Oracle VM behind NGINX reverse proxy.
# Related: app/main.py, docker-compose.yml, ops/nginx/webhook-handle.conf

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime deps (pinning kept light for demo)
RUN pip install --no-cache-dir fastapi==0.115.0 uvicorn[standard]==0.30.6

# Copy app source
COPY app ./app

EXPOSE 8004

# Default PORT env is honored by uvicorn via CMD
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
