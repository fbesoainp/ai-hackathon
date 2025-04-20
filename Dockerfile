# Dockerfile — Fast build for QuickEats backend
FROM python:3.12-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install deps first for layer caching
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


RUN pip install --no-cache-dir --upgrade google-generativeai


# Copy source
COPY . .

RUN modal token set --token-id ak-I6Npsbs1OgRshyNO6IZPir --token-secret as-e1KncGcQueLPpiEZcKdouf --profile=pairfecto
RUN modal profile activate pairfecto
RUN modal deploy embed_modal.py
RUN modal deploy location_modal.py

EXPOSE 8000
CMD ["uvicorn", "backend_core:app", "--host", "0.0.0.0", "--port", "8000"]
