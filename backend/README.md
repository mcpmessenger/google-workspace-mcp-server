# Google Workspace MCP Server

A production-ready Model Context Protocol (MCP) server implementing the Streamable HTTP transport standard for Google Workspace integrations. Designed for deployment on Google Cloud Run with multi-user OAuth 2.1 authentication and distributed session management.

## Architecture Overview

### Streamable HTTP Transport

This server implements the MCP Streamable HTTP specification (March 2025), which provides:

- **Unified HTTP Endpoint**: Single `/mcp` endpoint supporting GET, POST, and DELETE methods
- **Session Management**: Cryptographically secure session IDs via `Mcp-Session-Id` headers
- **Bidirectional Communication**: Server-Sent Events (SSE) for long-running operations
- **DNS Rebinding Protection**: Origin header validation for security
- **Automatic Token Refresh**: Transparent OAuth token management

### Core Components

1. **Session Manager**: Handles session lifecycle, timeout, and state persistence
2. **Google Workspace Tools**: Integrations for Drive, Gmail, Calendar, Docs, Sheets, Slides, Tasks, Forms
3. **OAuth 2.1 Flow**: Multi-user authentication with token storage
4. **CORS Proxy**: Secure authentication handshakes for browser-based clients

## Features

### Google Workspace Integrations

#### Google Drive
- `search_drive_files`: Semantic/keyword search with Drive query syntax
- `get_drive_file_content`: Download or export to PDF/Office formats
- `create_drive_file`: Upload files or create directories
- `update_drive_file`: Modify metadata or move between folders
- `list_drive_items`: Enumerate folder contents

#### Gmail
- `search_gmail_messages`: Gmail search operators support
- `get_gmail_message_content`: Full headers and body retrieval
- `send_gmail_message`: Compose with threading support
- `modify_gmail_labels`: Add/remove labels from messages
- `get_thread_content_batch`: Batch message retrieval

#### Google Calendar
- `list_calendars`: Access all available calendars
- `get_events`: Retrieve meetings in time intervals
- `create_event`: Schedule with attendees and reminders
- `query_free_busy`: Check availability status
- `quick_add_event`: Natural language event creation

#### Additional Services
- **Google Docs**: Text modification, find/replace, table insertion, PDF export
- **Google Sheets**: Cell-level control, range manipulation, data analysis
- **Google Slides**: Presentation creation, slide management, image insertion
- **Google Tasks**: Task management with hierarchy
- **Google Forms**: Form creation and response collection

### Security Features

- **OAuth 2.1 Authentication**: Modern security with token refresh
- **DNS Rebinding Protection**: Origin header validation
- **Session Isolation**: Per-session OAuth token storage
- **CORS Proxy**: Secure browser-based authentication
- **Cloud Run IAM**: Identity-Aware Proxy integration

## Deployment

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export PORT=8080
export HOST=0.0.0.0

# Run server
python main.py
```

### Google Cloud Run

#### Prerequisites
- Google Cloud Project with billing enabled
- `gcloud` CLI installed and authenticated
- Docker installed locally

#### Deployment Steps

```bash
# Build and push Docker image
gcloud builds submit --tag gcr.io/PROJECT_ID/google-workspace-mcp:latest

# Deploy to Cloud Run
gcloud run deploy google-workspace-mcp-server \
  --image gcr.io/PROJECT_ID/google-workspace-mcp:latest \
  --platform managed \
  --region us-central1 \
  --memory 1Gi \
  --cpu 1 \
  --concurrency 80 \
  --no-allow-unauthenticated \
  --set-env-vars PORT=8080,OAUTH_ISSUER=https://accounts.google.com

# Create service account
gcloud iam service-accounts create google-workspace-mcp

# Grant Cloud Run invoker role
gcloud run services add-iam-policy-binding google-workspace-mcp-server \
  --member=serviceAccount:google-workspace-mcp@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/run.invoker
```

### Configuration Parameters

| Parameter | Recommended | Reasoning |
|-----------|-------------|-----------|
| Memory | 512MB - 1GB | Multiple concurrent JSON-RPC sessions |
| Concurrency | 80-100 | Asynchronous FastMCP engine |
| Response Streaming | Enabled | Essential for SSE streams |
| Min Instances | 1 (optional) | Prevents cold starts |
| Ingress | Internal + LB | Corporate VPN/gateway access |

## API Endpoints

### Health Check
```
GET /health
```
Returns server status and active session count.

### OAuth Discovery
```
GET /.well-known/oauth-authorization-server
```
OAuth 2.1 authorization server discovery endpoint.

### MCP Streamable HTTP

#### Initialize Session
```
POST /mcp
Headers:
  Content-Type: application/json

Body:
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "clientName": "VS Code Extension",
    "clientVersion": "1.0.0"
  }
}

Response:
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-03",
    "capabilities": {...},
    "serverInfo": {...}
  }
}
Headers:
  Mcp-Session-Id: <session_id>
```

#### Tool Call
```
POST /mcp
Headers:
  Mcp-Session-Id: <session_id>
  Content-Type: application/json

Body:
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search_drive_files",
    "arguments": {
      "query": "project proposal",
      "pageSize": 10
    }
  }
}
```

#### Server-Sent Events Stream
```
GET /mcp
Headers:
  Mcp-Session-Id: <session_id>
  Accept: text/event-stream
  Last-Event-ID: <last_event_id> (optional for resumption)

Response: text/event-stream
```

#### Terminate Session
```
DELETE /mcp
Headers:
  Mcp-Session-Id: <session_id>
```

## Session Lifecycle

1. **Initialization**: Client sends `initialize` method, server responds with `Mcp-Session-Id`
2. **Tool Calls**: Client includes session ID in subsequent requests
3. **SSE Stream**: Client opens persistent GET connection for server-initiated events
4. **Termination**: Client sends DELETE or server timeout expires (24 hours default)

## Distributed State Management

For multi-instance deployments, use external persistence:

### Redis (Session Caching)
```python
# Sub-millisecond latency for session metadata
REDIS_URL=redis://memorystore-instance:6379/0
```

### Firestore (Long-term Persistence)
```python
# Serverless NoSQL for user preferences and agent memory
GCP_PROJECT_ID=your-project-id
```

## Observability

### Logging
- JSON-RPC message envelopes (with PII redaction)
- Session lifecycle events
- API performance metrics
- Error trajectories

### Monitoring
```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Monitor metrics
gcloud monitoring metrics-descriptors list --filter="metric.type:run.googleapis.com"
```

### MCP Inspector
```bash
# Connect to running server for debugging
mcp dev http://localhost:8080/mcp
```

## Protocol Versioning

- **Current Version**: 2025-03
- **Header**: `Mcp-Protocol-Version`
- **Fallback**: Automatic detection of legacy SSE support

## Error Handling

### HTTP Status Codes
- `200 OK`: Successful tool call or response
- `202 Accepted`: Long-running operation initiated
- `400 Bad Request`: Missing required headers or invalid request
- `403 Forbidden`: Origin not allowed (DNS rebinding protection)
- `404 Not Found`: Session expired or not found
- `500 Internal Server Error`: Tool execution failure

### JSON-RPC Error Responses
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": {
      "details": "..."
    }
  }
}
```

## Development

### Project Structure
```
backend/
├── main.py                 # FastAPI application
├── pyproject.toml         # Dependencies
├── Dockerfile             # Cloud Run container
├── clouddeploy.yaml       # GCP deployment config
├── .env.example           # Environment template
└── README.md              # This file
```

### Adding New Tools

1. Add method to `GoogleWorkspaceTools` class
2. Register in `mcp_post` tool routing
3. Define JSON Schema in capabilities
4. Test with MCP Inspector

### Testing

```bash
# Unit tests
pytest tests/

# Integration tests
pytest tests/integration/

# Load testing
locust -f tests/load/locustfile.py
```

## Security Considerations

1. **Always use HTTPS** in production
2. **Enable Identity-Aware Proxy** on Cloud Run
3. **Rotate OAuth tokens** regularly
4. **Validate Origin headers** for DNS rebinding protection
5. **Implement rate limiting** per session
6. **Audit all API calls** to Google Workspace

## Troubleshooting

### Session Not Found
- Session may have expired (24-hour timeout)
- Client must include `Mcp-Session-Id` header
- Server may have been restarted

### OAuth Token Errors
- Refresh token may be invalid
- User may have revoked permissions
- Token may have expired without refresh

### SSE Stream Disconnection
- Use `Last-Event-ID` header to resume
- Server will replay missed events
- Check firewall/proxy for stream timeout

## References

- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Streamable HTTP Transport](https://spec.modelcontextprotocol.io/docs/concepts/transports/http)
- [Google Workspace APIs](https://developers.google.com/workspace/apis)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [OAuth 2.1 Specification](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1)

## License

MIT License - See LICENSE file for details

## Support

For issues, feature requests, or contributions, please open an issue on the project repository.
