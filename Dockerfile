# Dockerfile — Fast build for QuickEats backend
FROM python:3.12-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install deps first for layer caching
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

EXPOSE 8000
CMD ["uvicorn", "backend_fastapi_main:app", "--host", "0.0.0.0", "--port", "8000"]
