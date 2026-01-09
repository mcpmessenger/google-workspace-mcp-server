# Local Testing with ngrok

This guide shows you how to test OAuth locally using ngrok to expose your local server to the internet.

## Why ngrok?

OAuth requires a publicly accessible callback URL. During local development, your server runs on `localhost`, which Google's OAuth servers cannot reach. ngrok creates a secure tunnel to your local server, giving you a public URL.

## Step 1: Install ngrok

### Windows
1. Download ngrok from [ngrok.com/download](https://ngrok.com/download)
2. Extract the ZIP file
3. (Optional) Add ngrok to your PATH

### macOS (Homebrew)
```bash
brew install ngrok/ngrok/ngrok
```

### Linux
```bash
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

## Step 2: Sign Up for ngrok (Optional but Recommended)

1. Go to [ngrok.com](https://ngrok.com) and sign up for a free account
2. Get your auth token from the dashboard
3. Configure ngrok with your token:
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

## Step 3: Start Your Backend Server

```bash
cd backend
python main.py
```

Your server should be running on `http://localhost:8081`

## Step 4: Start ngrok Tunnel

In a new terminal window:

```bash
ngrok http 8081
```

You'll see output like:

```
Session Status                online
Account                       your-account (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok.io -> http://localhost:8081
```

**Copy the `https://abc123.ngrok.io` URL** - this is your public URL!

## Step 5: Update OAuth Redirect URI

### In Google Cloud Console:
1. Go to **APIs & Services** > **Credentials**
2. Click on your OAuth 2.0 Client ID
3. Under **Authorized redirect URIs**, add:
   ```
   https://abc123.ngrok.io/oauth/callback
   ```
   (Replace `abc123` with your actual ngrok subdomain)
4. Click **"Save"**

### In Your `.env` File:
```env
OAUTH_REDIRECT_URI=https://abc123.ngrok.io/oauth/callback
```

## Step 6: Test OAuth Flow

1. Open your browser and go to:
   ```
   https://abc123.ngrok.io/oauth/authorize
   ```

2. You should be redirected to Google's OAuth consent screen
3. Sign in and grant permissions
4. You'll be redirected back to your ngrok URL with a success message

## Step 7: Monitor Requests (Optional)

ngrok provides a web interface to inspect HTTP traffic:

```
http://localhost:4040
```

This shows all requests going through the tunnel, which is helpful for debugging.

## Tips & Best Practices

### Keep ngrok Running
- ngrok must stay running while you're testing
- If you restart ngrok, you'll get a new URL (unless you have a paid plan)
- Update the redirect URI in Google Cloud Console if the URL changes

### Use a Custom Domain (Paid Feature)
With ngrok's paid plans, you can use a custom subdomain:
```bash
ngrok http --subdomain=my-mcp-server 8081
```

This gives you a consistent URL: `https://my-mcp-server.ngrok.io`

### Security Considerations
- ngrok URLs are publicly accessible
- Don't share your ngrok URL publicly
- Use ngrok only for development/testing
- For production, deploy to a proper hosting service

## Troubleshooting

### "Tunnel not found" Error
- Make sure ngrok is running
- Check that you're using the correct port (8081)

### OAuth Redirect Mismatch
- Verify the redirect URI in Google Cloud Console matches your ngrok URL exactly
- Include `/oauth/callback` at the end
- Use `https://`, not `http://`

### ngrok Session Expired
- Free ngrok sessions expire after 2 hours
- Restart ngrok and update your redirect URI

## Next Steps

Once OAuth is working locally:
- [Deploy to Google Cloud Run](./deploy-cloud-run.md) for production
- [Configure MCP Clients](./mcp-client-setup.md) to use your server
