# Deploy to Google Cloud Run

This guide walks you through deploying the Google Workspace MCP Server to Google Cloud Run for production use.

## Why Cloud Run?

- **Serverless**: No infrastructure management
- **Auto-scaling**: Scales to zero when not in use
- **HTTPS**: Automatic SSL certificates
- **Cost-effective**: Pay only for what you use
- **Fast deployment**: Deploy in minutes

## Prerequisites

- Google Cloud Project with billing enabled
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed
- Docker installed (optional, Cloud Run can build for you)
- OAuth credentials configured (see [Google Cloud OAuth Setup](./google-cloud-oauth-setup.md))

## Step 1: Install gcloud CLI

### Windows
Download and run the installer from [cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)

### macOS
```bash
brew install --cask google-cloud-sdk
```

### Linux
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

## Step 2: Initialize gcloud

```bash
gcloud init
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

## Step 3: Enable Required Services

```bash
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.gcr.io
gcloud services enable cloudbuild.googleapis.com
```

## Step 4: Create Dockerfile

The project already includes a `Dockerfile`. Review it to ensure it meets your needs:

```dockerfile
# Multi-stage build for production
FROM python:3.11-slim as backend-builder

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM node:18-alpine as frontend-builder

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install
COPY . .
RUN pnpm build

FROM python:3.11-slim

WORKDIR /app
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=frontend-builder /app/dist /app/dist
COPY backend /app/backend

WORKDIR /app/backend
ENV PORT=8080
ENV HOST=0.0.0.0

EXPOSE 8080

CMD ["python", "main.py"]
```

## Step 5: Build and Deploy

### Option A: Let Cloud Run Build (Recommended)

```bash
gcloud run deploy google-workspace-mcp-server \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=YOUR_PROJECT_ID"
```

### Option B: Build Locally and Deploy

```bash
# Build Docker image
docker build -t gcr.io/YOUR_PROJECT_ID/google-workspace-mcp-server .

# Push to Google Container Registry
docker push gcr.io/YOUR_PROJECT_ID/google-workspace-mcp-server

# Deploy to Cloud Run
gcloud run deploy google-workspace-mcp-server \
  --image gcr.io/YOUR_PROJECT_ID/google-workspace-mcp-server \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

## Step 6: Set Environment Variables

After deployment, set your OAuth credentials:

```bash
gcloud run services update google-workspace-mcp-server \
  --region us-central1 \
  --set-env-vars="GOOGLE_CLIENT_ID=your-client-id" \
  --set-env-vars="GOOGLE_CLIENT_SECRET=your-client-secret" \
  --set-env-vars="OAUTH_REDIRECT_URI=https://your-service-url.run.app/oauth/callback" \
  --set-env-vars="OAUTH_SCOPES=https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/calendar"
```

## Step 7: Get Your Service URL

```bash
gcloud run services describe google-workspace-mcp-server \
  --region us-central1 \
  --format='value(status.url)'
```

You'll get a URL like: `https://google-workspace-mcp-server-abc123-uc.a.run.app`

## Step 8: Update OAuth Redirect URI

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **APIs & Services** > **Credentials**
3. Click on your OAuth 2.0 Client ID
4. Under **Authorized redirect URIs**, add:
   ```
   https://your-service-url.run.app/oauth/callback
   ```
5. Click **"Save"**

## Step 9: Test Your Deployment

Visit your service URL:
```
https://your-service-url.run.app/health
```

You should see:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-09T06:00:00",
  "sessions_active": 0
}
```

Test OAuth:
```
https://your-service-url.run.app/oauth/authorize
```

## Step 10: Configure Custom Domain (Optional)

### Map a Custom Domain

```bash
gcloud run domain-mappings create \
  --service google-workspace-mcp-server \
  --domain mcp.yourdomain.com \
  --region us-central1
```

Follow the instructions to update your DNS records.

## Monitoring and Logs

### View Logs
```bash
gcloud run services logs read google-workspace-mcp-server \
  --region us-central1 \
  --limit 50
```

### View Metrics
Go to [Cloud Console](https://console.cloud.google.com) > **Cloud Run** > Your Service > **Metrics**

## Cost Optimization

### Set Resource Limits
```bash
gcloud run services update google-workspace-mcp-server \
  --region us-central1 \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 10 \
  --min-instances 0
```

### Enable CPU Throttling
```bash
gcloud run services update google-workspace-mcp-server \
  --region us-central1 \
  --cpu-throttling
```

This reduces costs by throttling CPU when no requests are being processed.

## Security Best Practices

### Use Secret Manager for Credentials

```bash
# Create secrets
echo -n "your-client-id" | gcloud secrets create google-client-id --data-file=-
echo -n "your-client-secret" | gcloud secrets create google-client-secret --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding google-client-id \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Update service to use secrets
gcloud run services update google-workspace-mcp-server \
  --region us-central1 \
  --set-secrets="GOOGLE_CLIENT_ID=google-client-id:latest,GOOGLE_CLIENT_SECRET=google-client-secret:latest"
```

### Enable VPC Connector (Optional)
For enhanced security, connect to a VPC network.

## Troubleshooting

### Deployment Fails
- Check build logs: `gcloud builds list --limit=1`
- Verify Dockerfile syntax
- Ensure all dependencies are in requirements.txt

### Service Won't Start
- Check logs: `gcloud run services logs read`
- Verify environment variables are set correctly
- Check that PORT is set to 8080

### OAuth Not Working
- Verify redirect URI matches exactly
- Check that environment variables are set
- Ensure service is publicly accessible

## Next Steps

- [Configure MCP Clients](./mcp-client-setup.md) to use your production URL
- Set up monitoring and alerts
- Configure CI/CD for automatic deployments
