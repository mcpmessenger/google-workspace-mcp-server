"""
OAuth 2.0 endpoints for Google Workspace authentication
Add these endpoints to main.py after the health check endpoint
"""

# ============================================================================
# OAuth Endpoints
# ============================================================================

@app.get("/oauth/authorize")
async def oauth_authorize(session_id: str = None):
    """Initiate OAuth flow"""
    try:
        # Create or use existing session
        if not session_id:
            session_id = session_manager.create_session()
        
        # Get OAuth configuration from environment
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        redirect_uri = os.getenv('OAUTH_REDIRECT_URI')
        scopes = os.getenv('OAUTH_SCOPES', '').split(',')
        
        if not client_id or not redirect_uri:
            raise HTTPException(
                status_code=500,
                detail="OAuth not configured. Please set GOOGLE_CLIENT_ID and OAUTH_REDIRECT_URI"
            )
        
        # Create OAuth flow
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
        
        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Store state in session for verification
        session_manager.update_session(session_id, oauth_state=state)
        
        logger.info(f"OAuth flow initiated for session: {session_id}")
        
        # Redirect to Google OAuth consent screen
        return RedirectResponse(url=authorization_url)
        
    except Exception as e:
        logger.error(f"OAuth authorization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/oauth/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None, session_id: str = None):
    """Handle OAuth callback from Google"""
    try:
        if error:
            logger.error(f"OAuth error: {error}")
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        
        if not code:
            raise HTTPException(status_code=400, detail="No authorization code received")
        
        # Get OAuth configuration
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        redirect_uri = os.getenv('OAUTH_REDIRECT_URI')
        scopes = os.getenv('OAUTH_SCOPES', '').split(',')
        
        # Create OAuth flow
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
            scopes=scopes,
            state=state
        )
        flow.redirect_uri = redirect_uri
        
        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Store tokens in session
        tokens = {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_expiry': credentials.expiry.isoformat() if credentials.expiry else None,
            'scopes': credentials.scopes
        }
        
        # Find or create session
        if not session_id:
            session_id = session_manager.create_session()
        
        session_manager.store_oauth_tokens(session_id, tokens)
        
        logger.info(f"OAuth tokens stored for session: {session_id}")
        
        # Return success page or redirect to dashboard
        return {
            "status": "success",
            "message": "Authentication successful",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
