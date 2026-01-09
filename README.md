# Google Workspace MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-Protocol-blue)](https://modelcontextprotocol.io)

A professional [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server implementation for Google Workspace, featuring a "Retro Postcard" management dashboard. This server allows AI agents (like Claude or Gemini) to interact securely with your Google Drive, Gmail, and Calendar data.

![Dashboard Preview](client/public/preview.png) *(Placeholder: Actual dashboard features a unique retro postcard aesthetic)*

## 🌟 Features

- **Standard MCP Protocol**: Implements the latest MCP specification using Streamable HTTP transport.
- **Google Workspace Integration**:
  - **Drive**: Search, read, and export files.
  - **Gmail**: Search threads, manage drafts, and send emails.
  - **Calendar**: List events and manage schedules.
  - **Docs/Sheets/Slides**: Create and edit documents, spreadsheets, and presentations.
- **Modern Nordic Dashboard**: A clean, professional "Snow & Slate" management interface with dark mode, live metrics, and real-time status.
- **Cloud Ready**: Optimized for deployment on Google Cloud Run.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ & `pnpm`
- Google Cloud Project with OAuth 2.0 credentials

### 1. Clone the Repository

```bash
git clone https://github.com/mcpmessenger/google-workspace-mcp-server.git
cd google-workspace-mcp-server
```

### Client Integration (Claude Desktop)

To use this server with Claude Desktop, add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-google-workspace"],
      "env": {
        "GOOGLE_CLIENT_ID": "your-client-id",
        "GOOGLE_CLIENT_SECRET": "your-client-secret"
      }
    },
    "workspace-cloud": {
      "url": "https://your-service-url.a.run.app/mcp",
      "transport": "sse"
    }
  }
}
```

> **Note**: For the Cloud Run deployment, simply use the `url` transport as shown above.

### Client Integration (Cursor)

1.  Open **Cursor Settings** (Ctrl+Shift+J or Cmd+Shift+J).
2.  Navigate to **Generative AI** > **MCP Servers** (or just **MCP** in newer versions).
3.  Click **+ Add New MCP Server**.
4.  Select **Type**: `SSE` (Server-Sent Events).
5.  **Name**: `google-workspace`
6.  **URL**: `https://google-workspace-mcp-server-554655392699.us-central1.run.app/mcp`
7.  Click **Save**.

### 2. Backend Setup

```bash
cd backend
python -m pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:

```env
PORT=8081
HOST=0.0.0.0
GCP_PROJECT_ID=your-project-id
# OAuth Settings
OAUTH_ISSUER=https://accounts.google.com
OAUTH_AUTH_ENDPOINT=https://accounts.google.com/o/oauth2/v2/auth
OAUTH_TOKEN_ENDPOINT=https://oauth2.googleapis.com/token
```

Start the backend:
```bash
python main.py
```

### 3. Frontend Setup

In the root directory:

```bash
pnpm install
pnpm dev
```

The dashboard will be available at `http://localhost:3000` (or the port specified by Vite).

## ☁️ Cloud Deployment

### 1. Google Cloud Run

To deploy the backend to Cloud Run:

```bash
cd backend
gcloud run deploy google-workspace-mcp-server --source . --region us-central1
```

### 2. Environment Configuration

Ensure the following environment variables are set in Cloud Run:

```yaml
GOOGLE_CLIENT_ID: "your-client-id"
GOOGLE_CLIENT_SECRET: "your-client-secret"
OAUTH_REDIRECT_URI: "https://your-service-url.a.run.app/oauth/callback"
OAUTH_AUTH_ENDPOINT: "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN_ENDPOINT: "https://oauth2.googleapis.com/token"
OAUTH_SCOPES: "openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/userinfo.profile,https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/calendar.readonly,https://www.googleapis.com/auth/documents,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/presentations"
OAUTHLIB_RELAX_TOKEN_SCOPE: "1"
```

### 3. Google Cloud Console Setup

1.  **OAuth Consent Screen**: Add the scopes listed above.
2.  **Credentials**: Create an OAuth 2.0 Client ID for a **Web Application**.
3.  **Authorized Redirect URIs**: Add `https://your-service-url.a.run.app/oauth/callback`.

## 🛠️ Components

- **Backend**: FastAPI server handling MCP requests and Google OAuth.
- **Frontend**: React (Vite) dashboard with Tailwind CSS and Radix UI.
- **Server**: Express server for static file hosting in production.

## 📜 Documentation

For a step-by-step verification guide, check out the [Walkthrough](file:///C:/Users/senti/.gemini/antigravity/brain/cb6a28a9-b834-4946-a1f3-8413abd01710/walkthrough.md).

## 📄 License

This project is licensed under the MIT License.
