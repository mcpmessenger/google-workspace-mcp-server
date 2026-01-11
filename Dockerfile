# Root Dockerfile for Google Workspace MCP Server
FROM python:3.11-slim

# Set environment variables
ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY google-workspace-mcp-server/backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY google-workspace-mcp-server/backend /app

# Expose port (metadata)
EXPOSE 8080

# Run with uvicorn
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --log-level info
