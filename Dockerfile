# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend assets
COPY --from=frontend-builder /app/frontend/dist ./static

# Runtime config
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5050
ENV REPORT_RAWDATA_DIR=/app/rawdata
ENV REPORT_DB_PATH=/app/db/report.db

EXPOSE 5050

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5050/api/dashboard/overview')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "1", "backend.api:app"]
