# Dockerfile for Google Workspace MCP Server
# Multi-stage build for optimized production image

# Stage 1: Build Python backend dependencies
FROM python:3.11-slim as backend-builder

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Build frontend
FROM node:18-alpine as frontend-builder

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile

COPY client ./client
COPY server ./server
COPY shared ./shared
COPY tsconfig.json tsconfig.node.json vite.config.ts ./

RUN pnpm build

# Stage 3: Production image
FROM python:3.11-slim

# Install Node.js for serving frontend
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python dependencies
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy built frontend
COPY --from=frontend-builder /app/dist /app/dist

# Copy backend code
COPY backend /app/backend

# Set working directory to backend
WORKDIR /app/backend

# Environment variables
ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run the application
CMD ["python", "main.py"]
