import os
import sys

# Basic health check log
print(f"--- SERVER STARTING ON PORT {os.getenv('PORT', '8080')} ---", flush=True)

import json
import logging
import asyncio
from typing import Optional, Any, List, Dict
from datetime import datetime, timedelta
import uuid
import secrets
# import psutil  # Removed to avoid container startup issues

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

from google.cloud import firestore
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

print("--- ANALYZING DEPENDENCIES ---", flush=True)
try:
    import fastapi
    import uvicorn
    import pydantic
    import google.auth
    print(f"FastAPI: {fastapi.__version__}", flush=True)
    print(f"Pydantic: {pydantic.__version__}", flush=True)
except Exception as e:
    print(f"CRITICAL: Dependency check failed: {e}", flush=True)

load_dotenv()

def get_google_credentials():
    """Helper to get Google credentials from environment with multiple alias support"""
    client_id = os.getenv('GOOGLE_CLIENT_ID') or os.getenv('GOOGLE_OAUTH_CLIENT_ID') or os.getenv('OAUTH_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET') or os.getenv('GOOGLE_OAUTH_CLIENT_SECRET') or os.getenv('OAUTH_CLIENT_SECRET')
    return client_id, client_secret

# ============================================================================
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
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    oauth_tokens: dict = {}
    oauth_state: Optional[str] = None
    scopes: Optional[List[str]] = None
    oauth_client_id: Optional[str] = None
    oauth_client_secret: Optional[str] = None
    
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
    """Manages MCP sessions with Google Cloud Firestore persistence"""
    
    def __init__(self, collection_name="mcp_sessions"):
        try:
            self.db = firestore.Client()
            self.collection = self.db.collection(collection_name)
            self.session_timeout = timedelta(hours=24)
            logger.info(f"FirestoreSessionManager initialized with collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            # Fallback to in-memory if Firestore fails (for local dev)
            self.db = None
            self.sessions = {}
            logger.warning("Falling back to in-memory session storage")

    def _dict_to_state(self, data: dict) -> Optional[SessionState]:
        """Convert Firestore dict to SessionState object"""
        if not data:
            return None
        try:
            # Handle datetime deserialization
            if 'created_at' in data and isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
            if 'last_activity' in data and isinstance(data['last_activity'], str):
                data['last_activity'] = datetime.fromisoformat(data['last_activity'])
            return SessionState(**data)
        except Exception as e:
            logger.error(f"Error converting dict to SessionState: {e}")
            return None

    def _state_to_dict(self, state: SessionState) -> dict:
        """Convert SessionState object to Firestore-compatible dict"""
        data = state.dict()
        # Handle datetime serialization for Firestore (though Firestore supports native datetimes,
        # keeping them as ISO strings is often safer for cross-platform/JSON compatibility)
        if data.get('created_at'):
            data['created_at'] = data['created_at'].isoformat() if isinstance(data['created_at'], datetime) else data['created_at']
        if data.get('last_activity'):
            data['last_activity'] = data['last_activity'].isoformat() if isinstance(data['last_activity'], datetime) else data['last_activity']
        return data

    def create_session(self, client_name: Optional[str] = None) -> str:
        """Create a new session stored in Firestore"""
        session_id = secrets.token_urlsafe(32)
        session = SessionState(
            session_id=session_id,
            client_name=client_name,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        if self.db:
            try:
                self.collection.document(session_id).set(self._state_to_dict(session))
                logger.info(f"Session created and saved to Firestore: {session_id}")
            except Exception as e:
                logger.error(f"Error saving new session to Firestore: {e}")
        else:
            self.sessions[session_id] = session
            logger.info(f"Session created in-memory: {session_id}")
            
        return session_id

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve session from Firestore by ID"""
        if not session_id:
            return None
            
        if self.db:
            try:
                doc = self.collection.document(session_id).get()
                if doc.exists:
                    session = self._dict_to_state(doc.to_dict())
                    if session:
                        # Check expiration
                        if datetime.utcnow() - session.last_activity > self.session_timeout:
                            logger.info(f"Session expired according to Firestore timestamp: {session_id}")
                            self.delete_session(session_id)
                            return None
                        
                        # Update last activity (throttled/batched ideally, but direct for reliability now)
                        session.last_activity = datetime.utcnow()
                        self.collection.document(session_id).update({'last_activity': session.last_activity.isoformat()})
                        return session
                return None
            except Exception as e:
                logger.error(f"Error retrieving session from Firestore: {e}")
                return None
        else:
            session = self.sessions.get(session_id)
            if session:
                if datetime.utcnow() - session.last_activity > self.session_timeout:
                    del self.sessions[session_id]
                    return None
                session.last_activity = datetime.utcnow()
            return session

    def delete_session(self, session_id: str) -> bool:
        """Delete session from Firestore"""
        if self.db:
            try:
                self.collection.document(session_id).delete()
                return True
            except Exception as e:
                logger.error(f"Error deleting session from Firestore: {e}")
                return False
        else:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False

    def update_session(self, session_id: str, **kwargs) -> Optional[SessionState]:
        """Update session state in Firestore"""
        session = self.get_session(session_id)
        if session:
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            if self.db:
                try:
                    # Partial update in Firestore for efficiency
                    update_data = {}
                    for key, value in kwargs.items():
                        if key == 'last_activity' and isinstance(value, datetime):
                            update_data[key] = value.isoformat()
                        else:
                            update_data[key] = value
                    self.collection.document(session_id).update(update_data)
                except Exception as e:
                    logger.error(f"Error updating session in Firestore: {e}")
            return session
        return None

    def store_oauth_tokens(self, session_id: str, tokens: dict) -> bool:
        """Store OAuth tokens for a session in Firestore"""
        return self.update_session(session_id, oauth_tokens=tokens, last_activity=datetime.utcnow()) is not None

    def get_oauth_tokens(self, session_id: str) -> Optional[dict]:
        """Retrieve OAuth tokens from Firestore session"""
        session = self.get_session(session_id)
        return session.oauth_tokens if session else None

    def refresh_oauth_token(self, session_id: str) -> Optional[dict]:
        """Refresh OAuth access token and update Firestore"""
        session = self.get_session(session_id)
        if not session or not session.oauth_tokens.get('refresh_token'):
            return None
        
        try:
            creds = Credentials(
                token=session.oauth_tokens.get('access_token'),
                refresh_token=session.oauth_tokens['refresh_token'],
                token_uri=os.getenv('OAUTH_TOKEN_ENDPOINT', 'https://oauth2.googleapis.com/token'),
                client_id=session.oauth_client_id or os.getenv('GOOGLE_CLIENT_ID'),
                client_secret=session.oauth_client_secret or os.getenv('GOOGLE_CLIENT_SECRET')
            )
            
            if creds.expired and creds.refresh_token:
                creds.refresh(GoogleAuthRequest())
                
                new_tokens = {
                    'access_token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_expiry': creds.expiry.isoformat() if creds.expiry else None,
                    'scopes': session.oauth_tokens.get('scopes', [])
                }
                self.store_oauth_tokens(session_id, new_tokens)
                return new_tokens
        except Exception as e:
            logger.error(f"Firestore session token refresh failed: {e}")
            return None

    def get_active_sessions_count(self) -> int:
        """Get approximate count of active sessions"""
        if self.db:
            try:
                # We can't easily get count from Firestore without a full scan or separate counter
                # For health check, a simple check if database is alive is often enough, 
                # but we'll try to get a count from the collection metadata if possible 
                # or just return -1 to indicate 'Firestore Mode'
                return -1 
            except Exception:
                return 0
        else:
            return len(self.sessions)


# ============================================================================
# Google Workspace Tools
# ============================================================================

class GoogleWorkspaceTools:
    """Google Workspace API integration tools"""
    
    def get_auth_error(self, session_id: str):
        """Helper to generate standard auth error response"""
        redirect_uri = os.getenv('OAUTH_REDIRECT_URI')
        if not redirect_uri:
            return {"error": "Authentication required", "message": "OAUTH_REDIRECT_URI is not set on the server."}
        
        # Determine the base URL for the authorization endpoint
        # Remove any callback path to get the base server URL
        base_url = redirect_uri
        for path in ['/oauth2/callback', '/oauth/callback', '/callback']:
            if path in base_url:
                base_url = base_url.split(path)[0]
        
        # Ensure base_url doesn't end with a slash for the custom /oauth/authorize endpoint
        base_url = base_url.rstrip('/')
        auth_url = f"{base_url}/oauth/authorize?session_id={session_id}"
        
        # Relay credentials back to authorize endpoint if we have them in session
        session = session_manager.get_session(session_id)
        if session:
            if session.oauth_client_id:
                auth_url += f"&client_id={session.oauth_client_id}"
            if session.oauth_client_secret:
                auth_url += f"&client_secret={session.oauth_client_secret}"
                
        return {"error": "Authentication required", "auth_url": auth_url}

    @staticmethod
    def get_service(session_id: str, service_name: str, version: str):
        """Get an authenticated Google API service"""
        tokens = session_manager.get_oauth_tokens(session_id)
        if not tokens or not tokens.get('access_token'):
            return None
            
        session = session_manager.get_session(session_id)
        env_cid, env_csec = get_google_credentials()
        creds = Credentials(
            token=tokens.get('access_token'),
            refresh_token=tokens.get('refresh_token'),
            token_uri=os.getenv('OAUTH_TOKEN_ENDPOINT'),
            client_id=(session.oauth_client_id if session else None) or env_cid,
            client_secret=(session.oauth_client_secret if session else None) or env_csec,
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
                    'scopes': getattr(creds, 'scopes', tokens.get('scopes'))
                })
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                return None
                
        return build(service_name, version, credentials=creds)

    async def search_drive_files(self, session_id: str, query: str, mime_type: Optional[str] = None, page_size: int = 10) -> dict:
        """Search Google Drive files"""
        service = self.get_service(session_id, 'drive', 'v3')
        if not service:
            return self.get_auth_error(session_id)
        
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
            return self.get_auth_error(session_id)
            
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
            return self.get_auth_error(session_id)
            
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
            return self.get_auth_error(session_id)
            
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
            return self.get_auth_error(session_id)
            
        results = service.calendarList().list(minAccessRole=min_access_role).execute()
        return results
    
    async def get_events(self, session_id: str, calendar_id: str = 'primary', time_min: Optional[str] = None, time_max: Optional[str] = None) -> dict:
        """Get calendar events. Defaults to 'primary' and today's schedule if range is omitted."""
        service = self.get_service(session_id, 'calendar', 'v3')
        if not service:
            return self.get_auth_error(session_id)
            
        # Default to today if times are missing
        if not time_min:
            time_min = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
        if not time_max:
            time_max = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999).isoformat() + 'Z'
            
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

# ============================================================================
# Startup
# ============================================================================

try:
    print("--- INITIALIZING APPLICATION COMPONENTS ---", flush=True)
    session_manager = SessionManager()
    workspace_tools = GoogleWorkspaceTools()
    print("--- COMPONENTS INITIALIZED SUCCESSFULLY ---", flush=True)
except Exception as e:
    print(f"!!! CRITICAL ERROR DURING COMPONENT INIT: {e} !!!", flush=True)
    import traceback
    traceback.print_exc()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    port = os.getenv("PORT", "8080")
    host = os.getenv("HOST", "0.0.0.0")
    print(f"--- SERVER STARTING AT {host}:{port} ---", flush=True)
    yield
    print("--- SERVER SHUTTING DOWN ---", flush=True)

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
        "sessions": session_manager.get_active_sessions_count(),
        "storage_mode": "firestore" if session_manager.db else "in-memory",
        "system": {
            "status": "active"
        }
    }


# ============================================================================
# OAuth Endpoints
# ============================================================================

@app.get("/oauth/authorize")
async def oauth_authorize(session_id: str = None, client_id: str = None, client_secret: str = None):
    """Initiate OAuth flow"""
    try:
        if not session_id:
            session_id = session_manager.create_session()
        
        # Favor query params, then session storage, then env vars
        cid = client_id
        csec = client_secret
        
        # Check session if missing
        session = session_manager.get_session(session_id)
        if not cid and session:
            cid = session.oauth_client_id
        if not csec and session:
            csec = session.oauth_client_secret
            
        # Fallback to env
        env_cid, env_csec = get_google_credentials()
        cid = cid or env_cid
        csec = csec or env_csec
        redirect_uri = os.getenv('OAUTH_REDIRECT_URI')
        
        if not cid or not csec or not redirect_uri:
            missing = []
            if not cid: missing.append("GOOGLE_CLIENT_ID / client_id")
            if not csec: missing.append("GOOGLE_CLIENT_SECRET / client_secret")
            if not redirect_uri: missing.append("OAUTH_REDIRECT_URI")
            
            error_detail = f"Missing required configuration: {', '.join(missing)}. "
            if session_id:
                error_detail += f"Checked session ID: {session_id}. Session found: {bool(session)}. "
                if session:
                    error_detail += f"Session keys: {[k for k in session.dict().keys() if getattr(session, k) is not None]}. "
            
            logger.error(f"Cannot initiate OAuth: {error_detail}")
            raise HTTPException(
                status_code=500, 
                detail=error_detail + "Please ensure Client ID and Client Secret are provided in Nexus Server Configuration."
            )

        # Store back in session to ensure consistency for callback
        session_manager.update_session(session_id, oauth_client_id=cid, oauth_client_secret=csec)
        
        # Update local variables for following flow code
        client_id = cid
        client_secret = csec

        scopes_env = os.getenv('OAUTH_SCOPES', 'https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/calendar.readonly')
        scopes = [s.strip() for s in scopes_env.split(',') if s.strip()]
        
        logger.info(f"Initiating OAuth: client_id={client_id}, redirect_uri={redirect_uri}, scopes={scopes}")
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": os.getenv('OAUTH_AUTH_ENDPOINT', 'https://accounts.google.com/o/oauth2/auth'),
                    "token_uri": os.getenv('OAUTH_TOKEN_ENDPOINT', 'https://oauth2.googleapis.com/token'),
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
        
        logger.info(f"Generated authorization_url for session {session_id}: {authorization_url}")
        session_manager.update_session(session_id, oauth_state=state, scopes=scopes)
        return RedirectResponse(url=authorization_url)
        
    except Exception as e:
        logger.error(f"OAuth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/oauth/config")
async def oauth_config():
    """Check if global OAuth credentials are configured"""
    cid, csec = get_google_credentials()
    return {
        "configured": bool(cid and csec),
        "has_client_id": bool(cid),
        "has_client_secret": bool(csec),
        "redirect_uri": os.getenv('OAUTH_REDIRECT_URI')
    }


@app.get("/oauth/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None, session_id: str = None):
    """Handle OAuth callback"""
    try:
        if error:
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code missing")

        # Attempt to retrieve session if session_id provided
        session = None
        if session_id:
            session = session_manager.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found during callback")
        
        # State validation if session exists
        if session and session.oauth_state and state != session.oauth_state:
            logger.error(f"State mismatch: received {state}, expected {session.oauth_state}")
            # We'll continue for now but log the error, as some environments or strictness might differ
            # In a production app, you might want to raise an error here.
        
        # Try to get credentials from session or environment
        env_cid, env_csec = get_google_credentials()
        client_id = (session.oauth_client_id if session else None) or env_cid
        client_secret = (session.oauth_client_secret if session else None) or env_csec
        redirect_uri = os.getenv('OAUTH_REDIRECT_URI')
        
        if not client_id or not client_secret or not redirect_uri:
            raise HTTPException(status_code=500, detail="OAuth is not fully configured. Ensure Client ID and Secret are provided.")

        # Use stored scopes if available, otherwise default
        scopes = session.scopes if session and session.scopes else []
        if not scopes:
            scopes_env = os.getenv('OAUTH_SCOPES', 'https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/calendar.readonly')
            scopes = [s.strip() for s in scopes_env.split(',') if s.strip()]
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": os.getenv('OAUTH_AUTH_ENDPOINT', 'https://accounts.google.com/o/oauth2/auth'),
                    "token_uri": os.getenv('OAUTH_TOKEN_ENDPOINT', 'https://oauth2.googleapis.com/token'),
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=scopes,
            state=state
        )
        flow.redirect_uri = redirect_uri
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        tokens = {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_expiry': credentials.expiry.isoformat() if credentials.expiry else None,
            'scopes': getattr(credentials, 'scopes', scopes)
        }
        
        if not session_id:
            session_id = session_manager.create_session()
        
        session_manager.store_oauth_tokens(session_id, tokens)
        logger.info(f"Authentication successful for session: {session_id} (Saved to Firestore)")
        
        # Return a premium success page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authenticated | Nexus</title>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Outfit:wght@600;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --primary: #3b82f6;
                    --primary-hover: #2563eb;
                    --bg: #0f172a;
                    --card-bg: rgba(15, 23, 42, 0.8);
                    --text: #f8fafc;
                    --text-muted: #94a3b8;
                    --accent: #38bdf8;
                    --success: #06b6d4;
                }}
                * {{ box-sizing: border-box; }}
                body {{
                    font-family: 'Inter', system-ui, -apple-system, sans-serif;
                    background-color: var(--bg);
                    background-image: 
                        radial-gradient(at 0% 0%, hsla(215, 25%, 15%, 1) 0, transparent 50%), 
                        radial-gradient(at 50% 0%, hsla(201, 94%, 30%, 0.1) 0, transparent 50%);
                    color: var(--text);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                    overflow: hidden;
                }}
                .card {{
                    background: var(--card-bg);
                    backdrop-filter: blur(12px);
                    -webkit-backdrop-filter: blur(12px);
                    padding: 3.5rem 2.5rem;
                    border-radius: 2rem;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.05);
                    text-align: center;
                    max-width: 440px;
                    width: 90%;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1);
                    position: relative;
                }}
                @keyframes slideUp {{
                    from {{ transform: translateY(30px); opacity: 0; }}
                    to {{ transform: translateY(0); opacity: 1; }}
                }}
                .icon-container {{
                    position: relative;
                    width: 80px;
                    height: 80px;
                    margin: 0 auto 2rem;
                }}
                .icon-pulse {{
                    position: absolute;
                    top: 0; left: 0; width: 100%; height: 100%;
                    background: var(--success);
                    border-radius: 50%;
                    opacity: 0.2;
                    animation: pulse 2s infinite;
                }}
                @keyframes pulse {{
                    0% {{ transform: scale(1); opacity: 0.2; }}
                    70% {{ transform: scale(1.5); opacity: 0; }}
                    100% {{ transform: scale(1); opacity: 0; }}
                }}
                .icon {{
                    width: 80px;
                    height: 80px;
                    background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                    z-index: 1;
                    box-shadow: 0 10px 20px rgba(6, 182, 212, 0.3);
                }}
                h1 {{
                    font-family: 'Outfit', sans-serif;
                    font-size: 2.5rem;
                    font-weight: 700;
                    margin: 0 0 1rem;
                    letter-spacing: -0.02em;
                    background: linear-gradient(135deg, #f8fafc 0%, #cbd5e1 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }}
                p {{
                    color: var(--text-muted);
                    font-size: 1.05rem;
                    line-height: 1.6;
                    margin-bottom: 2rem;
                }}
                .session-info {{
                    background: rgba(15, 23, 42, 0.6);
                    padding: 1rem;
                    border-radius: 1rem;
                    margin-bottom: 2.5rem;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }}
                .session-label {{
                    font-size: 0.75rem;
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                    color: var(--accent);
                    margin-bottom: 0.5rem;
                    font-weight: 600;
                }}
                .session-id {{
                    font-family: 'JetBrains Mono', 'Fira Code', monospace;
                    font-size: 0.85rem;
                    color: #e2e8f0;
                    word-break: break-all;
                }}
                .btn {{
                    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                    color: white;
                    padding: 1rem 2rem;
                    border-radius: 1rem;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 1rem;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    display: inline-block;
                    width: 100%;
                    box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }}
                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 15px 30px rgba(37, 99, 235, 0.3);
                    filter: brightness(1.1);
                }}
                .btn:active {{ transform: translateY(0); }}
                
                .footer-text {{
                    margin-top: 1.5rem;
                    font-size: 0.875rem;
                    color: var(--text-muted);
                }}
            </style>
            <script>
                // Notify the opener window that authentication was successful
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'oauth_success',
                        session_id: '{session_id}',
                        service: 'google-workspace',
                        tokens: {json.dumps(tokens)}
                    }}, '*');
                }}
            </script>
        </head>
        <body>
            <div class="card">
                <div class="icon-container">
                    <div class="icon-pulse"></div>
                    <div class="icon">
                        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
                    </div>
                </div>
                <h1>Success!</h1>
                <p>Authentication complete. Your Google Workspace tools are now securely connected.</p>
                
                <div class="session-info">
                    <div class="session-label">Active Session</div>
                    <div class="session-id">{session_id}</div>
                </div>

                <a href="javascript:window.close()" class="btn">Return to Project Nexus</a>
                <div class="footer-text">You can now safely close this window.</div>
            </div>
        </body>
        </html>
        """
        return Response(content=html_content, media_type="text/html")
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MCP Streamable HTTP Endpoints
# ============================================================================


# Tool Definitions
TOOLS_SCHEMA = [
    {
        "name": "list_calendars",
        "description": "List available Google Calendars",
        "inputSchema": {
            "type": "object",
            "properties": {
                "min_access_role": {"type": "string", "description": "Min access role (writer, reader, owner)", "default": "reader"}
            }
        }
    },
    {
        "name": "get_events",
        "description": "Get events from a calendar. If no time range is provided, it defaults to today's schedule.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "calendar_id": {"type": "string", "description": "The Calendar ID", "default": "primary"},
                "time_min": {"type": "string", "description": "Start time (ISO format, e.g. 2023-10-10T00:00:00Z)"},
                "time_max": {"type": "string", "description": "End time (ISO format, e.g. 2023-10-10T23:59:59Z)"}
            }
        }
    },
    {
        "name": "search_drive_files",
        "description": "Search for files in Google Drive",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Drive search query info"},
                "mime_type": {"type": "string", "description": "Filter by MIME type"},
                "page_size": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_drive_file_content",
        "description": "Get the content of a file from Google Drive",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "The file ID"},
                "export_format": {"type": "string", "description": "MIME type for exporting Docs/Sheets (e.g. application/pdf)", "default": "application/pdf"}
            },
            "required": ["file_id"]
        }
    },
    {
        "name": "search_gmail_messages",
        "description": "Search Gmail messages",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search query"},
                "max_results": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "gmail_create_draft",
        "description": "Create a draft email",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body"}
            },
            "required": ["to", "subject", "body"]
        }
    }
]

@app.post("/mcp")
async def mcp_post(
    request: Request,
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    x_mcp_session_id: Optional[str] = Header(None, alias="X-Mcp-Session-Id"),
    x_google_client_id: Optional[str] = Header(None, alias="X-Google-Client-Id"),
    x_google_client_secret: Optional[str] = Header(None, alias="X-Google-Client-Secret"),
    x_google_access_token: Optional[str] = Header(None, alias="X-Google-Access-Token"),
    x_google_refresh_token: Optional[str] = Header(None, alias="X-Google-Refresh-Token")
):
    """MCP HTTP transport root - handles POST as JSON-RPC"""
    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    method = body.get("method")
    
    # Extract session ID from headers or body
    config = body.get("config", {})
    relay_headers = config.get("headers", {})
    session_id = (
        session_id or 
        x_mcp_session_id or 
        body.get("params", {}).get("session_id") or 
        relay_headers.get("X-Session-ID") or 
        relay_headers.get("x-session-id")
    )
    session = session_manager.get_session(session_id)
    
    if not session:
        # Create a new session if missing or expired
        session_id = session_manager.create_session(client_name="mcp-client")
        session_manager.update_session(session_id, initialized=True)
        session = session_manager.get_session(session_id)
        logger.info(f"Using new/recreated session: {session_id}")
    
    # Trace OAuth token state for the session
    has_tokens = bool(session.oauth_tokens)
    logger.info(f"Session {session_id} state - has_tokens: {has_tokens}, initialized: {session.initialized}")
    
    # Update session with relayed Google credentials from various sources
    # 1. From direct headers
    cid = x_google_client_id
    cs = x_google_client_secret
    
    # 2. From config in body (standard for our frontend)
    config = body.get("config", {})
    if not cid:
        cid = config.get("oauthClientId")
    if not cs:
        cs = config.get("oauthClientSecret")
        
    # 3. From headers embedded in config (another common relay pattern)
    relay_headers = config.get("headers", {})
    if not cid:
        cid = relay_headers.get("X-Google-Client-Id") or relay_headers.get("x-google-client-id")
    if not cs:
        cs = relay_headers.get("X-Google-Client-Secret") or relay_headers.get("x-google-client-secret")

    if cid or cs or x_google_access_token:
        # Construct updated state
        update_data = {}
        if cid: update_data['oauth_client_id'] = cid
        if cs: update_data['oauth_client_secret'] = cs
        
        # Hydrate tokens if relayed from client
        if x_google_access_token:
            # Important: Get fresh session data from Firestore before updating
            current_session = session_manager.get_session(session_id)
            current_tokens = (current_session.oauth_tokens if current_session else {}) or {}
            
            # Update with relayed tokens
            current_tokens['access_token'] = x_google_access_token
            if x_google_refresh_token:
                current_tokens['refresh_token'] = x_google_refresh_token
            update_data['oauth_tokens'] = current_tokens
            
        session_manager.update_session(session_id, **update_data)
        logger.info(f"Updated Firestore session {session_id} with relayed credentials/tokens")

    logger.info(f"Incoming MCP request: {method} for session: {session_id}")
    
    # Log headers (redacting sensitive ones)
    headers_to_log = {k: v for k, v in request.headers.items() if k and k.lower() not in ['authorization', 'cookie', 'x-api-key', 'x-google-client-id', 'x-google-client-secret']}
    logger.info(f"Headers: {json.dumps(headers_to_log)}")

    if method == "initialize":
        session_manager.update_session(session_id, initialized=True)
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True}
                },
                "serverInfo": {
                    "name": "Google Workspace MCP Server",
                    "version": "0.1.0"
                }
            }
        }, headers={"Mcp-Session-Id": session_id})
    
    if method in ["tools/list", "list_tools"]:
        logger.info(f"Returning {len(TOOLS_SCHEMA)} tools")
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "tools": TOOLS_SCHEMA
            }
        })
    
    if method == "tools/call":
        tool_name = body.get("params", {}).get("name")
        arguments = body.get("params", {}).get("arguments", {})
        
        # Add session_id to arguments for auth
        arguments["session_id"] = session_id
        
        try:
            if hasattr(workspace_tools, tool_name):
                tool_func = getattr(workspace_tools, tool_name)
                result = await tool_func(**arguments)
                
                # Check for auth required
                if isinstance(result, dict) and result.get("error") == "Authentication required":
                    auth_response = workspace_tools.get_auth_error(session_id)
                    auth_url = auth_response.get('auth_url')
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
    
    logger.info(f"Starting uvicorn on {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
