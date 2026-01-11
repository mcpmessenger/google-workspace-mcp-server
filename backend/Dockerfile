# Production image for Google Workspace MCP Server
FROM python:3.11-slim

# Set environment variables
ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies directly
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Expose port (metadata)
EXPOSE 8080

# Run with python directly to ensure our custom logging and port logic is used
CMD ["python", "main.py"]
