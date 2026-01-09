# Google Workspace MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-Protocol-blue)](https://modelcontextprotocol.io)

A professional [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server implementation for Google Workspace, featuring a "Retro Postcard" management dashboard. This server allows AI agents (like Claude or Gemini) to interact securely with your Google Drive, Gmail, and Calendar data.

![Dashboard Preview](client/public/preview.png) *(Placeholder: Actual dashboard features a unique retro postcard aesthetic)*

## 🌟 Features

- **Standard MCP Protocol**: Implements the latest MCP specification using Streamable HTTP transport.
- **Google Workspace Integration**:
  - **Drive**: Search, read, and manage files.
  - **Gmail**: Search and send messages, manage threads.
  - **Calendar**: List calendars and manage events.
- **Vintage Dashboard**: A beautifully designed "Retro Postcard" management interface to monitor server health, sessions, and configuration.
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

## 🛠️ Components

- **Backend**: FastAPI server handling MCP requests and Google OAuth.
- **Frontend**: React (Vite) dashboard with Tailwind CSS and Radix UI.
- **Server**: Express server for static file hosting in production.

## 📜 Documentation

For detailed protocol specifications and API usage, visit the [official documentation](https://github.com/mcpmessenger/google-workspace-mcp-server).

## 📄 License

This project is licensed under the MIT License.
