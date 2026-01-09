# Google Cloud OAuth Setup Guide

This guide walks you through setting up OAuth 2.0 credentials for the Google Workspace MCP Server.

## Prerequisites

- A Google Cloud Project
- Access to Google Cloud Console
- Project billing enabled (for API usage)

## Step 1: Create or Select a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click the project dropdown at the top
3. Click **"New Project"** or select an existing project
4. Name your project (e.g., "Google Workspace MCP Server")
5. Click **"Create"**

## Step 2: Enable Required APIs

1. In the Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for and enable the following APIs:
   - **Google Drive API**
   - **Gmail API**
   - **Google Calendar API**
3. Click **"Enable"** for each API

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Select **External** user type (or Internal if using Google Workspace)
3. Click **"Create"**
4. Fill in the required fields:
   - **App name**: Google Workspace MCP Server
   - **User support email**: Your email
   - **Developer contact**: Your email
5. Click **"Save and Continue"**
6. On the **Scopes** page, click **"Add or Remove Scopes"**
7. Add the following scopes:
   - `https://www.googleapis.com/auth/drive`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/calendar`
8. Click **"Save and Continue"**
9. Add test users (your email) if using External user type
10. Click **"Save and Continue"**

## Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **"Create Credentials"** > **"OAuth client ID"**
3. Select **"Web application"**
4. Name it: "MCP Server OAuth Client"
5. Under **Authorized redirect URIs**, add:
   - For local development: `http://localhost:8081/oauth/callback`
   - For production: `https://your-domain.com/oauth/callback`
6. Click **"Create"**
7. **Important**: Copy your **Client ID** and **Client Secret**

## Step 5: Update Environment Variables

1. Open `backend/.env` file
2. Update the following variables with your credentials:

```env
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
OAUTH_REDIRECT_URI=http://localhost:8081/oauth/callback
```

## Step 6: Test OAuth Flow

1. Start your backend server:
   ```bash
   cd backend
   python main.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:8081/oauth/authorize
   ```

3. You should be redirected to Google's OAuth consent screen
4. Sign in with your Google account
5. Grant the requested permissions
6. You'll be redirected back to the callback URL with a success message

## Security Best Practices

> [!WARNING]
> **Never commit your `.env` file to version control!**

- Keep your `CLIENT_SECRET` secure
- Use environment variables for all sensitive data
- Rotate credentials periodically
- Use HTTPS in production
- Limit OAuth scopes to only what you need

## Troubleshooting

### "redirect_uri_mismatch" Error
- Ensure the redirect URI in your code exactly matches the one in Google Cloud Console
- Check for trailing slashes
- Verify HTTP vs HTTPS

### "access_denied" Error
- User declined authorization
- Check that required scopes are configured in OAuth consent screen

### "invalid_client" Error
- Client ID or Client Secret is incorrect
- Verify credentials in `.env` file

## Next Steps

- [Local Testing with ngrok](./setup-ngrok.md)
- [Deploy to Google Cloud Run](./deploy-cloud-run.md)
- [Configure MCP Clients](./mcp-client-setup.md)
