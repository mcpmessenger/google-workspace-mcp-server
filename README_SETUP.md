# Google Workspace MCP Server Setup

## Prerequisites
- Python 3.10+
- Google Cloud Project with Gmail, Drive, and Calendar APIs enabled.
- OAuth 2.0 Client credentials (Client ID and Secret).

## Installation

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Install Dependencies:**
    ```bash
    python -m pip install -r requirements.txt
    ```

3.  **Configuration:**
    The `.env` file should be automatically configured by the setup script. If not, verify it contains:
    - `PORT=8081`
    - `GOOGLE_CLIENT_ID=...`
    - `GOOGLE_CLIENT_SECRET=...`

## Running the Server

**Important:** This server must be running in a separate terminal window for Nexus to connect.

1.  **Start the Server:**
    Make sure you are in the `backend` directory:
    ```bash
    # From the google-workspace-mcp-server directory:
    cd backend
    python main.py
    ```

2.  **Verify:**
    You should see output indicating the server is running on `http://0.0.0.0:8081`.

## Connecting to Nexus

1.  Go to the **Monitoring** page in Nexus.
2.  Click **+ Add Server**.
3.  Fill in the details:
    - **Name:** Google Workspace
    - **URL:** `http://localhost:8081/mcp`
    - **Transport:** HTTP (should auto-select)
4.  Click **Add Server**.
