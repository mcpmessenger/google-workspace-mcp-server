# Backend-Only OAuth Testing Guide

## Prerequisites
- Backend running (locally or on Cloud Run)
- OAuth credentials configured in `.env`

## Step 1: Start Backend

### Local:
```bash
cd backend
python main.py
```

### Or deploy to Cloud Run:
```bash
gcloud run deploy mcp-server --source ./backend --region us-central1
```

## Step 2: Get Your Server URL

### Local:
```
http://localhost:8081
```

### Cloud Run:
```bash
gcloud run services describe mcp-server --region us-central1 --format='value(status.url)'
```

### ngrok (for local HTTPS):
```bash
ngrok http 8081
# Copy the https:// URL
```

## Step 3: Update OAuth Redirect URI

In Google Cloud Console, add:
```
YOUR_SERVER_URL/oauth/callback
```

And in `.env`:
```env
OAUTH_REDIRECT_URI=YOUR_SERVER_URL/oauth/callback
```

## Step 4: Test OAuth Flow (Browser Required)

1. **Open in browser:**
   ```
   YOUR_SERVER_URL/oauth/authorize
   ```

2. **Sign in to Google and approve**

3. **Copy the session ID from the response:**
   ```json
   {
     "status": "success",
     "message": "Authentication successful",
     "session_id": "abc123xyz..."
   }
   ```

## Step 5: Test MCP Endpoints with curl

### Health Check
```bash
curl YOUR_SERVER_URL/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-09T07:00:00",
  "sessions_active": 1
}
```

### Initialize MCP Session
```bash
curl -X POST YOUR_SERVER_URL/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: YOUR_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    }
  }'
```

### List Available Tools
```bash
curl -X POST YOUR_SERVER_URL/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: YOUR_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
  }'
```

### Call a Tool (Search Drive)
```bash
curl -X POST YOUR_SERVER_URL/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: YOUR_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "search_drive_files",
      "arguments": {
        "query": "test",
        "max_results": 10
      }
    }
  }'
```

## Step 6: Test Token Refresh

Tokens expire after 1 hour. The server automatically refreshes them, but you can test manually:

```bash
# Wait for token to expire (or force it in code)
# Then make another API call - it should auto-refresh

curl -X POST YOUR_SERVER_URL/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: YOUR_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/list"
  }'
```

Check logs for:
```
OAuth token refreshed for session: YOUR_SESSION_ID
```

## Troubleshooting

### "OAuth not configured" Error
- Check `.env` file has `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
- Restart backend after updating `.env`

### "redirect_uri_mismatch" Error
- Redirect URI in Google Cloud Console must exactly match `OAUTH_REDIRECT_URI` in `.env`
- Include the full path: `https://your-url.com/oauth/callback`

### "Session not found" Error
- Session expired (24 hours)
- Re-run OAuth flow to get new session ID

### "Invalid credentials" Error
- OAuth tokens expired and refresh failed
- Re-run OAuth flow

## Production Deployment (Backend Only)

### 1. Deploy to Cloud Run
```bash
gcloud run deploy mcp-server \
  --source ./backend \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_CLIENT_ID=your-id,GOOGLE_CLIENT_SECRET=your-secret"
```

### 2. Get URL
```bash
gcloud run services describe mcp-server \
  --region us-central1 \
  --format='value(status.url)'
```

### 3. Update OAuth Redirect
Add to Google Cloud Console:
```
https://mcp-server-xyz.run.app/oauth/callback
```

### 4. Test
```bash
# Open in browser for OAuth
https://mcp-server-xyz.run.app/oauth/authorize

# Then use curl with session ID
curl -X POST https://mcp-server-xyz.run.app/mcp \
  -H "X-Session-ID: your-session" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## No Frontend Needed!

The frontend is just a dashboard for monitoring. All OAuth and MCP functionality works perfectly with just the backend + browser for OAuth consent.
