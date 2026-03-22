# ---- Stage 1: Frontend bauen ----
FROM node:22-alpine AS frontend-build

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Backend + Frontend Bundle ----
FROM python:3.14-slim

WORKDIR /app

# System-Abhaengigkeiten fuer Pillow
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libjpeg62-turbo-dev libwebp-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

# Python-Abhaengigkeiten installieren
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir .

# Backend-Code kopieren
COPY backend/app ./app

# Frontend-Build als statische Dateien einbinden
COPY --from=frontend-build /build/dist ./static

# Datenverzeichnis
RUN mkdir -p /app/data

EXPOSE 8000

# Uvicorn starten
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
