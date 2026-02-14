# Research: Gmail Integration for AI Employee

**Feature**: 001-gmail-integration
**Date**: 2026-02-12
**Purpose**: Document technical research, decisions, and best practices for Gmail watcher and MCP server implementation

## Research Topics

### 1. Gmail API OAuth2 Authentication

**Decision**: Use OAuth2 with offline access and automatic token refresh

**Rationale**:
- Gmail API requires OAuth2 for user data access (no API keys for reading emails)
- Offline access scope allows daemon to run without user interaction
- Refresh tokens enable long-running watcher without re-authentication
- Google's official python client (google-api-python-client) provides built-in token refresh

**Implementation Pattern**:
```python
# Load credentials from .env (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET)
# Store tokens in credentials/gmail_token.json (gitignored)
# Use google.auth.transport.requests.Request for automatic refresh
# Scopes: gmail.readonly (detection), gmail.send (sending), gmail.modify (labeling)
```

**Alternatives Considered**:
- Service accounts: Rejected - requires Google Workspace domain-wide delegation, not suitable for personal Gmail
- API keys: Rejected - not supported for Gmail API user data access
- Manual token refresh: Rejected - adds complexity, built-in refresh is more reliable

**References**:
- Google OAuth2 documentation: https://developers.google.com/identity/protocols/oauth2
- Gmail API Python quickstart: https://developers.google.com/gmail/api/quickstart/python

---

### 2. Email Classification Algorithm

**Decision**: Rule-based classification with three-tier filtering (domain patterns → keywords → handbook lookup)

**Rationale**:
- Deterministic and explainable (users can understand why emails are filtered)
- No ML training required (works immediately without labeled data)
- Low latency (rule evaluation is fast, <10ms per email)
- Easy to customize via Company_Handbook.md

**Classification Rules** (applied in order):

1. **Domain Pattern Matching** (non-actionable if matches):
   - `noreply@*`, `no-reply@*`, `notifications@*`, `donotreply@*`
   - `*@facebookmail.com`, `*@linkedin.com`, `*@twitter.com` (platform notifications)

2. **Subject Keyword Matching** (non-actionable if contains):
   - `unsubscribe`, `promotional`, `sponsored`, `newsletter`, `marketing`
   - Case-insensitive matching with word boundaries

3. **Company Handbook Lookup** (actionable if matches):
   - Parse Company_Handbook.md for known client domains
   - Format: `## Clients` section with domain list
   - If sender domain in list → actionable

4. **Default Behavior**:
   - If no negative signals detected → classify as actionable (conservative)
   - Log uncertainty score for manual review

**Alternatives Considered**:
- ML-based classification (Naive Bayes, transformers): Rejected - requires training data, adds complexity, harder to debug
- Gmail filters only: Rejected - insufficient control, can't integrate with Company_Handbook.md
- LLM-based classification: Rejected - high latency (200-500ms), API costs, requires external service

**Edge Cases Handled**:
- Unknown senders: Apply domain + keyword filters, default to actionable
- Missing handbook: Continue with domain + keyword filters only
- Uncertain classification: Default to actionable, log for review

---

### 3. MCP Server Implementation Pattern

**Decision**: Use MCP SDK for Python with JSON-RPC protocol and tool-based architecture

**Rationale**:
- MCP protocol is standardized for AI-to-external-action communication
- Tool-based architecture allows Claude to discover and invoke send_email capability
- JSON-RPC provides structured request/response with error handling
- SDK handles protocol details (handshake, tool registration, parameter validation)

**Tool Schema**:
```json
{
  "name": "send_email",
  "description": "Send an email via Gmail API with approval workflow",
  "parameters": {
    "to": {"type": "string", "required": true, "description": "Recipient email address"},
    "subject": {"type": "string", "required": true, "description": "Email subject line"},
    "body": {"type": "string", "required": true, "description": "Email body content (plain text or HTML)"},
    "dry_run": {"type": "boolean", "required": false, "default": false, "description": "If true, simulate send without actual delivery"}
  }
}
```

**Implementation Details**:
- Server listens on stdio (standard MCP pattern)
- Validates email addresses (RFC 5322 format)
- Respects DRY_RUN environment variable (overrides parameter)
- Rate limiting: 20 emails/hour using token bucket algorithm
- Error responses include actionable messages for Claude

**Alternatives Considered**:
- REST API: Rejected - requires network setup, authentication complexity, not standard for local AI actions
- Direct function calls: Rejected - no protocol standardization, harder to integrate with Claude
- gRPC: Rejected - overkill for local communication, MCP is simpler

**References**:
- MCP protocol specification: https://modelcontextprotocol.io/
- MCP Python SDK: https://github.com/anthropics/mcp-python

---

### 4. Python Daemon Best Practices

**Decision**: Use PM2 for process management with graceful shutdown and state persistence

**Rationale**:
- PM2 provides automatic restart on crashes (constitution §7 requirement)
- Supports log rotation and monitoring out of the box
- Graceful shutdown allows watcher to save state before exit
- Cross-platform (works on Linux, macOS, Windows)

**Implementation Pattern**:
```python
# Watcher main loop
def run(self):
    signal.signal(signal.SIGTERM, self._handle_shutdown)
    signal.signal(signal.SIGINT, self._handle_shutdown)

    while not self._shutdown_requested:
        try:
            self.check_for_updates()
            time.sleep(self.check_interval)
        except Exception as e:
            self.logger.error(f"Error in watcher loop: {e}")
            time.sleep(60)  # Back off on errors

    self._save_state()  # Persist before exit

def _handle_shutdown(self, signum, frame):
    self._shutdown_requested = True
```

**PM2 Configuration**:
```json
{
  "apps": [{
    "name": "gmail-watcher",
    "script": "src/watchers/gmail_watcher.py",
    "interpreter": "python3",
    "autorestart": true,
    "max_restarts": 10,
    "min_uptime": "10s",
    "restart_delay": 5000
  }]
}
```

**Alternatives Considered**:
- systemd: Rejected - Linux-only, more complex configuration
- supervisord: Rejected - requires separate installation, PM2 is more modern
- Docker: Rejected - overkill for local daemon, adds deployment complexity

---

### 5. Rate Limiting Strategy

**Decision**: Token bucket algorithm with per-hour and per-day limits

**Rationale**:
- Token bucket allows burst traffic while enforcing average rate
- Separate buckets for email sending (20/hour) and API calls (100/day)
- Graceful degradation: queue requests when limit reached, process when tokens available
- Prevents Gmail API quota exceeded errors (constitution §9 requirement)

**Implementation**:
```python
class RateLimiter:
    def __init__(self, rate_per_hour, rate_per_day):
        self.hourly_bucket = TokenBucket(rate_per_hour, refill_rate=rate_per_hour/3600)
        self.daily_bucket = TokenBucket(rate_per_day, refill_rate=rate_per_day/86400)

    def acquire(self, tokens=1):
        if not self.hourly_bucket.consume(tokens):
            raise RateLimitError("Hourly limit exceeded")
        if not self.daily_bucket.consume(tokens):
            raise RateLimitError("Daily limit exceeded")
        return True
```

**Backoff Strategy**:
- On rate limit hit: log warning, queue pending requests
- Retry after calculated wait time (time until next token available)
- Exponential backoff for API errors (1s, 2s, 4s, 8s, max 60s)

**Alternatives Considered**:
- Fixed window: Rejected - allows burst at window boundaries (e.g., 20 emails at 11:59, 20 more at 12:01)
- Leaky bucket: Rejected - doesn't allow bursts, token bucket is more flexible
- No rate limiting: Rejected - violates Gmail API terms, risks quota exceeded errors

---

### 6. State Persistence Pattern

**Decision**: JSON file with atomic writes and file locking

**Rationale**:
- Simple and human-readable (easy to debug and manually edit if needed)
- Atomic writes prevent corruption on crashes (write to temp file, then rename)
- File locking prevents race conditions with multiple watcher instances
- No external dependencies (no database required)

**State Schema**:
```json
{
  "last_checked_message_id": "18d4f2a3b5c6d7e8",
  "last_check_timestamp": "2026-02-12T10:30:00Z",
  "processed_message_ids": [
    "18d4f2a3b5c6d7e8",
    "18d4f2a3b5c6d7e9"
  ],
  "classification_stats": {
    "total_processed": 150,
    "actionable": 45,
    "non_actionable": 105
  }
}
```

**Implementation Pattern**:
```python
import fcntl
import json
import tempfile

def save_state(self, state):
    with open(self.state_file, 'r+') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock

        # Write to temp file first
        temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(self.state_file))
        with os.fdopen(temp_fd, 'w') as temp_f:
            json.dump(state, temp_f, indent=2)

        # Atomic rename
        os.rename(temp_path, self.state_file)

        fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Release lock
```

**Alternatives Considered**:
- SQLite: Rejected - overkill for simple key-value state, adds dependency
- Pickle: Rejected - not human-readable, security concerns with untrusted data
- In-memory only: Rejected - loses state on crashes, violates constitution §4 requirement

---

## Summary of Key Decisions

| Component | Technology/Pattern | Rationale |
|-----------|-------------------|-----------|
| Authentication | OAuth2 with offline access | Required by Gmail API, enables daemon operation |
| Classification | Rule-based (domain → keyword → handbook) | Deterministic, explainable, no training required |
| MCP Server | MCP SDK for Python with JSON-RPC | Standardized protocol, tool discovery, error handling |
| Daemon Management | PM2 with graceful shutdown | Auto-restart, log rotation, cross-platform |
| Rate Limiting | Token bucket (20/hour, 100/day) | Prevents quota errors, allows bursts |
| State Persistence | JSON with atomic writes + file locking | Simple, human-readable, crash-safe |

**Next Steps**: Proceed to Phase 1 (Design & Contracts) to create data-model.md and contracts/
