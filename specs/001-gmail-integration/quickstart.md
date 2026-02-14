# Quickstart Guide: Gmail Integration for AI Employee

**Feature**: 001-gmail-integration
**Date**: 2026-02-12
**Audience**: Developers implementing the Gmail watcher and MCP server

## Overview

This guide walks you through setting up and running the Gmail integration feature, which consists of:
1. **Gmail Watcher**: Python daemon that monitors Gmail inbox and creates action files
2. **Gmail MCP Server**: MCP server that provides send_email tool for Claude

**Estimated Setup Time**: 30-45 minutes

---

## Prerequisites

### System Requirements
- Python 3.13+ installed
- PM2 installed (`npm install -g pm2`)
- Git repository cloned
- Obsidian vault initialized with folder structure

### Required Accounts
- Google Cloud Platform account (free tier sufficient)
- Gmail account to monitor

### Knowledge Requirements
- Basic Python programming
- Understanding of OAuth2 authentication
- Familiarity with command line tools

---

## Step 1: Google Cloud Setup (15 minutes)

### 1.1 Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Create Project"
3. Name: "AI Employee Gmail Integration"
4. Click "Create"

### 1.2 Enable Gmail API

1. In the project, go to "APIs & Services" > "Library"
2. Search for "Gmail API"
3. Click "Enable"

### 1.3 Create OAuth2 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Configure consent screen:
   - User Type: External
   - App name: "AI Employee"
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Add `gmail.readonly`, `gmail.send`, `gmail.modify`
4. Create OAuth client ID:
   - Application type: Desktop app
   - Name: "AI Employee Desktop"
5. Download JSON credentials file
6. Save as `client_secret.json` (temporary, will extract values)

### 1.4 Extract Credentials

Open `client_secret.json` and extract:
```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "client_secret": "YOUR_CLIENT_SECRET"
  }
}
```

---

## Step 2: Environment Configuration (5 minutes)

### 2.1 Create .env File

In the repository root, create `.env`:

```bash
# Gmail OAuth2 Credentials
GMAIL_CLIENT_ID=YOUR_CLIENT_ID.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=YOUR_CLIENT_SECRET

# System Settings
DRY_RUN=false
LOG_LEVEL=INFO

# Rate Limiting
GMAIL_RATE_LIMIT_HOURLY=20
GMAIL_RATE_LIMIT_DAILY=100
```

### 2.2 Verify .gitignore

Ensure `.gitignore` contains:
```
.env
credentials/
config/gmail_watcher_state.json
```

### 2.3 Create Required Directories

```bash
mkdir -p credentials config
mkdir -p mcp_servers/gmail/tools
mkdir -p src/watchers src/utils
mkdir -p tests/unit tests/integration tests/contract
```

---

## Step 3: Install Dependencies (5 minutes)

### 3.1 Create requirements.txt

```txt
google-auth==2.27.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
google-api-python-client==2.116.0
python-dotenv==1.0.0
mcp==0.9.0
pytest==8.0.0
pytest-asyncio==0.23.0
```

### 3.2 Install Packages

```bash
pip install -r requirements.txt
```

---

## Step 4: Initial OAuth2 Authentication (5 minutes)

### 4.1 Create Authentication Script

Create `scripts/authenticate_gmail.py`:

```python
#!/usr/bin/env python3
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

def authenticate():
    creds = None
    token_path = 'credentials/gmail_token.pickle'

    # Load existing token if available
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Load client secrets from .env
            from dotenv import load_dotenv
            load_dotenv()

            client_config = {
                "installed": {
                    "client_id": os.getenv("GMAIL_CLIENT_ID"),
                    "client_secret": os.getenv("GMAIL_CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"]
                }
            }

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    print(f"✅ Authentication successful! Token saved to {token_path}")
    return creds

if __name__ == '__main__':
    authenticate()
```

### 4.2 Run Authentication

```bash
python scripts/authenticate_gmail.py
```

This will:
1. Open browser for Google OAuth consent
2. Ask you to authorize the application
3. Save token to `credentials/gmail_token.pickle`

---

## Step 5: Test Gmail API Connection (5 minutes)

### 5.1 Create Test Script

Create `scripts/test_gmail_connection.py`:

```python
#!/usr/bin/env python3
import pickle
from googleapiclient.discovery import build

def test_connection():
    with open('credentials/gmail_token.pickle', 'rb') as token:
        creds = pickle.load(token)

    service = build('gmail', 'v1', credentials=creds)

    # Test: Get user profile
    profile = service.users().getProfile(userId='me').execute()
    print(f"✅ Connected to Gmail: {profile['emailAddress']}")

    # Test: List recent messages
    results = service.users().messages().list(userId='me', maxResults=5).execute()
    messages = results.get('messages', [])
    print(f"✅ Found {len(messages)} recent messages")

    return True

if __name__ == '__main__':
    test_connection()
```

### 5.2 Run Test

```bash
python scripts/test_gmail_connection.py
```

Expected output:
```
✅ Connected to Gmail: your-email@gmail.com
✅ Found 5 recent messages
```

---

## Step 6: Configure Company Handbook (5 minutes)

### 6.1 Add Client Domains

Edit `Company_Handbook.md` and add:

```markdown
## Clients

Known client domains for email classification:

- example.com
- client-company.com
- partner-org.net

Emails from these domains are automatically classified as actionable.
```

### 6.2 Add Auto-Approval Rules (Optional)

```markdown
## Email Auto-Approval Rules

Auto-approve email replies for:
- Known clients (listed above)
- Subject contains: "Thank you", "Received", "Confirmed"
- Body length < 200 characters

Always require approval for:
- New contacts (not in client list)
- Attachments > 1MB
- Bulk emails (>5 recipients)
```

---

## Step 7: Start Gmail Watcher (5 minutes)

### 7.1 Configure PM2

Create `ecosystem.config.js`:

```javascript
module.exports = {
  apps: [{
    name: 'gmail-watcher',
    script: 'src/watchers/gmail_watcher.py',
    interpreter: 'python3',
    autorestart: true,
    watch: false,
    max_restarts: 10,
    min_uptime: '10s',
    restart_delay: 5000,
    env: {
      PYTHONUNBUFFERED: '1'
    }
  }]
};
```

### 7.2 Start Watcher

```bash
pm2 start ecosystem.config.js
pm2 logs gmail-watcher
```

### 7.3 Verify Watcher is Running

```bash
pm2 status
```

Expected output:
```
┌─────┬──────────────────┬─────────┬─────────┬──────────┐
│ id  │ name             │ status  │ restart │ uptime   │
├─────┼──────────────────┼─────────┼─────────┼──────────┤
│ 0   │ gmail-watcher    │ online  │ 0       │ 10s      │
└─────┴──────────────────┴─────────┴─────────┴──────────┘
```

---

## Step 8: Configure MCP Server (5 minutes)

### 8.1 Add to mcp.json

Edit `mcp.json` (or create if doesn't exist):

```json
{
  "mcpServers": {
    "gmail": {
      "command": "python",
      "args": ["mcp_servers/gmail/server.py"],
      "env": {
        "GMAIL_CLIENT_ID": "${GMAIL_CLIENT_ID}",
        "GMAIL_CLIENT_SECRET": "${GMAIL_CLIENT_SECRET}",
        "DRY_RUN": "${DRY_RUN}"
      }
    }
  }
}
```

### 8.2 Test MCP Server

```bash
# Test in dry-run mode
DRY_RUN=true python mcp_servers/gmail/server.py
```

---

## Step 9: End-to-End Test (10 minutes)

### 9.1 Send Test Email to Yourself

1. Send an email to your monitored Gmail account
2. Mark it as "Important" in Gmail
3. Wait 2-5 minutes for watcher to detect it

### 9.2 Verify Action File Created

```bash
ls -la Needs_Action/
```

Expected: `EMAIL_<message_id>_<timestamp>.md` file created

### 9.3 Test Email Classification

Send these test emails to verify filtering:
1. From `noreply@example.com` → Should be labeled "non-actionable", no action file
2. Subject: "Newsletter: Weekly Update" → Should be labeled "non-actionable"
3. From known client domain → Should create action file

### 9.4 Test Email Sending (Dry Run)

1. Create a draft in `/Pending_Approval/`:
   ```markdown
   ---
   to: test@example.com
   subject: Test Email
   ---

   This is a test email body.
   ```

2. Move to `/Approved/`
3. Verify MCP server logs show dry-run send

---

## Troubleshooting

### Watcher Not Starting

**Symptom**: PM2 shows status "errored"

**Solutions**:
1. Check logs: `pm2 logs gmail-watcher --lines 50`
2. Verify Python path: `which python3`
3. Check credentials exist: `ls credentials/gmail_token.pickle`
4. Test manually: `python src/watchers/gmail_watcher.py`

### Authentication Errors

**Symptom**: "Invalid credentials" or "Token expired"

**Solutions**:
1. Re-run authentication: `python scripts/authenticate_gmail.py`
2. Verify .env has correct CLIENT_ID and CLIENT_SECRET
3. Check token file exists: `ls credentials/gmail_token.pickle`
4. Revoke and re-authorize in Google Account settings

### No Emails Detected

**Symptom**: Watcher running but no action files created

**Solutions**:
1. Verify emails are marked "Important" in Gmail
2. Check watcher logs: `pm2 logs gmail-watcher`
3. Verify state file: `cat config/gmail_watcher_state.json`
4. Test Gmail API connection: `python scripts/test_gmail_connection.py`

### Rate Limit Errors

**Symptom**: "RATE_LIMIT_EXCEEDED" in logs

**Solutions**:
1. Wait for rate limit window to expire (check logs for retry time)
2. Reduce check frequency in watcher config
3. Verify rate limits in .env are correct

---

## Monitoring & Maintenance

### Daily Checks

```bash
# Check watcher status
pm2 status

# View recent logs
pm2 logs gmail-watcher --lines 20

# Check classification stats
cat config/gmail_watcher_state.json | jq '.classification_stats'
```

### Weekly Maintenance

1. Review `/Logs/` for errors or anomalies
2. Check classification accuracy (false positives/negatives)
3. Update Company_Handbook.md with new client domains
4. Rotate old logs (keep last 30 days)

### Monthly Tasks

1. Review OAuth2 token expiry (auto-refreshes, but verify)
2. Audit email sending logs for patterns
3. Update classification rules based on feedback
4. Check PM2 restart count (should be low)

---

## Next Steps

After successful setup:

1. **Production Mode**: Set `DRY_RUN=false` in .env
2. **Monitoring**: Set up alerts for watcher crashes
3. **Optimization**: Tune classification rules based on accuracy
4. **Integration**: Connect with orchestrator for full automation
5. **Testing**: Run full test suite (`pytest tests/`)

---

## Reference Commands

```bash
# Watcher management
pm2 start gmail-watcher
pm2 stop gmail-watcher
pm2 restart gmail-watcher
pm2 logs gmail-watcher
pm2 delete gmail-watcher

# Testing
pytest tests/unit/
pytest tests/integration/
pytest tests/contract/

# Debugging
python -m pdb src/watchers/gmail_watcher.py
tail -f Logs/$(date +%Y-%m-%d).md

# State inspection
cat config/gmail_watcher_state.json | jq '.'
ls -lah Needs_Action/
ls -lah Approved/
```

---

## Support

- **Documentation**: See `specs/001-gmail-integration/` for detailed specs
- **Issues**: Check logs in `/Logs/` and PM2 logs
- **Constitution**: Review `.specify/memory/constitution.md` for principles
