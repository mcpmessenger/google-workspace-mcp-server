# MCP Client Setup Guide

This guide shows you how to configure MCP clients (like Claude Desktop) to use your Google Workspace MCP Server.

## What is an MCP Client?

MCP (Model Context Protocol) clients are applications that can connect to MCP servers to extend their capabilities. The most common client is Claude Desktop, but the protocol is designed to work with any compatible client.

## Prerequisites

- Google Workspace MCP Server deployed and running
- OAuth configured and tested
- MCP client installed (e.g., Claude Desktop)

## Claude Desktop Configuration

### Step 1: Locate Configuration File

The Claude Desktop configuration file is located at:

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### Step 2: Add MCP Server Configuration

Edit the configuration file and add your server:

```json
{
  "mcpServers": {
    "google-workspace": {
      "url": "https://your-server-url.run.app/mcp",
      "transport": "streamable-http",
      "headers": {
        "Authorization": "Bearer YOUR_SESSION_TOKEN"
      }
    }
  }
}
```

**For local development with ngrok:**
```json
{
  "mcpServers": {
    "google-workspace-local": {
      "url": "https://abc123.ngrok.io/mcp",
      "transport": "streamable-http"
    }
  }
}
```

### Step 3: Restart Claude Desktop

Close and reopen Claude Desktop for the changes to take effect.

## Authentication Flow

### First-Time Setup

1. **Start a conversation in Claude Desktop**
2. **Trigger OAuth authentication:**
   - Claude will detect that authentication is required
   - You'll be prompted to authorize the connection
   
3. **Complete OAuth flow:**
   - Click the authorization link
   - Sign in to your Google account
   - Grant the requested permissions
   - You'll receive a session ID

4. **Update configuration with session:**
   ```json
   {
     "mcpServers": {
       "google-workspace": {
         "url": "https://your-server-url.run.app/mcp",
         "transport": "streamable-http",
         "headers": {
           "X-Session-ID": "your-session-id-here"
         }
       }
     }
   }
   ```

### Session Management

Sessions are valid for 24 hours by default. After expiration:
1. Remove the old session ID from config
2. Restart Claude Desktop
3. Complete OAuth flow again

## Available Tools

Once connected, you can use these Google Workspace tools in Claude:

### Google Drive
- `search_drive_files` - Search for files in Drive
- `get_drive_file_content` - Get file content
- `create_drive_file` - Create a new file
- `update_drive_file` - Update existing file
- `list_drive_items` - List files and folders

### Gmail
- `search_gmail_messages` - Search emails
- `get_gmail_message_content` - Read email content
- `send_gmail_message` - Send an email
- `modify_gmail_labels` - Manage email labels
- `get_thread_content_batch` - Get email thread

### Google Calendar
- `list_calendars` - List your calendars
- `get_events` - Get calendar events
- `create_event` - Create a calendar event
- `query_free_busy` - Check availability
- `quick_add_event` - Quick event creation

## Example Usage

### In Claude Desktop:

**Search Drive:**
```
Can you search my Google Drive for files about "project proposal"?
```

**Read Emails:**
```
Show me my recent emails from john@example.com
```

**Create Calendar Event:**
```
Create a meeting for tomorrow at 2pm titled "Team Sync"
```

## Troubleshooting

### "Server not responding"
- Check that your server is running
- Verify the URL in your configuration
- Check server logs for errors

### "Authentication required"
- Complete the OAuth flow
- Ensure session ID is in configuration
- Check that session hasn't expired

### "Permission denied"
- Verify OAuth scopes are correctly configured
- Re-authorize if you've changed scopes
- Check Google Cloud Console for API access

### Tools not appearing
- Restart Claude Desktop
- Check configuration file syntax (valid JSON)
- Verify server is returning tool list correctly

## Advanced Configuration

### Multiple Servers

You can configure multiple MCP servers:

```json
{
  "mcpServers": {
    "google-workspace-prod": {
      "url": "https://prod-server.run.app/mcp",
      "transport": "streamable-http"
    },
    "google-workspace-dev": {
      "url": "https://dev-server.run.app/mcp",
      "transport": "streamable-http"
    }
  }
}
```

### Custom Headers

Add custom headers for authentication or tracking:

```json
{
  "mcpServers": {
    "google-workspace": {
      "url": "https://your-server.run.app/mcp",
      "transport": "streamable-http",
      "headers": {
        "X-Session-ID": "your-session",
        "X-Client-Version": "1.0.0",
        "X-Custom-Header": "value"
      }
    }
  }
}
```

## Security Best Practices

- **Never share your session ID** - It provides full access to your Google Workspace
- **Use HTTPS** - Always use secure connections in production
- **Rotate sessions** - Periodically re-authenticate for security
- **Monitor usage** - Check server logs for unexpected activity
- **Limit scopes** - Only grant necessary OAuth permissions

## Next Steps

- Explore available tools in Claude Desktop
- Set up monitoring for your MCP server
- Configure additional Google Workspace services
- Implement custom tools for your workflow
