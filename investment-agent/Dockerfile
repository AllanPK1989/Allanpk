# Build the PWA, then serve it and the API from one small Python image (fits Render's free tier).
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 STATIC_DIR=/app/static
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt
COPY backend/app ./app
COPY --from=web /web/dist ./static
RUN useradd --system --uid 10001 appuser && mkdir -p /app/data && chown appuser /app/data
USER appuser
EXPOSE 8000
# Render sets PORT. --proxy-headers so redirects/cookies see https; the app reads the client IP itself.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
