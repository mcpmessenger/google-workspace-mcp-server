# Cloud Run Deployment Guide

## Prerequisites

- Google Cloud Project with billing enabled
- `gcloud` CLI installed: https://cloud.google.com/sdk/docs/install
- Docker installed locally
- Appropriate IAM permissions (Cloud Run Admin, Service Account Admin)

## Step 1: Set Up Google Cloud Project

```bash
# Set project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable iam.googleapis.com
```

## Step 2: Create Service Account

```bash
# Create service account for MCP server
gcloud iam service-accounts create google-workspace-mcp \
  --display-name="Google Workspace MCP Server"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:google-workspace-mcp@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Create key for local development (optional)
gcloud iam service-accounts keys create ~/gcp-key.json \
  --iam-account=google-workspace-mcp@${PROJECT_ID}.iam.gserviceaccount.com

export GOOGLE_APPLICATION_CREDENTIALS=~/gcp-key.json
```

## Step 3: Configure OAuth 2.0

### Create OAuth 2.0 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **APIs & Services** > **Credentials**
3. Click **Create Credentials** > **OAuth 2.0 Client ID**
4. Select **Web application**
5. Add authorized redirect URIs:
   - `https://YOUR_CLOUD_RUN_URL/oauth2/callback`
   - `http://localhost:8080/oauth2/callback` (for local testing)
6. Download the credentials JSON

### Store Credentials

```bash
# Save OAuth credentials to Cloud Secret Manager
gcloud secrets create google-oauth-credentials \
  --data-file=path/to/credentials.json

# Grant service account access
gcloud secrets add-iam-policy-binding google-oauth-credentials \
  --member="serviceAccount:google-workspace-mcp@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Step 4: Build and Push Docker Image

### Option A: Using Cloud Build (Recommended)

```bash
# Build in Google Cloud
gcloud builds submit \
  --tag gcr.io/$PROJECT_ID/google-workspace-mcp:latest \
  --source backend/

# Or with specific region
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/$PROJECT_ID/cloud-run-repo/google-workspace-mcp:latest \
  --source backend/ \
  --region us-central1
```

### Option B: Build Locally and Push

```bash
# Build locally
cd backend/
docker build -t gcr.io/$PROJECT_ID/google-workspace-mcp:latest .

# Configure Docker authentication
gcloud auth configure-docker

# Push to Container Registry
docker push gcr.io/$PROJECT_ID/google-workspace-mcp:latest
```

## Step 5: Deploy to Cloud Run

```bash
# Deploy service
gcloud run deploy google-workspace-mcp-server \
  --image gcr.io/$PROJECT_ID/google-workspace-mcp:latest \
  --platform managed \
  --region us-central1 \
  --memory 1Gi \
  --cpu 1 \
  --concurrency 80 \
  --timeout 3600 \
  --no-allow-unauthenticated \
  --service-account google-workspace-mcp@${PROJECT_ID}.iam.gserviceaccount.com \
  --set-env-vars PORT=8080,OAUTH_ISSUER=https://accounts.google.com

# Get service URL
gcloud run services describe google-workspace-mcp-server \
  --region us-central1 \
  --format='value(status.url)'
```

## Step 6: Configure IAM Access

### Grant Users Access

```bash
# Grant specific user access
gcloud run services add-iam-policy-binding google-workspace-mcp-server \
  --region us-central1 \
  --member="user:email@example.com" \
  --role="roles/run.invoker"

# Or grant service account access
gcloud run services add-iam-policy-binding google-workspace-mcp-server \
  --region us-central1 \
  --member="serviceAccount:client-app@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

## Step 7: Configure Custom Domain (Optional)

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service google-workspace-mcp-server \
  --domain mcp.example.com \
  --region us-central1

# Verify DNS records (follow gcloud output instructions)
```

## Step 8: Set Up Monitoring and Logging

### View Logs

```bash
# Stream logs in real-time
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=google-workspace-mcp-server" \
  --limit 50 \
  --follow

# View specific error logs
gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" \
  --limit 20
```

### Create Monitoring Alert

```bash
# Create alert for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="MCP Server High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=300s
```

## Step 9: Configure Redis for Session Management (Optional)

### Create Memorystore Redis Instance

```bash
# Create Redis instance
gcloud redis instances create mcp-sessions \
  --size=1 \
  --region=us-central1 \
  --redis-version=7.0

# Get connection details
gcloud redis instances describe mcp-sessions \
  --region=us-central1 \
  --format='value(host,port)'

# Update Cloud Run environment variable
gcloud run services update google-workspace-mcp-server \
  --region us-central1 \
  --set-env-vars REDIS_URL=redis://REDIS_HOST:REDIS_PORT/0
```

## Step 10: Configure Firestore for Persistence (Optional)

```bash
# Create Firestore database
gcloud firestore databases create --region=us-central1

# Grant service account access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:google-workspace-mcp@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/datastore.user"
```

## Verification

### Health Check

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe google-workspace-mcp-server \
  --region us-central1 \
  --format='value(status.url)')

# Test health endpoint
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  $SERVICE_URL/health
```

### Test MCP Endpoint

```bash
# Initialize session
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "clientName": "Test Client",
      "clientVersion": "1.0.0"
    }
  }' \
  $SERVICE_URL/mcp
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs for errors
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Check service status
gcloud run services describe google-workspace-mcp-server --region us-central1
```

### Authentication Issues

```bash
# Verify service account has correct roles
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:google-workspace-mcp@*"

# Re-grant roles if needed
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:google-workspace-mcp@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### High Memory Usage

```bash
# Increase memory allocation
gcloud run services update google-workspace-mcp-server \
  --region us-central1 \
  --memory 2Gi
```

## Rollback

```bash
# List revisions
gcloud run revisions list --service google-workspace-mcp-server --region us-central1

# Route traffic to previous revision
gcloud run services update-traffic google-workspace-mcp-server \
  --region us-central1 \
  --to-revisions REVISION_NAME=100
```

## Cleanup

```bash
# Delete Cloud Run service
gcloud run services delete google-workspace-mcp-server --region us-central1

# Delete service account
gcloud iam service-accounts delete google-workspace-mcp@${PROJECT_ID}.iam.gserviceaccount.com

# Delete secrets
gcloud secrets delete google-oauth-credentials

# Delete Redis instance (if created)
gcloud redis instances delete mcp-sessions --region us-central1
```

## Cost Optimization

1. **Set Min Instances to 0** for development (default)
2. **Use Cloud Run's automatic scaling** - pay only for used resources
3. **Monitor with Cloud Monitoring** to identify optimization opportunities
4. **Use Cloud CDN** for caching if applicable
5. **Consider committed use discounts** for production workloads

## Security Best Practices

1. ✅ Use Identity-Aware Proxy (no-allow-unauthenticated)
2. ✅ Store secrets in Cloud Secret Manager
3. ✅ Enable Cloud Audit Logs
4. ✅ Use VPC Service Controls for additional isolation
5. ✅ Regularly rotate OAuth credentials
6. ✅ Enable Binary Authorization for container image verification
7. ✅ Use private Cloud Run services with Cloud Load Balancer

## References

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Security Best Practices](https://cloud.google.com/run/docs/securing/securing-services)
- [gcloud run command reference](https://cloud.google.com/sdk/gcloud/reference/run)
