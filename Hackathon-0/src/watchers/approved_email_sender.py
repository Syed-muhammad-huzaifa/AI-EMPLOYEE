"""
Approved Email Sender
=====================
Watches the Approved/ vault folder. When a draft email file lands there it:
  1. Parses the recipient, subject, and body from the Markdown
  2. Sends the email via Gmail API (same credentials as email-mcp)
  3. Moves the file to Done/ on success, Rejected/ on failure
  4. Logs every action to Logs/

Supported draft format (YAML front-matter + body):

    ---
    to: alice@example.com
    subject: Re: Your inquiry
    ---

    Dear Alice,

    Body text here...

    Best regards,
    Ralph

If no front-matter is found the parser falls back to inline "Field: value" lines
at the top of the file.
"""

import os
import re
import sys
import time
import yaml
import pickle
import base64
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

_BASE_DIR = Path(__file__).parent.parent.parent  # Hackathon-0/
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

from src.vault.manager import VaultManager

load_dotenv(_BASE_DIR / ".env")

logger = logging.getLogger(__name__)

TOKEN_PATH = _BASE_DIR / "config" / "gmail_token.pickle"
_RETRYABLE  = (429, 500, 502, 503, 504)


# ── Gmail service ─────────────────────────────────────────────────────────────

def _load_service():
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
            raise RuntimeError("Credentials invalid — re-authenticate.")
    return build("gmail", "v1", credentials=creds)


# ── Draft parser ──────────────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)


def _clean_output_text(text: str) -> str:
    """
    Clean markdown formatting and meta-commentary from email/social post text.
    Makes output look human-written, not AI-generated.

    Removes:
    - Markdown headers (##, ###)
    - Markdown bold (**text**)
    - Markdown lists (- item, * item)
    - Meta-commentary ("Let me draft...", "Here's what I'm thinking...")
    - Processing steps ("Step 1:", "First, I will...")

    Preserves:
    - Natural line breaks
    - Paragraph structure
    - Emojis and hashtags
    """
    if not text:
        return text

    # Remove meta-commentary patterns (case-insensitive)
    meta_patterns = [
        r"(?i)^.*?(?:let me|i'll|i will|here's what|i'm thinking|i'm going to).*?\n",
        r"(?i)^.*?(?:step \d+:|first,|next,|then,|finally,).*?\n",
        r"(?i)^.*?(?:this (?:email|post|message) will|the purpose is).*?\n",
        r"(?i)^## (?:action summary|draft|preview|email body|to approve).*?\n",
    ]
    for pattern in meta_patterns:
        text = re.sub(pattern, "", text, flags=re.MULTILINE)

    # Remove markdown headers (## Header, ### Header)
    text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)

    # Convert markdown bold to plain text (**text** or __text__)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)

    # Convert markdown lists to natural text
    # "- Item" or "* Item" → "Item"
    text = re.sub(r'^[\s]*[-*]\s+', '', text, flags=re.MULTILINE)

    # Remove horizontal rules (---, ***)
    text = re.sub(r'^[\s]*[-*]{3,}[\s]*$', '', text, flags=re.MULTILINE)

    # Remove code blocks (```...```)
    text = re.sub(r'```[\s\S]*?```', '', text)

    # Clean up excessive blank lines (max 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def parse_draft(content: str) -> Optional[Dict[str, str]]:
    """
    Parse a draft markdown file into {to, subject, body, task_id, action,
    thread_id, in_reply_to, attachments}.
    Returns None if required fields (to, subject) are missing.

    Handles three layouts:
      1. YAML frontmatter with to:/subject:/task_id: keys  (skill HITL format)
      2. YAML frontmatter (other keys) + **To**:/**Subject**: in the body
      3. Plain inline "To: ..." / "**To**: ..." lines (no frontmatter)

    Attachments format in frontmatter:
      attachments:
        - filename: invoice.pdf
          content_base64: <base64-encoded-data>
          mime_type: application/pdf
    """
    to = subject = body = task_id = action = thread_id = in_reply_to = None
    attachments = []
    invoice_id = None

    # Strip frontmatter block (we'll scan both it and the remainder)
    fm_match = _FRONTMATTER_RE.match(content.strip())
    platform = None
    if fm_match:
        fm_block    = fm_match.group(1)
        after_front = fm_match.group(2).strip()

        # Parse attachments from YAML frontmatter
        # Format: attachments: [{filename: x, content_base64: y, mime_type: z}]
        import yaml
        try:
            fm_data = yaml.safe_load(fm_block)
            if isinstance(fm_data, dict) and "attachments" in fm_data:
                att_list = fm_data["attachments"]
                if isinstance(att_list, list):
                    for att in att_list:
                        if isinstance(att, dict):
                            attachments.append({
                                "filename": att.get("filename", "attachment.bin"),
                                "content_base64": att.get("content_base64", ""),
                                "mime_type": att.get("mime_type", "application/octet-stream"),
                            })
        except Exception:
            pass  # YAML parsing failed, continue with line-by-line parsing

        # Scan frontmatter for all known keys
        for line in fm_block.splitlines():
            m = re.match(
                r"^\s*(to|whatsapp_to|subject|task_id|action|thread_id|in_reply_to|platform|invoice_id)\s*:\s*(.+)",
                line, re.IGNORECASE
            )
            if m:
                key = m.group(1).lower()
                val = m.group(2).strip()
                if key in ("to", "whatsapp_to") and not to:
                    to = val
                elif key == "subject" and not subject:
                    subject = val
                elif key == "task_id" and not task_id:
                    task_id = val
                elif key == "action" and not action:
                    action = val
                elif key == "thread_id" and not thread_id:
                    thread_id = val
                elif key == "in_reply_to" and not in_reply_to:
                    in_reply_to = val
                elif key == "platform" and not platform:
                    platform = val
                elif key == "invoice_id" and not invoice_id:
                    try:
                        invoice_id = int(val)
                    except (ValueError, TypeError):
                        pass
        # Scan the body section for **To**: / **Subject**: patterns
        body_lines = after_front.splitlines()
    else:
        body_lines = content.splitlines()

    # Scan lines for bold or plain "To:" / "Subject:" / "Task_id:" patterns
    body_start = 0
    for i, line in enumerate(body_lines[:40]):
        m = re.match(r"^\s*\*{0,2}(to|subject|task_id|action)\*{0,2}\s*:\s*(.+)", line, re.IGNORECASE)
        if m:
            key = m.group(1).lower()
            val = m.group(2).strip()
            if key == "to" and not to:
                to = val
            elif key == "subject" and not subject:
                subject = val
            elif key == "task_id" and not task_id:
                task_id = val
            elif key == "action" and not action:
                action = val
            body_start = i + 1
        if to and subject and i > body_start:
            break

    if body is None:
        # Take everything after the header lines as the body
        # Skip markdown section headers like "## Email Body", "## To Approve"
        raw_body_lines = body_lines[body_start:]
        body_content = []
        for line in raw_body_lines:
            if re.match(r"^##\s+(To Approve|To Reject)", line):
                break  # stop at approval instructions
            body_content.append(line)
        body = "\n".join(body_content).strip()
        # Remove leading "## Email Body" header if present
        body = re.sub(r"^##\s+Email Body\s*\n", "", body).strip()

    _action = (action or "send_email").strip()
    # Social media posts don't need 'to' or 'subject'
    if _action in ("post_linkedin", "post_twitter", "post_facebook", "post_social_media", "post_social"):
        return {
            "to":          to or "",
            "subject":     subject or "",
            "body":        body or "",
            "task_id":     task_id.strip() if task_id else None,
            "action":      _action,
            "platform":    platform.strip() if platform else "linkedin",
            "thread_id":   thread_id.strip() if thread_id else None,
            "in_reply_to": in_reply_to.strip() if in_reply_to else None,
        }

    # Email and WhatsApp require 'to' field
    if not to:
        return None
    if _action == "send_email" and not subject:
        return None

    return {
        "to":          to.strip(),
        "subject":     subject.strip() if subject else "",
        "body":        body or "",
        "task_id":     task_id.strip() if task_id else None,
        "action":      _action,
        "thread_id":   thread_id.strip() if thread_id else None,
        "in_reply_to": in_reply_to.strip() if in_reply_to else None,
        "attachments": attachments,
        "invoice_id":  invoice_id,
    }


# ── Sender ────────────────────────────────────────────────────────────────────

def _send_with_retry(service, to: str, subject: str, body: str,
                     attachments: list = None,
                     thread_id: Optional[str] = None,
                     in_reply_to: Optional[str] = None,
                     max_retries: int = 3) -> Tuple[bool, str]:
    """
    Send email with optional attachments, retry on transient errors.
    Pass thread_id + in_reply_to to reply in the same Gmail thread.

    attachments: list of dicts with {filename, content_base64, mime_type}

    Returns (success: bool, message_id_or_error: str).
    """
    attachments = attachments or []
    backoff = 1
    for attempt in range(1, max_retries + 1):
        try:
            mime = MIMEMultipart()
            mime["to"]      = to
            mime["subject"] = subject
            if in_reply_to:
                mime["In-Reply-To"] = in_reply_to
                mime["References"]  = in_reply_to
            mime.attach(MIMEText(body, "plain"))

            # Attach files
            for att in attachments:
                filename = att.get("filename", "attachment.bin")
                content_b64 = att.get("content_base64", "")
                mime_type = att.get("mime_type", "application/octet-stream")

                if not content_b64:
                    logger.warning(f"Skipping empty attachment: {filename}")
                    continue

                try:
                    # Decode base64 content
                    file_data = base64.b64decode(content_b64)

                    # Create MIME attachment
                    part = MIMEBase(*mime_type.split("/", 1))
                    part.set_payload(file_data)
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={filename}")
                    mime.attach(part)
                    logger.info(f"Attached file: {filename} ({len(file_data)} bytes)")
                except Exception as att_error:
                    logger.error(f"Failed to attach {filename}: {att_error}")
                    # Continue with other attachments

            raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
            send_body: Dict = {"raw": raw}
            if thread_id:
                send_body["threadId"] = thread_id
            result = service.users().messages().send(
                userId="me", body=send_body
            ).execute()
            return True, result.get("id", "unknown")
        except HttpError as exc:
            if exc.resp.status in _RETRYABLE and attempt < max_retries:
                logger.warning(f"Retryable error (attempt {attempt}): {exc}. Retry in {backoff}s")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            return False, f"GMAIL_API_ERROR: {exc}"
        except Exception as exc:
            if attempt < max_retries:
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            return False, f"NETWORK_ERROR: {exc}"
    return False, "MAX_RETRIES_EXCEEDED"


# ── ApprovedEmailSender ───────────────────────────────────────────────────────

class ApprovedEmailSender:
    """
    Daemon that polls Approved/ and sends any email draft files it finds.
    Not a BaseWatcher subclass because it doesn't create action files —
    it consumes and moves them.
    """

    def __init__(self, vault_path: Optional[str] = None, check_interval: int = 15,
                 dry_run: bool = False):
        load_dotenv(_BASE_DIR / ".env")

        vault_path = vault_path or os.getenv("VAULT_PATH", "/mnt/c/MY_EMPLOYEE") or "/mnt/c/MY_EMPLOYEE"
        self.vault          = Path(vault_path)
        self.approved_dir   = self.vault / "Approved"
        self.done_dir       = self.vault / "Done"
        self.rejected_dir   = self.vault / "Rejected"
        self.check_interval = check_interval
        self.dry_run        = dry_run or os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")
        self.vault_manager  = VaultManager(vault_path)
        self._shutdown      = False
        self.logger         = logging.getLogger(self.__class__.__name__)

        for d in (self.approved_dir, self.done_dir, self.rejected_dir):
            d.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            f"ApprovedEmailSender ready | vault={vault_path} | "
            f"interval={check_interval}s | dry_run={self.dry_run}"
        )

    def stop(self):
        self._shutdown = True

    def run(self):
        """Polling loop — runs forever until stop() is called."""
        self.logger.info("ApprovedEmailSender started.")
        while not self._shutdown:
            try:
                self._process_approved_files()
            except Exception as exc:
                self.logger.error(f"Error in ApprovedEmailSender loop: {exc}")
            time.sleep(self.check_interval)

    def _process_approved_files(self):
        if not self.approved_dir.exists():
            return

        for file_path in sorted(self.approved_dir.iterdir()):
            if not file_path.is_file() or file_path.suffix != ".md":
                continue
            self._handle_approved_file(file_path)

    def _intelligent_parse(self, content: str, file_path: Path) -> Optional[Dict]:
        """
        Intelligent parser that handles Claude's creative approval formats.

        Extracts:
        - Email recipient, subject, body from various formats
        - Gmail draft IDs (fetches draft content)
        - Invoice IDs (fetches PDF from Odoo)
        - Normalizes action types
        """
        import re

        result = {
            "to": None,
            "subject": None,
            "body": None,
            "task_id": None,
            "action": "send_email",
            "attachments": [],
            "thread_id": None,
            "in_reply_to": None,
        }

        # Extract from YAML frontmatter if present
        fm_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL | re.MULTILINE)
        if fm_match:
            fm_text = fm_match.group(1)

            # Extract fields
            for line in fm_text.splitlines():
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip().lower()
                    val = val.strip()

                    if key == 'task_id':
                        result['task_id'] = val
                    elif key in ('action', 'step_id'):
                        # Normalize action types
                        if 'email' in val.lower():
                            result['action'] = 'send_email'

        # Extract recipient
        to_match = re.search(r'\*\*To\*\*:\s*([^\n]+)', content, re.IGNORECASE)
        if not to_match:
            to_match = re.search(r'(?:Recipient|Customer|Email):\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', content, re.IGNORECASE)
        if to_match:
            result['to'] = to_match.group(1).strip()

        # Extract subject
        subj_match = re.search(r'\*\*Subject\*\*:\s*([^\n]+)', content, re.IGNORECASE)
        if subj_match:
            result['subject'] = subj_match.group(1).strip()

        # Extract Gmail draft ID
        draft_match = re.search(r'Draft ID[:\s]+([a-zA-Z0-9_-]+)', content, re.IGNORECASE)
        if draft_match:
            draft_id = draft_match.group(1)
            self.logger.info(f"Found Gmail draft ID: {draft_id}")
            # TODO: Fetch draft content from Gmail API
            # For now, extract body from preview

        # Extract email body from preview section
        body_match = re.search(r'\*\*Body\*\*:\s*```\s*\n(.*?)\n```', content, re.DOTALL)
        if body_match:
            result['body'] = body_match.group(1).strip()

        # Extract invoice ID and fetch PDF
        inv_match = re.search(r'Invoice (?:ID|Number)[:\s]+(\d+|INV[/\-]?\d+[/\-]?\d+)', content, re.IGNORECASE)
        if inv_match:
            invoice_ref = inv_match.group(1)
            self.logger.info(f"Found invoice reference: {invoice_ref}")

            # Extract numeric ID
            inv_id_match = re.search(r'Invoice ID[:\s]+(\d+)', content, re.IGNORECASE)
            if inv_id_match:
                invoice_id = int(inv_id_match.group(1))
                pdf_data = self._fetch_invoice_pdf(invoice_id)
                if pdf_data:
                    result['attachments'].append(pdf_data)

        # Validate required fields
        if not result['to'] or not result['subject']:
            return None

        return result

    def _fetch_invoice_pdf(self, invoice_id: int) -> Optional[Dict]:
        """
        Fetch PDF from Odoo by calling the Odoo API directly.
        Uses the same credentials and approach as the Odoo MCP server.
        """
        try:
            import requests

            odoo_url  = os.getenv("ODOO_URL", "http://localhost:8069").rstrip("/")
            odoo_db   = os.getenv("ODOO_DB", "MYdb")
            odoo_user = os.getenv("ODOO_USER", "iam@gmail.com")
            odoo_pass = os.getenv("ODOO_PASSWORD", "admin123")

            session = requests.Session()

            # Authenticate
            auth_resp = session.post(
                f"{odoo_url}/web/session/authenticate",
                json={"jsonrpc": "2.0", "method": "call", "id": 1,
                      "params": {"db": odoo_db, "login": odoo_user, "password": odoo_pass}},
                timeout=15,
            )
            auth_resp.raise_for_status()
            auth_result = auth_resp.json().get("result", {})
            if not auth_result.get("uid"):
                self.logger.error("Odoo authentication failed — check ODOO_USER/ODOO_PASSWORD")
                return None

            # Get invoice name
            inv_resp = session.post(
                f"{odoo_url}/web/dataset/call_kw",
                json={"jsonrpc": "2.0", "method": "call", "id": 2,
                      "params": {"model": "account.move", "method": "read",
                                 "args": [[invoice_id]], "kwargs": {"fields": ["name", "state"]}}},
                timeout=15,
            )
            inv_data = inv_resp.json().get("result", [])
            if not inv_data:
                self.logger.error(f"Invoice {invoice_id} not found in Odoo")
                return None

            inv = inv_data[0]
            if inv.get("state") != "posted":
                self.logger.warning(f"Invoice {inv.get('name')} is not posted — cannot generate PDF")
                return None

            invoice_number = inv["name"]

            # Fetch PDF via HTTP report endpoint
            report_url = f"{odoo_url}/report/pdf/account.report_invoice/{invoice_id}"
            pdf_resp = session.get(report_url, timeout=30)
            pdf_resp.raise_for_status()

            pdf_bytes = pdf_resp.content
            if not pdf_bytes:
                self.logger.error(f"Empty PDF returned for invoice {invoice_id}")
                return None

            filename = f"{invoice_number.replace('/', '_')}.pdf"
            pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

            self.logger.info(
                f"Fetched PDF for {invoice_number} ({len(pdf_bytes):,} bytes) → {filename}"
            )
            return {
                "filename": filename,
                "content_base64": pdf_base64,
                "mime_type": "application/pdf",
            }

        except Exception as exc:
            self.logger.error(f"Error fetching invoice PDF for ID {invoice_id}: {exc}")
            return None

    def _enrich_with_invoice_pdf(self, draft: Dict, content: str) -> None:
        """
        Post-parse enrichment: fetch invoice PDF from Odoo and add to attachments.
        Runs after parsing succeeds. Mutates draft['attachments'] in place.
        No-op if attachments are already present.
        """
        if draft.get("attachments"):
            return  # already has attachments

        # Prefer invoice_id parsed from YAML frontmatter (clean, reliable)
        invoice_id = draft.get("invoice_id")

        # Fallback: scan raw content for patterns like "invoice_id: 70" or "Invoice ID: 70"
        if not invoice_id:
            inv_id_match = re.search(
                r'(?:^invoice_id|Invoice\s+ID)[:\s*]+(\d+)',
                content, re.IGNORECASE | re.MULTILINE
            )
            if inv_id_match:
                try:
                    invoice_id = int(inv_id_match.group(1))
                except (ValueError, TypeError):
                    pass

        if not invoice_id:
            return  # no invoice reference found

        self.logger.info(f"Enriching email with PDF for invoice ID {invoice_id}")
        pdf_data = self._fetch_invoice_pdf(invoice_id)
        if pdf_data:
            if not isinstance(draft.get("attachments"), list):
                draft["attachments"] = []
            draft["attachments"].append(pdf_data)
            self.logger.info(f"Attached PDF: {pdf_data['filename']}")
        else:
            self.logger.warning(
                f"Could not fetch PDF for invoice {invoice_id} — sending without attachment"
            )

    def _handle_approved_file(self, file_path: Path):
        self.logger.info(f"Processing approved file: {file_path.name}")

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            self.logger.error(f"Could not read {file_path}: {exc}")
            return

        # Try to parse as standard format first
        draft = parse_draft(content)

        # If standard parsing fails, try intelligent parsing
        if not draft:
            draft = self._intelligent_parse(content, file_path)

        if not draft:
            self.logger.warning(
                f"Could not parse fields from {file_path.name}. Moving to Rejected/."
            )
            self._move(file_path, self.rejected_dir, reason="parse_failed")
            return

        # Always enrich: if content mentions invoice IDs but no attachments yet, fetch PDF
        self._enrich_with_invoice_pdf(draft, content)

        action      = draft.get("action", "send_email")
        to          = draft["to"]
        subject     = draft.get("subject", "")
        body        = draft["body"]
        task_id     = draft.get("task_id")
        thread_id   = draft.get("thread_id")
        in_reply_to = draft.get("in_reply_to")
        attachments = draft.get("attachments", [])

        # Clean markdown and meta-commentary from body text
        # Makes emails/posts look human-written, not AI-generated
        body = _clean_output_text(body)

        # ── Route to correct channel ──────────────────────────────────────────
        if action == "send_whatsapp":
            self._handle_whatsapp_send(file_path, to, body, task_id)
            return
        elif action == "post_linkedin":
            self._handle_linkedin_post(file_path, body, task_id)
            return
        elif action == "post_twitter":
            self._handle_twitter_post(file_path, body, task_id)
            return
        elif action == "post_facebook":
            self._handle_facebook_post(file_path, body, task_id)
            return
        elif action == "post_social":
            # Route based on platform field in frontmatter
            platform = draft.get("platform", "linkedin").lower()
            if platform == "linkedin":
                self._handle_linkedin_post(file_path, body, task_id)
            elif platform == "twitter":
                self._handle_twitter_post(file_path, body, task_id)
            elif platform == "facebook":
                self._handle_facebook_post(file_path, body, task_id)
            else:
                self._handle_linkedin_post(file_path, body, task_id)
            return
        elif action == "post_social_media":
            # Multi-platform post - extract each platform's content
            self._handle_multi_platform_post(file_path, draft, task_id)
            return

        self.logger.info(f"Sending email → to={to} | subject={subject[:60]}")

        # Log attachment info if present
        if attachments:
            att_summary = ", ".join(f"{a['filename']} ({a.get('mime_type', 'unknown')})" for a in attachments)
            self.logger.info(f"Attachments: {att_summary}")


        # ── Dry run ──────────────────────────────────────────────────────────
        if self.dry_run:
            self.logger.info(
                f"[DRY RUN] Would send email | to={to} | subject={subject[:60]}"
            )
            self.vault_manager.log_activity(
                "Email approved and sent (DRY RUN)",
                {"to": to, "subject": subject[:60], "file": file_path.name},
            )
            self._move(file_path, self.done_dir, reason="sent_dry_run")
            self._close_original_task(task_id, reason="sent_dry_run")
            return

        # ── Real send ─────────────────────────────────────────────────────────
        try:
            service          = _load_service()
            success, msg_ref = _send_with_retry(
                service, to, subject, body,
                attachments=attachments,
                thread_id=thread_id, in_reply_to=in_reply_to
            )
        except RuntimeError as exc:
            self.logger.error(f"Authentication failed: {exc}")
            self._move(file_path, self.rejected_dir, reason="auth_failed")
            return

        if success:
            self.logger.info(f"✅ Email sent | message_id={msg_ref} | to={to}")
            self.vault_manager.log_activity(
                "Email sent successfully",
                {"to": to, "subject": subject[:60],
                 "message_id": msg_ref, "file": file_path.name},
            )
            self._move(file_path, self.done_dir, reason="sent")
            self._close_original_task(task_id, reason="email_sent")
        else:
            self.logger.error(f"❌ Email send failed: {msg_ref}")
            self.vault_manager.log_activity(
                "Email send FAILED",
                {"to": to, "subject": subject[:60],
                 "error": msg_ref, "file": file_path.name},
            )
            self._move(file_path, self.rejected_dir, reason=msg_ref)

    def _handle_whatsapp_send(
        self, file_path: Path, to: str, body: str, task_id: Optional[str]
    ):
        """Send an approved WhatsApp reply via Twilio."""
        from src.watchers.whatsapp_watcher import send_whatsapp_message, ConversationStore

        # Clean markdown and meta-commentary
        body = _clean_output_text(body)

        self.logger.info(f"Sending WhatsApp → to={to}")

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would send WhatsApp | to={to}")
            self.vault_manager.log_activity(
                "WhatsApp approved and sent (DRY RUN)",
                {"to": to, "file": file_path.name},
            )
            self._move(file_path, self.done_dir, reason="sent_dry_run")
            self._close_original_task(task_id, reason="sent_dry_run")
            return

        success, ref = send_whatsapp_message(to, body)
        if success:
            self.logger.info(f"✅ WhatsApp sent | sid={ref} | to={to}")
            # Log the assistant reply in conversation history
            try:
                store = ConversationStore()
                store.add_message(to, "assistant", body)
            except Exception:
                pass
            self.vault_manager.log_activity(
                "WhatsApp sent successfully",
                {"to": to, "sid": ref, "file": file_path.name},
            )
            self._move(file_path, self.done_dir, reason="sent")
            self._close_original_task(task_id, reason="whatsapp_sent")
        else:
            self.logger.error(f"❌ WhatsApp send failed: {ref}")
            self.vault_manager.log_activity(
                "WhatsApp send FAILED",
                {"to": to, "error": ref, "file": file_path.name},
            )
            self._move(file_path, self.rejected_dir, reason=ref)

    def _handle_linkedin_post(self, file_path: Path, body: str, task_id: Optional[str]):
        """Post to LinkedIn after human approval."""
        # Clean markdown and meta-commentary
        body = _clean_output_text(body)

        self.logger.info("Posting to LinkedIn")

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would post to LinkedIn | length={len(body)}")
            self.vault_manager.log_activity(
                "LinkedIn post approved (DRY RUN)",
                {"file": file_path.name},
            )
            self._move(file_path, self.done_dir, reason="posted_dry_run")
            self._close_original_task(task_id, reason="posted_dry_run")
            return

        try:
            import subprocess
            post_script = Path(__file__).parent.parent.parent / "scripts" / "post_social.py"
            result = subprocess.run(
                ["python3", str(post_script), "linkedin", body],
                capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                self.logger.info("✅ LinkedIn post published")
                self.vault_manager.log_activity(
                    "LinkedIn post published",
                    {"file": file_path.name},
                )
                self._move(file_path, self.done_dir, reason="posted")
                self._close_original_task(task_id, reason="linkedin_posted")
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self.logger.error(f"❌ LinkedIn post failed: {error_msg}")
                self._move(file_path, self.rejected_dir, reason="linkedin_post_failed")
        except Exception as exc:
            self.logger.error(f"LinkedIn post error: {exc}")
            self._move(file_path, self.rejected_dir, reason=str(exc))

    def _handle_twitter_post(self, file_path: Path, body: str, task_id: Optional[str]):
        """Post to Twitter after human approval."""
        # Clean markdown and meta-commentary
        body = _clean_output_text(body)

        self.logger.info("Posting to Twitter")

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would post to Twitter | length={len(body)}")
            self.vault_manager.log_activity(
                "Twitter post approved (DRY RUN)",
                {"file": file_path.name},
            )
            self._move(file_path, self.done_dir, reason="posted_dry_run")
            self._close_original_task(task_id, reason="posted_dry_run")
            return

        try:
            import subprocess
            post_script = Path(__file__).parent.parent.parent / "scripts" / "post_social.py"
            result = subprocess.run(
                ["python3", str(post_script), "twitter", body],
                capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                self.logger.info("✅ Twitter post published")
                self.vault_manager.log_activity(
                    "Twitter post published",
                    {"file": file_path.name},
                )
                self._move(file_path, self.done_dir, reason="posted")
                self._close_original_task(task_id, reason="twitter_posted")
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self.logger.error(f"❌ Twitter post failed: {error_msg}")
                self._move(file_path, self.rejected_dir, reason="twitter_post_failed")
        except Exception as exc:
            self.logger.error(f"Twitter post error: {exc}")
            self._move(file_path, self.rejected_dir, reason=str(exc))

    def _handle_facebook_post(self, file_path: Path, body: str, task_id: Optional[str]):
        """Post to Facebook after human approval."""
        # Clean markdown and meta-commentary
        body = _clean_output_text(body)

        self.logger.info("Posting to Facebook")

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would post to Facebook | length={len(body)}")
            self.vault_manager.log_activity(
                "Facebook post approved (DRY RUN)",
                {"file": file_path.name},
            )
            self._move(file_path, self.done_dir, reason="posted_dry_run")
            self._close_original_task(task_id, reason="posted_dry_run")
            return

        try:
            import subprocess
            post_script = Path(__file__).parent.parent.parent / "scripts" / "post_social.py"
            result = subprocess.run(
                ["python3", str(post_script), "facebook", body],
                capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                self.logger.info("✅ Facebook post published")
                self.vault_manager.log_activity(
                    "Facebook post published",
                    {"file": file_path.name},
                )
                self._move(file_path, self.done_dir, reason="posted")
                self._close_original_task(task_id, reason="facebook_posted")
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self.logger.error(f"❌ Facebook post failed: {error_msg}")
                self._move(file_path, self.rejected_dir, reason="facebook_post_failed")
        except Exception as exc:
            self.logger.error(f"Facebook post error: {exc}")
            self._move(file_path, self.rejected_dir, reason=str(exc))

    def _handle_multi_platform_post(self, file_path: Path, draft: Dict, task_id: Optional[str]):
        """Handle multi-platform social media posts (LinkedIn, Twitter, Facebook)."""
        import subprocess

        content = file_path.read_text(encoding="utf-8")

        # Extract platform-specific content
        linkedin_match = re.search(r"## LinkedIn Post.*?\n\n(.*?)(?=\n---|\n##|$)", content, re.DOTALL)
        twitter_match = re.search(r"## Twitter Post.*?\n\n(.*?)(?=\n---|\n##|$)", content, re.DOTALL)
        facebook_match = re.search(r"## Facebook Post.*?\n\n(.*?)(?=\n---|\n##|$)", content, re.DOTALL)

        results = []
        post_script = Path(__file__).parent.parent.parent / "scripts" / "post_social.py"

        # Post to LinkedIn
        if linkedin_match:
            linkedin_text = linkedin_match.group(1).strip()
            # Clean markdown and meta-commentary
            linkedin_text = _clean_output_text(linkedin_text)
            self.logger.info("Posting to LinkedIn...")
            try:
                result = subprocess.run(
                    ["python3", str(post_script), "linkedin", linkedin_text],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                success = result.returncode == 0
                results.append(("LinkedIn", success))
                if success:
                    self.logger.info("✅ LinkedIn post published")
                else:
                    self.logger.error(f"❌ LinkedIn post failed: {result.stderr}")
            except Exception as exc:
                self.logger.error(f"LinkedIn error: {exc}")
                results.append(("LinkedIn", False))

        # Post to Twitter
        if twitter_match:
            twitter_text = twitter_match.group(1).strip()
            # Clean markdown and meta-commentary
            twitter_text = _clean_output_text(twitter_text)
            self.logger.info("Posting to Twitter...")
            try:
                result = subprocess.run(
                    ["python3", str(post_script), "twitter", twitter_text],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                success = result.returncode == 0
                results.append(("Twitter", success))
                if success:
                    self.logger.info("✅ Twitter post published")
                else:
                    self.logger.error(f"❌ Twitter post failed: {result.stderr}")
            except Exception as exc:
                self.logger.error(f"Twitter error: {exc}")
                results.append(("Twitter", False))

        # Post to Facebook
        if facebook_match:
            facebook_text = facebook_match.group(1).strip()
            # Clean markdown and meta-commentary
            facebook_text = _clean_output_text(facebook_text)
            self.logger.info("Posting to Facebook...")
            try:
                result = subprocess.run(
                    ["python3", str(post_script), "facebook", facebook_text],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                success = result.returncode == 0
                results.append(("Facebook", success))
                if success:
                    self.logger.info("✅ Facebook post published")
                else:
                    self.logger.error(f"❌ Facebook post failed: {result.stderr}")
            except Exception as exc:
                self.logger.error(f"Facebook error: {exc}")
                results.append(("Facebook", False))

        # Determine overall success
        all_success = all(success for _, success in results)
        any_success = any(success for _, success in results)

        summary = ", ".join(f"{platform}: {'✅' if success else '❌'}" for platform, success in results)

        if all_success:
            self.logger.info(f"✅ All platforms posted successfully | {summary}")
            self.vault_manager.log_activity(
                "Multi-platform post published",
                {"platforms": summary, "file": file_path.name},
            )
            self._move(file_path, self.done_dir, reason="posted_all")
            self._close_original_task(task_id, reason="social_media_posted")
        elif any_success:
            self.logger.warning(f"⚠️ Partial success | {summary}")
            self.vault_manager.log_activity(
                "Multi-platform post partially published",
                {"platforms": summary, "file": file_path.name},
            )
            self._move(file_path, self.done_dir, reason="posted_partial")
            self._close_original_task(task_id, reason="social_media_posted_partial")
        else:
            self.logger.error(f"❌ All platforms failed | {summary}")
            self._move(file_path, self.rejected_dir, reason="all_platforms_failed")

    def _close_original_task(self, task_id: Optional[str], reason: str = ""):
        """Move the original task file from In_Progress to Done after email is sent."""
        if not task_id:
            return

        in_progress_dir = self.vault / "In_Progress" / "orchestrator"
        done_dir        = self.vault / "Done"

        # Look for the original task file (with or without .md)
        for candidate in [
            in_progress_dir / f"{task_id}.md",
            in_progress_dir / task_id,
        ]:
            if candidate.exists():
                dest = done_dir / candidate.name
                try:
                    candidate.rename(dest)
                    self.logger.info(
                        f"✅ Original task archived | {candidate.name} → Done/ [{reason}]"
                    )
                    self.vault_manager.log_activity(
                        "Original task moved to Done after approval",
                        {"task_id": task_id, "reason": reason},
                    )
                except Exception as exc:
                    self.logger.error(f"Could not move original task {candidate}: {exc}")
                return

        self.logger.debug(f"Original task file not found in In_Progress for task_id={task_id}")

    def _move(self, src: Path, dest_dir: Path, reason: str = ""):
        """Move a file to dest_dir, appending _reason to the name."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        stem    = src.stem
        suffix  = src.suffix
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest    = dest_dir / f"{stem}_{ts}{suffix}"
        try:
            src.rename(dest)
            self.logger.info(f"Moved {src.name} → {dest_dir.name}/{dest.name} [{reason}]")
        except Exception as exc:
            self.logger.error(f"Could not move {src}: {exc}")
