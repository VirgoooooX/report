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

CMD ["python", "backend/api.py"]
