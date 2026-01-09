"""
Google Workspace Model Context Protocol Server
Implements Streamable HTTP transport for cloud deployment on Google Cloud Run
"""

import os
import json
import logging
import asyncio
from typing import Optional, Any, List, Dict
from datetime import datetime, timedelta
import uuid
import secrets
import psutil

# Track server start time for uptime calculation
SERVER_START_TIME = datetime.utcnow()

# Required for Google OAuth when scopes are automatically expanded by Google
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from pydantic import BaseModel
from dotenv import load_dotenv

# Google OAuth and API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleAuthRequest
import httpx

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
    
    def store_oauth_tokens(self, session_id: str, tokens: dict) -> bool:
        """Store OAuth tokens for a session"""
        session = self.get_session(session_id)
        if session:
            session.oauth_tokens = tokens
            session.last_activity = datetime.utcnow()
            logger.info(f"OAuth tokens stored for session: {session_id}")
            return True
        return False
    
    def get_oauth_tokens(self, session_id: str) -> Optional[dict]:
        """Retrieve OAuth tokens for a session"""
        session = self.get_session(session_id)
        return session.oauth_tokens if session else None
    
    def refresh_oauth_token(self, session_id: str) -> Optional[dict]:
        """Refresh OAuth access token using refresh token"""
        session = self.get_session(session_id)
        if not session or not session.oauth_tokens.get('refresh_token'):
            return None
        
        try:
            creds = Credentials(
                token=session.oauth_tokens.get('access_token'),
                refresh_token=session.oauth_tokens['refresh_token'],
                token_uri=os.getenv('OAUTH_TOKEN_ENDPOINT'),
                client_id=os.getenv('GOOGLE_CLIENT_ID'),
                client_secret=os.getenv('GOOGLE_CLIENT_SECRET')
            )
            
            if creds.expired and creds.refresh_token:
                creds.refresh(GoogleAuthRequest())
                
                # Update stored tokens
                new_tokens = {
                    'access_token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_expiry': creds.expiry.isoformat() if creds.expiry else None
                }
                self.store_oauth_tokens(session_id, new_tokens)
                logger.info(f"OAuth token refreshed for session: {session_id}")
                return new_tokens
        except Exception as e:
            logger.error(f"Failed to refresh OAuth token: {e}")
            return None


# ============================================================================
# Google Workspace Tools
# ============================================================================

class GoogleWorkspaceTools:
    """Google Workspace API integration tools"""
    
    @staticmethod
    def get_service(session_id: str, service_name: str, version: str):
        """Get an authenticated Google API service"""
        tokens = session_manager.get_oauth_tokens(session_id)
        if not tokens or not tokens.get('access_token'):
            return None
            
        creds = Credentials(
            token=tokens.get('access_token'),
            refresh_token=tokens.get('refresh_token'),
            token_uri=os.getenv('OAUTH_TOKEN_ENDPOINT'),
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
            scopes=tokens.get('scopes')
        )
        
        # Check if expired and refresh if possible
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleAuthRequest())
                # Update stored tokens
                session_manager.store_oauth_tokens(session_id, {
                    'access_token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_expiry': creds.expiry.isoformat() if creds.expiry else None,
                    'scopes': creds.scopes
                })
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                return None
                
        return build(service_name, version, credentials=creds)

    async def search_drive_files(self, session_id: str, query: str, mime_type: Optional[str] = None, page_size: int = 10) -> dict:
        """Search Google Drive files"""
        service = self.get_service(session_id, 'drive', 'v3')
        if not service:
            return {"error": "Authentication required", "auth_url": f"{os.getenv('OAUTH_REDIRECT_URI').replace('/callback', '/authorize')}?session_id={session_id}"}
        
        q = query
        if mime_type:
            q = f"{q} and mimeType = '{mime_type}'"
            
        results = service.files().list(
            q=q, pageSize=page_size, fields="nextPageToken, files(id, name, mimeType, modifiedTime)"
        ).execute()
        return results
    
    async def get_drive_file_content(self, session_id: str, file_id: str, export_format: Optional[str] = None) -> dict:
        """Get Google Drive file content"""
        service = self.get_service(session_id, 'drive', 'v3')
        if not service:
            return {"error": "Authentication required"}
            
        file = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        
        if 'application/vnd.google-apps' in file['mimeType']:
            # Export Google Docs/Sheets/Slides
            export_mime = export_format or 'application/pdf'
            content = service.files().export(fileId=file_id, mimeType=export_mime).execute()
            # Return metadata; actual content usually streamed or saved
            return {"file_id": file_id, "name": file['name'], "status": "Ready for export", "mimeType": export_mime}
        else:
            # Download regular files
            return {"file_id": file_id, "name": file['name'], "status": "Ready for download", "mimeType": file['mimeType']}
    
    async def search_gmail_messages(self, session_id: str, query: str, max_results: int = 10) -> dict:
        """Search Gmail messages"""
        service = self.get_service(session_id, 'gmail', 'v1')
        if not service:
            return {"error": "Authentication required"}
            
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = []
        if 'messages' in results:
            for msg in results['messages']:
                m = service.users().messages().get(userId='me', id=msg['id'], format='minimal').execute()
                messages.append(m)
        return {"messages": messages, "query": query}

    async def gmail_create_draft(self, session_id: str, to: str, subject: str, body: str) -> dict:
        """Create a Gmail draft"""
        service = self.get_service(session_id, 'gmail', 'v1')
        if not service:
            return {"error": "Authentication required"}
            
        import base64
        from email.message import EmailMessage
        
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to
        message['From'] = 'me'
        message['Subject'] = subject
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'message': {'raw': encoded_message}}
        
        draft = service.users().drafts().create(userId='me', body=create_message).execute()
        return {"draft_id": draft['id'], "status": "Draft created successfully"}
    
    async def list_calendars(self, session_id: str, min_access_role: str = "reader") -> dict:
        """List available calendars"""
        service = self.get_service(session_id, 'calendar', 'v3')
        if not service:
            return {"error": "Authentication required"}
            
        results = service.calendarList().list(minAccessRole=min_access_role).execute()
        return results
    
    async def get_events(self, session_id: str, calendar_id: str, time_min: str, time_max: str) -> dict:
        """Get calendar events"""
        service = self.get_service(session_id, 'calendar', 'v3')
        if not service:
            return {"error": "Authentication required"}
            
        results = service.events().list(
            calendarId=calendar_id, 
            timeMin=time_min, 
            timeMax=time_max, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return results


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
    allow_origins=["*"],  # Open for development/testing
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with real metrics"""
    uptime = datetime.utcnow() - SERVER_START_TIME
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": str(uptime).split('.')[0],  # Format as H:MM:SS
        "sessions_active": len(session_manager.sessions),
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": round(psutil.Process().memory_info().rss / (1024 * 1024), 2)
        }
    }


# ============================================================================
# OAuth Endpoints
# ============================================================================

@app.get("/oauth/authorize")
async def oauth_authorize(session_id: str = None):
    """Initiate OAuth flow"""
    try:
        if not session_id:
            session_id = session_manager.create_session()
        
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        redirect_uri = os.getenv('OAUTH_REDIRECT_URI')
        scopes = [s.strip() for s in os.getenv('OAUTH_SCOPES', '').split(',') if s.strip()]
        
        logger.info(f"Initiating OAuth: client_id={client_id}, redirect_uri={redirect_uri}, scopes={scopes}")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                    "auth_uri": os.getenv('OAUTH_AUTH_ENDPOINT'),
                    "token_uri": os.getenv('OAUTH_TOKEN_ENDPOINT'),
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=scopes
        )
        flow.redirect_uri = redirect_uri
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        logger.info(f"Generated authorization_url: {authorization_url}")
        session_manager.update_session(session_id, oauth_state=state)
        return RedirectResponse(url=authorization_url)
        
    except Exception as e:
        logger.error(f"OAuth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/oauth/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None, session_id: str = None):
    """Handle OAuth callback"""
    try:
        if error:
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        redirect_uri = os.getenv('OAUTH_REDIRECT_URI')
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": os.getenv('OAUTH_AUTH_ENDPOINT'),
                    "token_uri": os.getenv('OAUTH_TOKEN_ENDPOINT'),
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=os.getenv('OAUTH_SCOPES', '').split(','),
            state=state
        )
        flow.redirect_uri = redirect_uri
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        tokens = {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_expiry': credentials.expiry.isoformat() if credentials.expiry else None,
            'scopes': credentials.scopes
        }
        
        if not session_id:
            session_id = session_manager.create_session()
        
        session_manager.store_oauth_tokens(session_id, tokens)
        
        return {
            "status": "success",
            "message": "Authentication successful. You can now use the tools.",
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MCP Streamable HTTP Endpoints
# ============================================================================

@app.post("/mcp")
async def mcp_post(
    request: Request,
    mcp_session_id: Optional[str] = Header(None),
    mcp_protocol_version: Optional[str] = Header("2025-03")
):
    """POST endpoint for MCP Streamable HTTP"""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    method = body.get("method")
    
    if method == "initialize":
        session_id = session_manager.create_session(
            client_name=body.get("params", {}).get("clientInfo", {}).get("name")
        )
        session_manager.update_session(session_id, initialized=True)
        
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "protocolVersion": "2025-03",
                "capabilities": {
                    "tools": {
                        "list_calendars": {},
                        "get_events": {},
                        "search_drive_files": {},
                        "get_drive_file_content": {},
                        "search_gmail_messages": {},
                        "gmail_create_draft": {}
                    },
                    "resources": {},
                    "prompts": {}
                },
                "serverInfo": {
                    "name": "Google Workspace MCP Server",
                    "version": "0.1.0"
                }
            }
        }, headers={"Mcp-Session-Id": session_id})
    
    if not mcp_session_id:
        raise HTTPException(status_code=400, detail="Mcp-Session-Id header required")
    
    session = session_manager.get_session(mcp_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if method == "tools/call":
        tool_name = body.get("params", {}).get("name")
        arguments = body.get("params", {}).get("arguments", {})
        
        # Add session_id to arguments for auth
        arguments["session_id"] = mcp_session_id
        
        try:
            if hasattr(workspace_tools, tool_name):
                tool_func = getattr(workspace_tools, tool_name)
                result = await tool_func(**arguments)
                
                # Check for auth required
                if isinstance(result, dict) and result.get("error") == "Authentication required":
                    redirect_uri = os.getenv('OAUTH_REDIRECT_URI', '')
                    auth_url = result.get('auth_url', f"{redirect_uri.replace('/callback', '/authorize')}?session_id={mcp_session_id}")
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "content": [
                                {
                                    "type": "text", 
                                    "text": f"⚠️ Authentication Required. Please visit this link to authorize: {auth_url}"
                                }
                            ],
                            "isError": True
                        }
                    })

                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                        "isError": False
                    }
                })
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error(f"Tool call error: {e}")
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {"code": -32603, "message": str(e)}
            }, status_code=500)
    
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
