# Backend-only Dockerfile for Google Cloud Run
FROM python:3.11-slim

WORKDIR /app

# Install dependencies directly to avoid requirements.txt encoding issues
# Using looser versions to let pip resolve conflicts
RUN pip install --no-cache-dir \
    "fastapi>=0.100.0" \
    "uvicorn>=0.20.0" \
    "fastmcp>=0.1.0" \
    "google-auth>=2.0.0" \
    "google-auth-oauthlib>=1.0.0" \
    "google-auth-httplib2>=0.1.0" \
    "google-api-python-client>=2.0.0" \
    "python-dotenv>=1.0.0" \
    "pydantic>=2.0.0" \
    "redis>=5.0.0" \
    "httpx>=0.25.0" \
    "google-cloud-secret-manager>=2.0.0"

# Copy application code
COPY . .

# Environment variables
ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "main.py"]
