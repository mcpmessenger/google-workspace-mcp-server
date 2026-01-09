"""
Google Workspace Model Context Protocol Server
Implements Streamable HTTP transport for cloud deployment on Google Cloud Run
"""

import os
import json
import logging
import asyncio
from typing import Optional, Any
from datetime import datetime, timedelta
import uuid
import secrets

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from pydantic import BaseModel
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ============================================================================
# Data Models
# ============================================================================

class InitializeRequest(BaseModel):
    """MCP Initialize request"""
    jsonrpc: str = "2.0"
    id: int
    method: str
    params: dict


class ToolCall(BaseModel):
    """Tool call request"""
    name: str
    arguments: dict


class SessionState(BaseModel):
    """Session state for Streamable HTTP"""
    session_id: str
    client_name: Optional[str] = None
    protocol_version: str = "2025-03"
    initialized: bool = False
    created_at: datetime = None
    last_activity: datetime = None
    oauth_tokens: dict = {}
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.last_activity is None:
            self.last_activity = datetime.utcnow()


# ============================================================================
# Session Management
# ============================================================================

class SessionManager:
    """Manages MCP sessions with Streamable HTTP"""
    
    def __init__(self):
        self.sessions: dict[str, SessionState] = {}
        self.session_timeout = timedelta(hours=24)
    
    def create_session(self, client_name: Optional[str] = None) -> str:
        """Create a new session with cryptographically secure ID"""
        session_id = secrets.token_urlsafe(32)
        session = SessionState(
            session_id=session_id,
            client_name=client_name,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        self.sessions[session_id] = session
        logger.info(f"Session created: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve session by ID"""
        session = self.sessions.get(session_id)
        if session:
            # Check if session has expired
            if datetime.utcnow() - session.last_activity > self.session_timeout:
                del self.sessions[session_id]
                logger.info(f"Session expired: {session_id}")
                return None
            session.last_activity = datetime.utcnow()
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session deleted: {session_id}")
            return True
        return False
    
    def update_session(self, session_id: str, **kwargs) -> Optional[SessionState]:
        """Update session state"""
        session = self.get_session(session_id)
        if session:
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
        return session


# ============================================================================
# Google Workspace Tools
# ============================================================================

class GoogleWorkspaceTools:
    """Google Workspace API integration tools"""
    
    @staticmethod
    async def search_drive_files(query: str, mime_type: Optional[str] = None, page_size: int = 10) -> dict:
        """Search Google Drive files"""
        # Placeholder - implement with google-api-python-client
        return {
            "files": [
                {
                    "id": "file_123",
                    "name": "Example Document",
                    "mimeType": "application/vnd.google-apps.document",
                    "modifiedTime": datetime.utcnow().isoformat()
                }
            ],
            "query": query,
            "mimeType": mime_type
        }
    
    @staticmethod
    async def get_drive_file_content(file_id: str, export_format: Optional[str] = None) -> dict:
        """Get Google Drive file content"""
        return {
            "file_id": file_id,
            "content": "File content would be retrieved here",
            "format": export_format or "pdf"
        }
    
    @staticmethod
    async def search_gmail_messages(query: str, max_results: int = 10) -> dict:
        """Search Gmail messages"""
        return {
            "messages": [
                {
                    "id": "msg_123",
                    "threadId": "thread_123",
                    "snippet": "Email snippet...",
                    "internalDate": str(int(datetime.utcnow().timestamp() * 1000))
                }
            ],
            "query": query,
            "resultSizeEstimate": 1
        }
    
    @staticmethod
    async def list_calendars(min_access_role: str = "reader") -> dict:
        """List available calendars"""
        return {
            "calendars": [
                {
                    "id": "primary",
                    "summary": "Primary Calendar",
                    "timeZone": "UTC",
                    "accessRole": "owner"
                }
            ],
            "minAccessRole": min_access_role
        }
    
    @staticmethod
    async def get_events(calendar_id: str, time_min: str, time_max: str) -> dict:
        """Get calendar events"""
        return {
            "calendarId": calendar_id,
            "events": [
                {
                    "id": "event_123",
                    "summary": "Meeting",
                    "start": {"dateTime": time_min},
                    "end": {"dateTime": time_max}
                }
            ],
            "timeMin": time_min,
            "timeMax": time_max
        }


# ============================================================================
# FastAPI Application
# ============================================================================

session_manager = SessionManager()
workspace_tools = GoogleWorkspaceTools()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Google Workspace MCP Server starting...")
    yield
    logger.info("Google Workspace MCP Server shutting down...")


app = FastAPI(
    title="Google Workspace MCP Server",
    description="Model Context Protocol Server with Streamable HTTP Transport",
    version="0.1.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["localhost", "127.0.0.1"],  # Restrict for security
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "sessions_active": len(session_manager.sessions)
    }


# ============================================================================
# OAuth Discovery Endpoints
# ============================================================================

@app.get("/.well-known/oauth-authorization-server")
async def oauth_discovery():
    """OAuth 2.1 Authorization Server Discovery"""
    return {
        "issuer": os.getenv("OAUTH_ISSUER", "https://accounts.google.com"),
        "authorization_endpoint": os.getenv("OAUTH_AUTH_ENDPOINT", "https://accounts.google.com/o/oauth2/v2/auth"),
        "token_endpoint": os.getenv("OAUTH_TOKEN_ENDPOINT", "https://oauth2.googleapis.com/token"),
        "revocation_endpoint": "https://oauth2.googleapis.com/revoke",
        "scopes_supported": [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar.readonly"
        ]
    }


# ============================================================================
# CORS Proxy for OAuth
# ============================================================================

@app.get("/auth/discovery/authorization-server/{server}")
async def oauth_proxy_discovery(server: str):
    """CORS proxy for OAuth discovery"""
    return await oauth_discovery()


@app.post("/oauth2/token")
async def oauth_proxy_token(request: Request):
    """CORS proxy for token exchange"""
    body = await request.json()
    # Placeholder - implement actual token exchange
    return {
        "access_token": "token_" + secrets.token_urlsafe(32),
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "refresh_" + secrets.token_urlsafe(32)
    }


# ============================================================================
# MCP Streamable HTTP Endpoints
# ============================================================================

@app.post("/mcp")
async def mcp_post(
    request: Request,
    mcp_session_id: Optional[str] = Header(None),
    mcp_protocol_version: Optional[str] = Header("2025-03")
):
    """
    POST endpoint for MCP Streamable HTTP
    Handles initialization, tool calls, and request-response patterns
    """
    # Validate Origin header for DNS rebinding protection
    origin = request.headers.get("origin")
    if origin and origin not in ["http://localhost:3000", "http://127.0.0.1:3000"]:
        raise HTTPException(status_code=403, detail="Origin not allowed")
    
    body = await request.json()
    method = body.get("method")
    
    # Handle initialization
    if method == "initialize":
        session_id = session_manager.create_session(
            client_name=body.get("params", {}).get("clientName")
        )
        session = session_manager.update_session(session_id, initialized=True)
        
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "protocolVersion": "2025-03",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {}
                },
                "serverInfo": {
                    "name": "Google Workspace MCP Server",
                    "version": "0.1.0"
                }
            }
        }, headers={"Mcp-Session-Id": session_id})
    
    # Validate session for subsequent requests
    if not mcp_session_id:
        raise HTTPException(status_code=400, detail="Mcp-Session-Id header required")
    
    session = session_manager.get_session(mcp_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Handle tool calls
    if method == "tools/call":
        tool_name = body.get("params", {}).get("name")
        arguments = body.get("params", {}).get("arguments", {})
        
        try:
            # Route to appropriate tool
            if tool_name == "search_drive_files":
                result = await workspace_tools.search_drive_files(**arguments)
            elif tool_name == "search_gmail_messages":
                result = await workspace_tools.search_gmail_messages(**arguments)
            elif tool_name == "list_calendars":
                result = await workspace_tools.list_calendars(**arguments)
            elif tool_name == "get_events":
                result = await workspace_tools.get_events(**arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}],
                    "isError": False
                }
            })
        except Exception as e:
            logger.error(f"Tool call error: {e}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {"code": -32603, "message": str(e)}
            }, status_code=500)
    
    # Handle other methods
    return JSONResponse({
        "jsonrpc": "2.0",
        "id": body.get("id"),
        "error": {"code": -32601, "message": "Method not found"}
    }, status_code=400)


@app.get("/mcp")
async def mcp_get(
    request: Request,
    mcp_session_id: Optional[str] = Header(None),
    last_event_id: Optional[str] = Header(None)
):
    """
    GET endpoint for MCP Streamable HTTP
    Handles Server-Sent Events for long-running operations and announcements
    """
    # Validate session
    if not mcp_session_id:
        raise HTTPException(status_code=400, detail="Mcp-Session-Id header required")
    
    session = session_manager.get_session(mcp_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    async def event_generator():
        """Generate SSE events"""
        event_id = 0
        try:
            while True:
                # Send heartbeat
                yield f"id: {event_id}\n"
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                event_id += 1
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
        except asyncio.CancelledError:
            logger.info(f"SSE stream closed for session {mcp_session_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.delete("/mcp")
async def mcp_delete(
    mcp_session_id: Optional[str] = Header(None)
):
    """
    DELETE endpoint for MCP Streamable HTTP
    Terminates a session and cleans up resources
    """
    if not mcp_session_id:
        raise HTTPException(status_code=400, detail="Mcp-Session-Id header required")
    
    if session_manager.delete_session(mcp_session_id):
        return JSONResponse({"status": "Session terminated"})
    else:
        raise HTTPException(status_code=404, detail="Session not found")


# ============================================================================
# Startup
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
