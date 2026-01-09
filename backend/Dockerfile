# Multi-stage build using uv for fast dependency resolution
FROM ghcr.io/astral-sh/uv:latest AS builder

WORKDIR /app

# Copy project files
COPY pyproject.toml .

# Install dependencies with uv
RUN uv pip install --system -r <(uv pip compile pyproject.toml)

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
COPY main.py .
COPY .env* ./

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV HOST=0.0.0.0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run application
CMD ["python", "main.py"]
