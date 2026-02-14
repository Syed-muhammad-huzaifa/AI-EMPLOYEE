"""Gmail watcher - monitors Gmail inbox, classifies emails, creates action files."""

import os
import re
import sys
import json
import time
import signal
import pickle
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Ensure Hackathon-0 root is on path for imports
_BASE_DIR = Path(__file__).parent.parent.parent  # Hackathon-0/
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

from src.watchers.base_watcher import BaseWatcher

# ── Classification rules ────────────────────────────────────────────────────

NON_ACTIONABLE_DOMAIN_PATTERNS = [
    re.compile(r"^noreply@", re.IGNORECASE),
    re.compile(r"^no-reply@", re.IGNORECASE),
    re.compile(r"^notifications@", re.IGNORECASE),
    re.compile(r"^donotreply@", re.IGNORECASE),
    re.compile(r"@facebookmail\.com$", re.IGNORECASE),
    re.compile(r"@linkedin\.com$", re.IGNORECASE),
    re.compile(r"@twitter\.com$", re.IGNORECASE),
]

NON_ACTIONABLE_KEYWORDS = [
    "unsubscribe",
    "promotional",
    "sponsored",
    "newsletter",
    "marketing",
]

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

# ── GmailWatcher ────────────────────────────────────────────────────────────


class GmailWatcher(BaseWatcher):
    """
    Extends BaseWatcher to monitor Gmail inbox.

    - Fetches unread important emails every 2 minutes (check_interval=120)
    - Classifies each email as actionable / non-actionable using three-tier rules:
        1. Sender domain pattern matching
        2. Subject keyword matching
        3. Company_Handbook.md client domain lookup
        4. Default: actionable (conservative)
    - Labels emails in Gmail accordingly
    - Creates EMAIL_{msg_id}_{ts}.md action files in Needs_Action/ for actionable only
    - Persists state to config/gmail_watcher_state.json for duplicate-free restarts
    - Includes thread context (previous message snippets) in action files (US3)
    - Exponential backoff on errors (1 → 2 → 4 → 8 → … → 60 s)
    """

    def __init__(self, vault_path: Optional[str] = None, check_interval: int = 120):
        # Load .env before anything else so VAULT_PATH is available
        load_dotenv(_BASE_DIR / ".env")

        if vault_path is None:
            vault_path = os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE")

        super().__init__(vault_path=vault_path, check_interval=check_interval)

        # Paths inside Hackathon-0/config/
        self._state_file = _BASE_DIR / "config" / "gmail_watcher_state.json"
        self._token_file = _BASE_DIR / "config" / "gmail_token.pickle"
        self._state_file.parent.mkdir(parents=True, exist_ok=True)

        self._gmail_service = None
        self._shutdown_requested = False
        self._label_cache: Dict[str, str] = {}  # label_name → label_id

        self._state = self._load_state()

        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        self.logger.info(
            f"GmailWatcher initialised | vault={vault_path} | interval={check_interval}s"
        )

    # ── Shutdown ─────────────────────────────────────────────────────────────

    def _handle_shutdown(self, _signum, _frame):
        self.logger.info("Shutdown signal received — saving state…")
        self._shutdown_requested = True

    # ── OAuth2 / service ─────────────────────────────────────────────────────

    def _load_credentials(self):
        """Load credentials from token pickle, refreshing if expired."""
        if not self._token_file.exists():
            raise RuntimeError(
                f"No Gmail token at {self._token_file}. "
                "Run 'python scripts/authenticate_gmail.py' first."
            )

        with open(self._token_file, "rb") as fh:
            creds = pickle.load(fh)

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                self.logger.info("Refreshing expired OAuth2 token…")
                creds.refresh(Request())
                with open(self._token_file, "wb") as fh:
                    pickle.dump(creds, fh)
                self.logger.info("Token refreshed and saved.")
            else:
                raise RuntimeError(
                    "Invalid Gmail credentials — cannot refresh. "
                    "Re-run 'python scripts/authenticate_gmail.py'."
                )

        return creds

    def _get_service(self):
        """Return (cached) Gmail API service."""
        if self._gmail_service is None:
            creds = self._load_credentials()
            self._gmail_service = build("gmail", "v1", credentials=creds)
            self.logger.info("Gmail API service initialised.")
        return self._gmail_service

    # ── State persistence ─────────────────────────────────────────────────────

    def _empty_state(self) -> Dict[str, Any]:
        return {
            "last_checked_message_id": None,
            "last_check_timestamp": None,
            "processed_message_ids": [],
            "classification_stats": {
                "total_processed": 0,
                "actionable": 0,
                "non_actionable": 0,
                "domain_pattern_filtered": 0,
                "keyword_filtered": 0,
                "handbook_matched": 0,
                "default_actionable": 0,
            },
        }

    def _load_state(self) -> Dict[str, Any]:
        if not self._state_file.exists():
            return self._empty_state()
        try:
            with open(self._state_file, "r") as fh:
                state = json.load(fh)
            n = len(state.get("processed_message_ids", []))
            self.logger.info(f"State loaded: {n} previously processed messages.")
            return state
        except Exception as exc:
            self.logger.warning(f"Could not load state ({exc}) — starting fresh.")
            return self._empty_state()

    def _save_state(self):
        """Atomic JSON write with rolling 1000-entry window."""
        try:
            ids = self._state.get("processed_message_ids", [])
            if len(ids) > 1000:
                self._state["processed_message_ids"] = ids[-1000:]

            self._state["last_check_timestamp"] = datetime.now(timezone.utc).isoformat()

            dir_path = self._state_file.parent
            fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as fh:
                    json.dump(self._state, fh, indent=2)
                os.replace(tmp_path, self._state_file)
            except Exception:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
        except Exception as exc:
            self.logger.error(f"Error saving state: {exc}")

    # ── Classification ────────────────────────────────────────────────────────

    def _classify_email(self, sender_email: str, subject: str) -> Tuple[str, str]:
        """
        Three-tier classification.
        Returns: (classification, reason)
          classification: "actionable" | "non-actionable"
          reason: "domain_pattern" | "keyword_match" | "handbook_client" | "default_actionable"
        """
        sender_lower = sender_email.lower()

        # 1. Domain pattern
        for pattern in NON_ACTIONABLE_DOMAIN_PATTERNS:
            if pattern.search(sender_lower):
                return "non-actionable", "domain_pattern"

        # 2. Subject keyword
        subject_lower = subject.lower()
        for keyword in NON_ACTIONABLE_KEYWORDS:
            if keyword in subject_lower:
                return "non-actionable", "keyword_match"

        # 3. Handbook client lookup
        if "@" in sender_email:
            domain = sender_email.split("@")[-1].lower()
            if domain and self._is_handbook_client(domain):
                return "actionable", "handbook_client"

        # 4. Default: actionable
        return "actionable", "default_actionable"

    def _is_handbook_client(self, sender_domain: str) -> bool:
        """Check if domain is listed under '## Clients' in Company_Handbook.md."""
        try:
            content = self.vault_manager.read_company_handbook()
            if not content:
                return False
            match = re.search(
                r"##\s+Clients\s*\n(.*?)(?=\n##\s|\Z)",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            if not match:
                return False
            domains = re.findall(r"[\w.-]+\.\w{2,}", match.group(1))
            return sender_domain in {d.lower() for d in domains}
        except Exception as exc:
            self.logger.warning(f"Handbook lookup failed: {exc}")
            return False

    # ── Gmail labelling ───────────────────────────────────────────────────────

    def _get_or_create_label(self, label_name: str) -> Optional[str]:
        if label_name in self._label_cache:
            return self._label_cache[label_name]
        try:
            svc = self._get_service()
            resp = svc.users().labels().list(userId="me").execute()
            for lbl in resp.get("labels", []):
                if lbl["name"].lower() == label_name.lower():
                    self._label_cache[label_name] = lbl["id"]
                    return lbl["id"]
            # Create
            new_lbl = svc.users().labels().create(
                userId="me",
                body={"name": label_name, "labelListVisibility": "labelShow"},
            ).execute()
            self._label_cache[label_name] = new_lbl["id"]
            return new_lbl["id"]
        except Exception as exc:
            self.logger.warning(f"Could not get/create label '{label_name}': {exc}")
            return None

    def _apply_label(self, message_id: str, classification: str):
        label_id = self._get_or_create_label(classification)
        if not label_id:
            return
        try:
            self._get_service().users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": [label_id]},
            ).execute()
        except Exception as exc:
            self.logger.warning(f"Label apply failed for {message_id}: {exc}")

    # ── Thread context (US3) ──────────────────────────────────────────────────

    def _fetch_thread_context(self, thread_id: str, current_message_id: str) -> List[Dict[str, str]]:
        """
        Return a list of previous message snippets in the thread
        (excludes the current message).
        """
        if not thread_id:
            return []
        try:
            svc = self._get_service()
            thread = svc.users().threads().get(
                userId="me", id=thread_id, format="metadata",
                metadataHeaders=["From", "Date"],
            ).execute()
            context = []
            for msg in thread.get("messages", []):
                if msg["id"] == current_message_id:
                    continue
                hdrs = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
                context.append({
                    "from": hdrs.get("from", "Unknown"),
                    "date": hdrs.get("date", "Unknown"),
                    "snippet": msg.get("snippet", "")[:200],
                })
            return context
        except Exception as exc:
            self.logger.warning(f"Thread context fetch failed for {thread_id}: {exc}")
            return []

    # ── Core watcher methods ──────────────────────────────────────────────────

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Fetch unread important emails, classify them, label in Gmail,
        and return only actionable ones for action-file creation.
        """
        actionable: List[Dict[str, Any]] = []
        processed_ids: List[str] = self._state.get("processed_message_ids", [])

        try:
            svc = self._get_service()
            result = svc.users().messages().list(
                userId="me", q="is:unread is:important", maxResults=50
            ).execute()
            messages = result.get("messages", [])
            self.logger.info(f"Fetched {len(messages)} unread important emails.")

            for ref in messages:
                msg_id = ref["id"]

                # Duplicate guard
                if msg_id in processed_ids:
                    continue

                try:
                    msg = svc.users().messages().get(
                        userId="me",
                        id=msg_id,
                        format="metadata",
                        metadataHeaders=["From", "Subject", "Date"],
                    ).execute()

                    hdrs = {
                        h["name"].lower(): h["value"]
                        for h in msg.get("payload", {}).get("headers", [])
                    }
                    sender_raw = hdrs.get("from", "")
                    subject = hdrs.get("subject", "(no subject)")
                    date_str = hdrs.get("date", "")
                    thread_id = msg.get("threadId", "")
                    body_snippet = msg.get("snippet", "")[:200]

                    # Parse sender
                    email_match = re.search(r"<([^>]+)>", sender_raw)
                    sender_email = email_match.group(1) if email_match else sender_raw.strip()
                    sender_name = re.sub(r"\s*<[^>]+>", "", sender_raw).strip().strip('"')

                    # Classify
                    classification, reason = self._classify_email(sender_email, subject)

                    # Update stats
                    stats = self._state["classification_stats"]
                    stats["total_processed"] += 1
                    if classification == "actionable":
                        stats["actionable"] += 1
                        if reason == "handbook_client":
                            stats["handbook_matched"] += 1
                        else:
                            stats["default_actionable"] += 1
                    else:
                        stats["non_actionable"] += 1
                        if reason == "domain_pattern":
                            stats["domain_pattern_filtered"] += 1
                        else:
                            stats["keyword_filtered"] += 1

                    # Label in Gmail
                    self._apply_label(msg_id, classification)

                    # Log decision
                    self.logger.info(
                        f"[{classification.upper()}] ({reason}) | "
                        f"from={sender_email} | subject={subject[:60]}"
                    )
                    self.vault_manager.log_activity(
                        "Email classified",
                        {
                            "message_id": msg_id,
                            "from": sender_email,
                            "subject": subject[:50],
                            "classification": classification,
                            "reason": reason,
                        },
                    )

                    # Mark processed
                    processed_ids.append(msg_id)
                    self._state["last_checked_message_id"] = msg_id

                    if classification == "actionable":
                        # Fetch thread context for US3
                        thread_context = self._fetch_thread_context(thread_id, msg_id)
                        actionable.append(
                            {
                                "message_id": msg_id,
                                "sender_email": sender_email,
                                "sender_name": sender_name,
                                "subject": subject,
                                "body_snippet": body_snippet,
                                "received_timestamp": date_str,
                                "thread_id": thread_id,
                                "classification": classification,
                                "classification_reason": reason,
                                "thread_context": thread_context,
                            }
                        )

                except HttpError as exc:
                    self.logger.error(f"API error on message {msg_id}: {exc}")
                except Exception as exc:
                    self.logger.error(f"Error processing message {msg_id}: {exc}")

            self._save_state()

        except HttpError as exc:
            self.logger.error(f"Gmail API error in check_for_updates: {exc}")
            self._gmail_service = None  # Force re-auth next cycle
        except Exception as exc:
            self.logger.error(f"Unexpected error in check_for_updates: {exc}")

        return actionable

    def create_action_file(self, item: Dict[str, Any]) -> Path:
        """
        Write EMAIL_{message_id}_{timestamp}.md to Needs_Action/.
        Includes thread context section when previous messages exist.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"EMAIL_{item['message_id']}_{timestamp}.md"
        file_path = self.needs_action_dir / filename

        content = f"""---
message_id: {item['message_id']}
thread_id: {item.get('thread_id', '')}
from_email: {item['sender_email']}
from_name: {item['sender_name']}
subject: {item['subject']}
received: {item.get('received_timestamp', '')}
---

# Email Action Required

## Metadata
- **Message ID**: {item['message_id']}
- **Thread ID**: {item.get('thread_id', 'N/A')}
- **From**: {item['sender_name']} <{item['sender_email']}>
- **Subject**: {item['subject']}
- **Received**: {item.get('received_timestamp', 'Unknown')}
- **Classification**: {item['classification']}
- **Classification Reason**: {item['classification_reason']}

## Body Snippet

{item['body_snippet']}

## Action Required

Review this email and determine the appropriate response or action.
"""

        # Thread context section (US3)
        thread_context = item.get("thread_context", [])
        if thread_context:
            content += "\n## Thread Context\n\n"
            for prev in thread_context:
                content += (
                    f"### Previous Message\n"
                    f"- **From**: {prev.get('from', 'Unknown')}\n"
                    f"- **Date**: {prev.get('date', 'Unknown')}\n"
                    f"- **Snippet**: {prev.get('snippet', '')}\n\n"
                )

        try:
            self.needs_action_dir.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            self.logger.info(f"Action file created: {file_path}")
            self.vault_manager.log_activity(
                "Email action file created",
                {
                    "file": filename,
                    "from": item["sender_email"],
                    "subject": item["subject"][:50],
                },
            )
            return file_path
        except Exception as exc:
            self.logger.error(f"Failed to create action file: {exc}")
            raise

    # ── Run loop ──────────────────────────────────────────────────────────────

    def run(self):
        """Main loop with graceful shutdown and exponential backoff on errors."""
        self.logger.info(
            f"GmailWatcher started (interval={self.check_interval}s, "
            f"token={self._token_file})"
        )
        backoff = 1
        max_backoff = 60

        while not self._shutdown_requested:
            try:
                items = self.check_for_updates()
                for item in items:
                    try:
                        self.create_action_file(item)
                    except Exception as exc:
                        self.logger.error(
                            f"Action file creation failed for {item.get('message_id')}: {exc}"
                        )
                backoff = 1  # Reset on success
            except Exception as exc:
                self.logger.error(f"Run-loop error: {exc}")
                self.vault_manager.log_activity("GmailWatcher error", {"error": str(exc)})
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                continue

            # Sleep in 1-second increments so shutdown is responsive
            for _ in range(self.check_interval):
                if self._shutdown_requested:
                    break
                time.sleep(1)

        self._save_state()
        self.logger.info("GmailWatcher stopped cleanly.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from src.utils.logger import setup_logging

    setup_logging()
    GmailWatcher().run()
