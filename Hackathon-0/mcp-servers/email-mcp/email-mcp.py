"""
Gmail MCP Server
================
Provides Claude with full Gmail capability via the MCP protocol (stdio).

Tools
-----
  send_email        — compose and send an email
  list_emails       — list emails matching a Gmail query
  read_email        — fetch full content of a single email
  get_thread        — fetch all messages in a conversation thread
  search_emails     — search Gmail with an advanced query
  create_draft      — save a draft without sending
  mark_as_read      — mark one or more emails as read
  apply_label       — add a Gmail label to an email
  get_email_stats   — show watcher classification statistics

Configure in mcp.json:
  {
    "mcpServers": {
      "gmail": {
        "command": "python",
        "args": ["mcp-servers/email-mcp/email-mcp.py"]
      }
    }
  }
"""

import os
import re
import sys
import time
import pickle
import base64
import logging
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from mcp.server.fastmcp import FastMCP

# ── Bootstrap ─────────────────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).parent.parent.parent  # Hackathon-0/
load_dotenv(_BASE_DIR / ".env")

TOKEN_PATH  = _BASE_DIR / "config" / "gmail_token.pickle"
STATE_PATH  = _BASE_DIR / "config" / "gmail_watcher_state.json"

# Log to stderr — stdout is reserved for MCP JSON-RPC
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("email-mcp")

# ── Gmail service ─────────────────────────────────────────────────────────────

def _load_service():
    """Return an authenticated Gmail API service, refreshing the token if needed."""
    if not TOKEN_PATH.exists():
        raise RuntimeError(
            f"Token not found at {TOKEN_PATH}. "
            "Run 'python scripts/authenticate_gmail.py' first."
        )
    with open(TOKEN_PATH, "rb") as fh:
        creds = pickle.load(fh)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, "wb") as fh:
                pickle.dump(creds, fh)
        else:
            raise RuntimeError(
                "Credentials invalid — re-run 'python scripts/authenticate_gmail.py'."
            )

    return build("gmail", "v1", credentials=creds)


# ── Validation helpers ────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _valid_email(addr: str) -> bool:
    return bool(_EMAIL_RE.match(addr.strip()))


def _parse_headers(payload: dict) -> dict:
    """Return header dict (lowercase keys) from a message payload."""
    return {
        h["name"].lower(): h["value"]
        for h in payload.get("headers", [])
    }


# ── Token-bucket rate limiter ─────────────────────────────────────────────────

class _TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity  = capacity
        self.tokens    = float(capacity)
        self.rate      = refill_rate
        self._last     = time.monotonic()

    def consume(self) -> bool:
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self._last) * self.rate)
        self._last  = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class _RateLimiter:
    def __init__(self, hourly: int = 20, daily: int = 100):
        self._hourly = _TokenBucket(hourly, hourly / 3600)
        self._daily  = _TokenBucket(daily,  daily  / 86400)

    def acquire(self) -> bool:
        if not self._hourly.consume():
            return False
        if not self._daily.consume():
            self._hourly.tokens += 1   # refund
            return False
        return True


_rate_limiter = _RateLimiter(
    hourly=int(os.getenv("GMAIL_RATE_LIMIT_HOURLY", "20")),
    daily =int(os.getenv("GMAIL_RATE_LIMIT_DAILY",  "100")),
)

# ── Retry helper ──────────────────────────────────────────────────────────────

_RETRYABLE = (429, 500, 502, 503, 504)


def _with_retry(fn, max_retries: int = 3):
    """Call fn(); retry with exponential backoff on transient errors."""
    backoff = 1
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except HttpError as exc:
            if exc.resp.status in _RETRYABLE and attempt < max_retries:
                logger.warning(f"Retryable error (attempt {attempt}): {exc}. Retry in {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            raise
        except Exception as exc:
            if attempt < max_retries:
                logger.warning(f"Network error (attempt {attempt}): {exc}. Retry in {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            raise


# ── MCP server ────────────────────────────────────────────────────────────────

mcp = FastMCP("gmail")

# ─────────────────────────────────────────────────────────────────────────────
# TOOL: send_email
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def send_email(to: str, subject: str, body: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Send an email via Gmail.

    Args:
        to:      Recipient address (RFC 5322). Required.
        subject: Subject line, max 500 chars. Required.
        body:    Plain-text body, max 50 KB. Required.
        dry_run: If True, simulate without sending.

    Returns: {success, message_id, timestamp, dry_run, error}
    """
    ts     = datetime.now(timezone.utc).isoformat()
    is_dry = dry_run or os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")

    def _err(code: str) -> Dict[str, Any]:
        return {"success": False, "message_id": None, "timestamp": ts,
                "dry_run": is_dry, "error": code}

    if not to or not to.strip():
        return _err("INVALID_EMAIL: 'to' is required")
    if not _valid_email(to):
        return _err(f"INVALID_EMAIL: '{to}' is not a valid address")
    if not subject or not subject.strip():
        return _err("INVALID_EMAIL: 'subject' is required")
    if len(subject) > 500:
        return _err(f"INVALID_EMAIL: subject exceeds 500 chars ({len(subject)})")
    if not body or not body.strip():
        return _err("INVALID_EMAIL: 'body' is required")
    if len(body.encode()) > 50 * 1024:
        return _err("INVALID_EMAIL: body exceeds 50 KB")

    if not _rate_limiter.acquire():
        logger.warning(f"Rate limit exceeded for send to {to}")
        return _err("RATE_LIMIT_EXCEEDED: retry later")

    if is_dry:
        logger.info(f"DRY RUN | to={to} | subject={subject[:60]}")
        return {"success": True, "message_id": f"dry_{int(time.time())}",
                "timestamp": ts, "dry_run": True, "error": None}

    try:
        service = _load_service()
    except RuntimeError as exc:
        return _err(f"AUTHENTICATION_FAILED: {exc}")

    try:
        def _send():
            mime = MIMEMultipart()
            mime["to"]      = to
            mime["subject"] = subject
            mime.attach(MIMEText(body, "plain"))
            raw    = base64.urlsafe_b64encode(mime.as_bytes()).decode()
            return service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()

        result = _with_retry(_send)
        logger.info(f"Email sent | id={result.get('id')} | to={to}")
        return {"success": True, "message_id": result.get("id"),
                "timestamp": ts, "dry_run": False, "error": None}

    except HttpError as exc:
        return _err(f"GMAIL_API_ERROR: {exc}")
    except Exception as exc:
        return _err(f"NETWORK_ERROR: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: list_emails
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_emails(
    query: str = "is:unread is:important",
    max_results: int = 20,
) -> Dict[str, Any]:
    """
    List emails matching a Gmail search query.

    Args:
        query:       Gmail search query (default: unread+important emails).
                     Examples: "from:boss@co.com", "subject:invoice", "is:unread"
        max_results: Max emails to return (1–100, default 20).

    Returns: {emails: [{id, thread_id, from, subject, date, snippet}], count, error}
    """
    max_results = max(1, min(100, max_results))

    try:
        service = _load_service()

        def _list():
            return service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()

        result   = _with_retry(_list)
        refs     = result.get("messages", [])
        emails   = []

        for ref in refs:
            try:
                def _get(mid=ref["id"]):
                    return service.users().messages().get(
                        userId="me", id=mid,
                        format="metadata",
                        metadataHeaders=["From", "Subject", "Date"],
                    ).execute()

                msg  = _with_retry(_get)
                hdrs = _parse_headers(msg.get("payload", {}))
                emails.append({
                    "id":        msg["id"],
                    "thread_id": msg.get("threadId", ""),
                    "from":      hdrs.get("from", ""),
                    "subject":   hdrs.get("subject", "(no subject)"),
                    "date":      hdrs.get("date", ""),
                    "snippet":   msg.get("snippet", "")[:200],
                })
            except Exception as exc:
                logger.warning(f"Could not fetch metadata for {ref['id']}: {exc}")

        return {"emails": emails, "count": len(emails), "error": None}

    except RuntimeError as exc:
        return {"emails": [], "count": 0, "error": f"AUTHENTICATION_FAILED: {exc}"}
    except HttpError as exc:
        return {"emails": [], "count": 0, "error": f"GMAIL_API_ERROR: {exc}"}
    except Exception as exc:
        return {"emails": [], "count": 0, "error": f"ERROR: {exc}"}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: read_email
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def read_email(message_id: str) -> Dict[str, Any]:
    """
    Fetch the full content of a single email.

    Args:
        message_id: Gmail message ID (from list_emails or search_emails).

    Returns: {id, thread_id, from, to, subject, date, body, labels, error}
    """
    if not message_id or not message_id.strip():
        return {"error": "INVALID_INPUT: message_id is required"}

    try:
        service = _load_service()

        def _get():
            return service.users().messages().get(
                userId="me", id=message_id, format="full"
            ).execute()

        msg  = _with_retry(_get)
        hdrs = _parse_headers(msg.get("payload", {}))

        # Extract plain-text body
        body = _extract_body(msg.get("payload", {}))

        return {
            "id":        msg["id"],
            "thread_id": msg.get("threadId", ""),
            "from":      hdrs.get("from", ""),
            "to":        hdrs.get("to", ""),
            "subject":   hdrs.get("subject", "(no subject)"),
            "date":      hdrs.get("date", ""),
            "body":      body,
            "labels":    msg.get("labelIds", []),
            "error":     None,
        }

    except RuntimeError as exc:
        return {"error": f"AUTHENTICATION_FAILED: {exc}"}
    except HttpError as exc:
        return {"error": f"GMAIL_API_ERROR: {exc}"}
    except Exception as exc:
        return {"error": f"ERROR: {exc}"}


def _extract_body(payload: dict) -> str:
    """Recursively extract the plain-text body from a message payload."""
    mime = payload.get("mimeType", "")

    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        text = _extract_body(part)
        if text:
            return text

    return payload.get("snippet", "")


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_thread
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_thread(thread_id: str) -> Dict[str, Any]:
    """
    Fetch all messages in an email conversation thread.

    Args:
        thread_id: Gmail thread ID (from list_emails or read_email).

    Returns: {thread_id, message_count, messages: [{id, from, date, snippet}], error}
    """
    if not thread_id or not thread_id.strip():
        return {"error": "INVALID_INPUT: thread_id is required"}

    try:
        service = _load_service()

        def _get():
            return service.users().threads().get(
                userId="me", id=thread_id,
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()

        thread   = _with_retry(_get)
        messages = []

        for msg in thread.get("messages", []):
            hdrs = _parse_headers(msg.get("payload", {}))
            messages.append({
                "id":      msg["id"],
                "from":    hdrs.get("from", ""),
                "subject": hdrs.get("subject", "(no subject)"),
                "date":    hdrs.get("date", ""),
                "snippet": msg.get("snippet", "")[:200],
            })

        return {
            "thread_id":     thread_id,
            "message_count": len(messages),
            "messages":      messages,
            "error":         None,
        }

    except RuntimeError as exc:
        return {"error": f"AUTHENTICATION_FAILED: {exc}"}
    except HttpError as exc:
        return {"error": f"GMAIL_API_ERROR: {exc}"}
    except Exception as exc:
        return {"error": f"ERROR: {exc}"}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: search_emails
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def search_emails(query: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Search Gmail with an advanced query and return matching emails.

    Args:
        query:       Gmail search syntax. Examples:
                       "from:alice@co.com subject:invoice after:2024/01/01"
                       "has:attachment larger:5M"
                       "label:actionable"
        max_results: Max results to return (1–50, default 10).

    Returns: {emails: [{id, thread_id, from, subject, date, snippet}], count, query, error}
    """
    if not query or not query.strip():
        return {"emails": [], "count": 0, "query": query,
                "error": "INVALID_INPUT: query is required"}

    max_results = max(1, min(50, max_results))

    try:
        service = _load_service()

        def _search():
            return service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()

        result = _with_retry(_search)
        refs   = result.get("messages", [])
        emails = []

        for ref in refs:
            try:
                def _get(mid=ref["id"]):
                    return service.users().messages().get(
                        userId="me", id=mid,
                        format="metadata",
                        metadataHeaders=["From", "Subject", "Date"],
                    ).execute()

                msg  = _with_retry(_get)
                hdrs = _parse_headers(msg.get("payload", {}))
                emails.append({
                    "id":        msg["id"],
                    "thread_id": msg.get("threadId", ""),
                    "from":      hdrs.get("from", ""),
                    "subject":   hdrs.get("subject", "(no subject)"),
                    "date":      hdrs.get("date", ""),
                    "snippet":   msg.get("snippet", "")[:200],
                })
            except Exception as exc:
                logger.warning(f"Skipping {ref['id']}: {exc}")

        return {"emails": emails, "count": len(emails), "query": query, "error": None}

    except RuntimeError as exc:
        return {"emails": [], "count": 0, "query": query,
                "error": f"AUTHENTICATION_FAILED: {exc}"}
    except HttpError as exc:
        return {"emails": [], "count": 0, "query": query,
                "error": f"GMAIL_API_ERROR: {exc}"}
    except Exception as exc:
        return {"emails": [], "count": 0, "query": query, "error": f"ERROR: {exc}"}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: create_draft
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def create_draft(to: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Save an email as a Gmail draft (does NOT send).

    Args:
        to:      Recipient address. Required.
        subject: Subject line, max 500 chars. Required.
        body:    Plain-text body. Required.

    Returns: {success, draft_id, timestamp, error}
    """
    ts = datetime.now(timezone.utc).isoformat()

    if not to or not _valid_email(to):
        return {"success": False, "draft_id": None, "timestamp": ts,
                "error": f"INVALID_EMAIL: '{to}' is not valid"}
    if not subject or not subject.strip():
        return {"success": False, "draft_id": None, "timestamp": ts,
                "error": "INVALID_INPUT: subject is required"}
    if not body or not body.strip():
        return {"success": False, "draft_id": None, "timestamp": ts,
                "error": "INVALID_INPUT: body is required"}

    try:
        service = _load_service()

        def _draft():
            mime = MIMEMultipart()
            mime["to"]      = to
            mime["subject"] = subject
            mime.attach(MIMEText(body, "plain"))
            raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
            return service.users().drafts().create(
                userId="me", body={"message": {"raw": raw}}
            ).execute()

        result = _with_retry(_draft)
        draft_id = result.get("id", "")
        logger.info(f"Draft created | id={draft_id} | to={to}")
        return {"success": True, "draft_id": draft_id, "timestamp": ts, "error": None}

    except RuntimeError as exc:
        return {"success": False, "draft_id": None, "timestamp": ts,
                "error": f"AUTHENTICATION_FAILED: {exc}"}
    except HttpError as exc:
        return {"success": False, "draft_id": None, "timestamp": ts,
                "error": f"GMAIL_API_ERROR: {exc}"}
    except Exception as exc:
        return {"success": False, "draft_id": None, "timestamp": ts,
                "error": f"ERROR: {exc}"}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: mark_as_read
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def mark_as_read(message_ids: List[str]) -> Dict[str, Any]:
    """
    Mark one or more emails as read (removes UNREAD label).

    Args:
        message_ids: List of Gmail message IDs.

    Returns: {marked: [ids], failed: [ids], error}
    """
    if not message_ids:
        return {"marked": [], "failed": [], "error": "INVALID_INPUT: message_ids list is empty"}

    try:
        service = _load_service()
        marked, failed = [], []

        for mid in message_ids:
            try:
                def _mark(m=mid):
                    return service.users().messages().modify(
                        userId="me", id=m,
                        body={"removeLabelIds": ["UNREAD"]},
                    ).execute()

                _with_retry(_mark)
                marked.append(mid)
            except Exception as exc:
                logger.warning(f"Could not mark {mid} as read: {exc}")
                failed.append(mid)

        logger.info(f"Marked {len(marked)} emails as read")
        return {"marked": marked, "failed": failed, "error": None}

    except RuntimeError as exc:
        return {"marked": [], "failed": message_ids,
                "error": f"AUTHENTICATION_FAILED: {exc}"}
    except Exception as exc:
        return {"marked": [], "failed": message_ids, "error": f"ERROR: {exc}"}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: apply_label
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def apply_label(message_id: str, label_name: str) -> Dict[str, Any]:
    """
    Add a Gmail label to an email. Creates the label if it doesn't exist.

    Args:
        message_id: Gmail message ID.
        label_name: Label to apply (e.g. "actionable", "follow-up", "urgent").

    Returns: {success, message_id, label_name, label_id, error}
    """
    if not message_id or not message_id.strip():
        return {"success": False, "error": "INVALID_INPUT: message_id is required"}
    if not label_name or not label_name.strip():
        return {"success": False, "error": "INVALID_INPUT: label_name is required"}

    try:
        service = _load_service()

        # Get or create the label
        label_id = _get_or_create_label(service, label_name)
        if not label_id:
            return {"success": False, "message_id": message_id,
                    "label_name": label_name, "label_id": None,
                    "error": "GMAIL_API_ERROR: could not get or create label"}

        def _apply():
            return service.users().messages().modify(
                userId="me", id=message_id,
                body={"addLabelIds": [label_id]},
            ).execute()

        _with_retry(_apply)
        logger.info(f"Label '{label_name}' applied to {message_id}")
        return {"success": True, "message_id": message_id,
                "label_name": label_name, "label_id": label_id, "error": None}

    except RuntimeError as exc:
        return {"success": False, "message_id": message_id,
                "label_name": label_name, "label_id": None,
                "error": f"AUTHENTICATION_FAILED: {exc}"}
    except HttpError as exc:
        return {"success": False, "message_id": message_id,
                "label_name": label_name, "label_id": None,
                "error": f"GMAIL_API_ERROR: {exc}"}
    except Exception as exc:
        return {"success": False, "message_id": message_id,
                "label_name": label_name, "label_id": None, "error": f"ERROR: {exc}"}


_label_cache: Dict[str, str] = {}


def _get_or_create_label(service, name: str) -> str:
    """Return label ID for name, creating it if absent. Uses in-process cache."""
    if name in _label_cache:
        return _label_cache[name]

    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for lbl in labels:
        if lbl["name"].lower() == name.lower():
            _label_cache[name] = lbl["id"]
            return lbl["id"]

    new_lbl = service.users().labels().create(
        userId="me", body={"name": name, "labelListVisibility": "labelShow"}
    ).execute()
    _label_cache[name] = new_lbl["id"]
    return new_lbl["id"]


# ─────────────────────────────────────────────────────────────────────────────
# TOOL: get_email_stats
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_email_stats() -> Dict[str, Any]:
    """
    Return the Gmail watcher's classification statistics from its state file.

    Returns:
        {
          last_check: ISO timestamp,
          total_processed: int,
          actionable: int,
          non_actionable: int,
          domain_pattern_filtered: int,
          keyword_filtered: int,
          handbook_matched: int,
          default_actionable: int,
          error: str | None
        }
    """
    import json

    if not STATE_PATH.exists():
        return {
            "last_check": None,
            "total_processed": 0,
            "actionable": 0,
            "non_actionable": 0,
            "domain_pattern_filtered": 0,
            "keyword_filtered": 0,
            "handbook_matched": 0,
            "default_actionable": 0,
            "error": "State file not found — watcher has not run yet.",
        }

    try:
        with open(STATE_PATH) as fh:
            state = json.load(fh)

        stats = state.get("classification_stats", {})
        return {
            "last_check":             state.get("last_check_timestamp"),
            "total_processed":        stats.get("total_processed", 0),
            "actionable":             stats.get("actionable", 0),
            "non_actionable":         stats.get("non_actionable", 0),
            "domain_pattern_filtered":stats.get("domain_pattern_filtered", 0),
            "keyword_filtered":       stats.get("keyword_filtered", 0),
            "handbook_matched":       stats.get("handbook_matched", 0),
            "default_actionable":     stats.get("default_actionable", 0),
            "error":                  None,
        }

    except Exception as exc:
        return {"error": f"Could not read state file: {exc}"}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Gmail MCP Server starting (9 tools registered)…")
    mcp.run(transport="stdio")
